import os
import logging.config
import gevent
import json

from datetime import timedelta
from urllib2 import urlopen
from gevent import monkey
from openprocurement.medicines.registry.utils import (
    journal_context, get_now, get_file_last_modified,
    string_time_to_datetime, decode_cp1251, file_exists,
    create_file, file_is_empty, XMLParser, get_file_name, delete_file,
    get_directory_files
)
from openprocurement.medicines.registry.journal_msg_ids import (
    BRIDGE_START, BRIDGE_INFO, BRIDGE_REGISTER, BRIDGE_FILE, BRIDGE_PARSER_ERROR, BRIDGE_CACHE, BRIDGE_RESTART_SYNC,
    BRIDGE_RESTART_CACHE_MONITORING
)
from openprocurement.medicines.registry.databridge.caching import DB
from openprocurement.medicines.registry import BASE_DIR


monkey.patch_all()

logger = logging.getLogger(__name__)


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

        self.time_update_at = string_time_to_datetime(self.config_get('time_update_at') or '05:00:00')
        self.delay = int(self.config_get('delay')) or 60
        self.registry_delay = int(self.config_get('registry_delay')) or 60
        self.json_files_delay = int(self.config_get('json_files_delay')) or 10
        self.file_cleaner_delay = int(self.config_get('file_cleaner_delay')) or 10
        self.cache_monitoring_delay = int(self.config_get('cache_monitoring_delay')) or 10

        self.source_registry = self.config_get('source_registry')

        self.inn_json_last_check = None
        self.atc_json_last_check = None
        self.inn2atc_json_last_check = None
        self.atc2inn_json_last_check = None

        self.eq_valid_names = {
            'mnn': 'inn',
            'atc1': 'atc',
            'inn2atc': 'inn2atc',
            'atc2inn': 'atc2inn'
        }

        self._files_init()

    def config_get(self, name):
        return self.config.get('app:api', name)

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

    def save_registry(self, xml):
        logger.info(
            'Save response to \'registry.xml\' file...',
            extra=journal_context({'MESSAGE_ID': BRIDGE_REGISTER}, {})
        )

        with open(os.path.join(self.DATA_PATH, 'registry.xml'), 'w') as f:
            f.write(xml)
            logger.info(
                'File \'registry.xml\' saved at: {}.'.format(get_now()),
                extra=journal_context({'MESSAGE_ID': BRIDGE_REGISTER}, {})
            )

    def get_registry(self):
        logger.info('Get remote registry...', extra=journal_context({'MESSAGE_ID': BRIDGE_INFO}, {}))
        response = urlopen(self.source_registry)

        if response.code != 200:
            logger.info(
                'Error! Server response status: {}. Sending a second request...'.format(response.code),
                extra=journal_context({'MESSAGE_ID': BRIDGE_REGISTER}, {})
            )
            return
        else:
            logger.info(
                'Server response status: {}'.format(response.code),
                extra=journal_context({'MESSAGE_ID': BRIDGE_REGISTER}, {})
            )

        response = response.readlines()

        try:
            response = ''.join(map(decode_cp1251, response)).encode('utf-8').strip()
        except UnicodeDecodeError as e:
            logger.info(e)
            return

        self.save_registry(response)

        return response

    @property
    def registry_update_time(self):
        now = get_now()

        if now.hour == self.time_update_at.hour:
            check_to_time = self.time_update_at + timedelta(minutes=30)

            if self.time_update_at.minute <= now.minute and now.replace(tzinfo=None).time() <= check_to_time.time():
                return True
            else:
                return False
        else:
            return False

    def update_local_registry(self):
        while self.INFINITY_LOOP:
            now = get_now()
            last_modified = get_file_last_modified(self.registry_xml)

            conditions = (
                now.date() > last_modified.date() and self.registry_update_time, file_is_empty(self.registry_xml)
            )

            if any(conditions):
                logger.info(
                    'Update local registry file...',
                    extra=journal_context({'MESSAGE_ID': BRIDGE_REGISTER}, {})
                )
                self.get_registry()
            else:
                logger.info(
                    'Registry file is updated.',
                    extra=journal_context({'MESSAGE_ID': BRIDGE_REGISTER}, {})
                )
            gevent.sleep(self.registry_delay)

    def update_json(self, name):
        logger.info(
            'Update local {}.json file...'.format(self.eq_valid_names.get(name)),
            extra=journal_context({'MESSAGE_ID': BRIDGE_INFO}, {})
        )

        file_path = os.path.join(self.DATA_PATH, '{}.json'.format(self.eq_valid_names.get(name)))

        if file_is_empty(self.registry_xml):
            logger.info('Local {}.json file not updated. Registry file is empty.'.format(
                self.eq_valid_names.get(name)),
                extra=journal_context({'MESSAGE_ID': BRIDGE_FILE}, {})
            )
            return

        with open(self.registry_xml) as registry:
            xml_parser = XMLParser(registry.read())

        if name == 'mnn':
            values = [v.decode('utf-8') for v in xml_parser.get_values(name) if v]
            self.inn_json_last_check = get_now()
        elif name == 'atc1':
            values = list()

            for atc in ['atc1', 'atc2', 'atc3']:
                values.extend(xml_parser.get_values(atc))

            values = [v.decode('utf-8') for v in set(values) if v]
            self.atc_json_last_check = get_now()
        elif name == 'inn2atc':
            values = xml_parser.inn2atc_atc2inn(root='inn')
            self.inn2atc_json_last_check = get_now()
        elif name == 'atc2inn':
            values = xml_parser.inn2atc_atc2inn(root='atc')
            self.atc2inn_json_last_check = get_now()
        else:
            logger.warn(
                'Error! Incorrect xml tag.',
                extra=journal_context({'MESSAGE_ID': BRIDGE_PARSER_ERROR}, {})
            )
            return

        name = self.eq_valid_names.get(name)

        with open(file_path, 'r') as f:
            if file_is_empty(file_path):
                data = list()
            else:
                data = json.loads(f.read())

        if set(values) == set(data):
            if name in ['inn2atc', 'atc2inn']:
                with open(file_path, 'w') as f:
                    f.write(json.dumps(values))

                logger.info(
                    'DONE. Local {}.json file updated.'.format(name),
                    extra=journal_context({'MESSAGE_ID': BRIDGE_FILE}, {})
                )
                self.__update_cache(name)
            else:
                logger.info(
                    '{} values in remote registry not changed. Skipping update local {}.json file'.format(
                        name, name
                    ),
                    extra=journal_context({'MESSAGE_ID': BRIDGE_FILE}, {})
                )
        else:
            with open(file_path, 'w') as f:
                f.write(json.dumps(values))

            logger.info(
                'DONE. Local {}.json file updated.'.format(name),
                extra=journal_context({'MESSAGE_ID': BRIDGE_FILE}, {})
            )
            self.__update_cache(name)

    def update_json_files(self):
        while self.INFINITY_LOOP:
            now = get_now()
            registry_last_modified = get_file_last_modified(self.registry_xml)

            last_check_dict = {
                'inn': self.inn_json_last_check, 'atc': self.atc_json_last_check,
                'inn2atc': self.inn2atc_json_last_check, 'atc2inn': self.atc2inn_json_last_check
            }
            files_dict = {
                'inn': self.inn_json, 'atc': self.atc_json,
                'inn2atc': self.inn2atc_json, 'atc2inn': self.atc2inn_json
            }

            for name, eq_name in self.eq_valid_names.items():
                if file_is_empty(files_dict.get(eq_name)):
                    self.update_json(name)
                else:
                    if now.date() >= registry_last_modified.date():
                        last_check = last_check_dict.get(eq_name)
                        if not last_check or registry_last_modified.date() > last_check.date():
                            self.update_json(name)

            gevent.sleep(self.json_files_delay)

    def __update_cache(self, name):
        logger.info('Update cache for {}...'.format(name), extra=journal_context({'MESSAGE_ID': BRIDGE_INFO}, {}))
        file_path = os.path.join(self.DATA_PATH, '{}.json'.format(name))

        with open(file_path, 'r') as f:
            if not file_is_empty(file_path):
                data = json.loads(f.read())

                self.db.remove_pattern('{}:*'.format(name))

                if name in ['inn2atc', 'atc2inn']:
                    for k, v in data.items():
                        self.db.put('{}:{}'.format(name, self.db.key_creation(k)), {k: v})
                else:
                    for i in data:
                        self.db.put('{}:{}'.format(name, self.db.key_creation(i)), i)

                logger.info(
                    'Cache updated for {}.'.format(name),
                    extra=journal_context({'MESSAGE_ID': BRIDGE_CACHE}, {})
                )
            else:
                logger.warn(
                    'Cache not updated for {}. Registry file is empty.'.format(name),
                    extra=journal_context({'MESSAGE_ID': BRIDGE_CACHE}, {})
                )

    def cache_monitoring(self):
        while self.INFINITY_LOOP:
            gevent.sleep(self.cache_monitoring_delay)

            for _, name in self.eq_valid_names.items():
                if not len(self.db.keys('{}:*'.format(name))) > 0:
                    self.__update_cache(name)

    def __delete_file(self, prefix):
        file_path = os.path.join(self.DATA_PATH, '{}.json'.format(prefix))
        last_modified_file = get_file_last_modified(file_path)

        for file_path in get_directory_files(self.DATA_PATH, prefix='{}-*'.format(prefix)):
            if get_file_name(file_path) != '{}-{}.json'.format(prefix, last_modified_file.date()):
                logger.info(
                    'Delete old file {}'.format(get_file_name(file_path)),
                    extra=journal_context({'MESSAGE_ID': BRIDGE_INFO}, {})
                )
                delete_file(file_path)

    def files_deleting(self):
        while self.INFINITY_LOOP:
            gevent.sleep(self.file_cleaner_delay)

            for prefix in ['inn', 'atc', 'inn2atc', 'atc2inn']:
                self.__delete_file(prefix)

    def __start_sync_workers(self):
        self.jobs = (
            gevent.spawn(self.update_local_registry),
            gevent.spawn(self.update_json_files)
        )

    def __start_cache_monitoring_worker(self):
        self.cache_monitoring_worker = gevent.spawn(self.cache_monitoring)

    def __start_file_cleaner_worker(self):
        self.file_cleaner_worker = gevent.spawn(self.files_deleting)

    def __restart_sync_workers(self):
        logger.warn(
            'Restarting sync workers...',
            extra=journal_context({'MESSAGE_ID': BRIDGE_RESTART_SYNC}, {})
        )

        for j in self.jobs:
            j.kill()

        self.__start_sync_workers()
        logger.info(
            'Restart sync workers completed.',
            extra=journal_context({'MESSAGE_ID': BRIDGE_INFO}, {})
        )

    def __restart_cache_monitoring_worker(self):
        logger.warn(
            'Restart cache monitoring worker...',
            extra=journal_context({'MESSAGE_ID': BRIDGE_RESTART_CACHE_MONITORING}, {})
        )

        self.cache_monitoring_worker.kill()
        self.__start_cache_monitoring_worker()

        logger.info(
            'Restart cache monitoring worker completed.',
            extra=journal_context({'MESSAGE_ID': BRIDGE_INFO}, {})
        )

    def __restart_file_cleaner_worker(self):
        logger.warn(
            'Restart file cleaner worker...',
            extra=journal_context({'MESSAGE_ID': BRIDGE_INFO}, {})
        )
        self.file_cleaner_worker.kill()
        self.__start_file_cleaner_worker()

        logger.info(
            'Restart file cleaner worker completed.',
            extra=journal_context({'MESSAGE_ID': BRIDGE_INFO}, {})
        )

    def run(self):
        logger.info(
            'Start medicines registry bridge...',
            extra=journal_context({'MESSAGE_ID': BRIDGE_START}, dict())
        )

        self.__start_sync_workers()
        self.__start_cache_monitoring_worker()
        self.__start_file_cleaner_worker()

        registry_updater, json_files_updater = self.jobs
        cache_monitoring_worker = self.cache_monitoring_worker

        while self.INFINITY_LOOP:
            gevent.sleep(self.delay)

            if registry_updater.dead or json_files_updater.dead:
                self.__restart_sync_workers()
                registry_updater, json_files_updater = self.jobs

            if cache_monitoring_worker.dead:
                self.__restart_cache_monitoring_worker()
                cache_monitoring_worker = self.cache_monitoring_worker

    def launch(self):
        try:
            self.run()
        except KeyboardInterrupt:
            logger.info('Exiting...')

