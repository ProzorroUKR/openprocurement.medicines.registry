import os
import logging.config
import gevent

from functools import partial
from gevent import monkey, event
from retrying import retry
from requests import RequestException
from ConfigParser import ConfigParser, NoOptionError
from openprocurement.medicines.registry.utils import (
    journal_context, string_time_to_datetime, file_exists, create_file
)
from openprocurement.medicines.registry.journal_msg_ids import (
    BRIDGE_START,
    BRIDGE_INFO,
    BRIDGE_PROXY_SERVER_CONN_ERROR,
    BRIDGE_RESTART_WORKER
)
from openprocurement.medicines.registry.databridge.caching import DB
from openprocurement.medicines.registry import BASE_DIR
from openprocurement.medicines.registry.databridge.components import Registry, JsonFormer
from openprocurement.medicines.registry.client import ProxyClient


monkey.patch_all()

logger = logging.getLogger(__name__)

RETRY_MULT = 1000


class MedicinesRegistryBridge(object):
    def __init__(self, config):
        self.config = config

        # Cache DB settings
        self.db = DB(self.config)
        logger.info(
            'Caching backend: \'{}\', db name: \'{}\', host: \'{}\', port: \'{}\''.format(
                self.db.backend, self.db.db_name, self.db.host, self.db.port
            ),
            extra=journal_context({'MESSAGE_ID': BRIDGE_INFO}, {})
        )

        self.BASE_DIR = BASE_DIR

        self.INFINITY_LOOP = True

        self.time_update_at = string_time_to_datetime(self.config_get('time_update_at') or '05:30:00')
        self.delay = int(self.config_get('delay')) or 60
        self.registry_delay = int(self.config_get('registry_delay')) or 60
        self.json_files_delay = int(self.config_get('json_files_delay')) or 10
        self.file_cleaner_delay = int(self.config_get('file_cleaner_delay')) or 10
        self.cache_monitoring_delay = int(self.config_get('cache_monitoring_delay')) or 10

        self.source_registry = self.config_get('source_registry')
        try:
            self.source_registry_proxy = self.config_get('source_registry_proxy')
        except NoOptionError:
            self.source_registry_proxy = None

        self._files_init()

        self.proxy_client = ProxyClient(
            host=self.config_get('proxy_host'),
            port=self.config_get('proxy_port'),
            version=self.config_get('proxy_version')
        )

        self.services_not_available = event.Event()
        self.services_not_available.set()

        self.registry = partial(
            Registry.spawn,
            source_registry=self.source_registry,
            source_registry_proxy=self.source_registry_proxy,
            time_update_at=self.time_update_at,
            delay=self.delay,
            registry_delay=self.registry_delay,
            services_not_available=self.services_not_available
        )
        self.json_former = partial(
            JsonFormer.spawn,
            db=self.db,
            delay=self.delay,
            json_files_delay=self.json_files_delay,
            cache_monitoring_delay=self.cache_monitoring_delay,
            services_not_available=self.services_not_available
        )

        self.sandbox_mode = os.environ.get('SANDBOX_MODE', 'False')

    def config_get(self, name):
        if isinstance(self.config, ConfigParser):
            return self.config.get('app:api', name)
        else:
            return self.config.get(name)

    def _files_init(self):
        self.DATA_PATH = os.path.join(self.BASE_DIR, 'data')

        if not os.path.exists(self.DATA_PATH):
            os.makedirs(self.DATA_PATH)

        self.registry_xml = os.path.join(self.DATA_PATH, 'registry.xml')
        self.inn_json = os.path.join(self.DATA_PATH, 'inn.json')
        self.atc_json = os.path.join(self.DATA_PATH, 'atc.json')
        self.inn2atc_json = os.path.join(self.DATA_PATH, 'inn2atc.json')
        self.atc2inn_json = os.path.join(self.DATA_PATH, 'atc2inn.json')

        for f in [self.inn_json, self.atc_json, self.inn2atc_json, self.atc2inn_json, self.registry_xml]:
            if not file_exists(f):
                create_file(f)

    def set_sleep(self):
        self.services_not_available.clear()

    def set_wake_up(self):
        self.services_not_available.set()

    @retry(stop_max_attempt_number=5, wait_exponential_multiplier=RETRY_MULT)
    def check_proxy(self):
        try:
            self.proxy_client.health(self.sandbox_mode)
        except RequestException as e:
            logger.info(
                'Proxy server connection error, message {} {}'.format(e, self.sandbox_mode),
                extra=journal_context({'MESSAGE_ID': BRIDGE_PROXY_SERVER_CONN_ERROR}, {})
            )
            raise e
        else:
            return True

    def all_available(self):
        try:
            self.check_proxy()
        except Exception as e:
            logger.info('Service is unavailable, message {}'.format(e.message))
            return False
        else:
            return True

    def check_services(self):
        if self.all_available():
            logger.info('All services are available')
            self.set_wake_up()
        else:
            logger.info('Pausing bot')
            self.set_sleep()

    def _start_jobs(self):
        self.jobs = {
            'registry': self.registry(),
            'json_former': self.json_former()
        }

    def run(self):
        logger.info(
            'Start medicines registry bridge...',
            extra=journal_context({'MESSAGE_ID': BRIDGE_START}, dict())
        )

        self._start_jobs()

        while self.INFINITY_LOOP:
            gevent.sleep(self.delay)
            self.check_services()

            for name, job in self.jobs.items():
                if job.dead:
                    logger.warn('Restarting {} worker'.format(name))
                    self.jobs[name] = gevent.spawn(getattr(self, name))

            self.check_and_revive_jobs()

    def launch(self):
        while self.INFINITY_LOOP:
            if self.all_available():
                try:
                    self.run()
                    break
                except KeyboardInterrupt:
                    logger.info('Exiting...')
                    gevent.killall(self.jobs, timeout=5)

            gevent.sleep(self.delay)

    def check_and_revive_jobs(self):
        for name, job in self.jobs.items():
            if job.dead:
                self.revive_job(name)

    def revive_job(self, name):
        logger.warning(
            'Restarting {} worker'.format(name),
            extra=journal_context({'MESSAGE_ID': BRIDGE_RESTART_WORKER})
        )
        self.jobs[name] = gevent.spawn(getattr(self, name))

