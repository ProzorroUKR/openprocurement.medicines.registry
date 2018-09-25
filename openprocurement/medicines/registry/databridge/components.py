import os
import logging.config
import gevent
import json
from urllib2 import urlopen

from datetime import timedelta
from gevent import spawn, monkey
from openprocurement.medicines.registry.journal_msg_ids import (
    BRIDGE_INFO,
    BRIDGE_REGISTER,
    BRIDGE_FILE,
    BRIDGE_PARSER_ERROR,
    BRIDGE_CACHE
)
from openprocurement.medicines.registry.utils import (
    journal_context, decode_cp1251, get_now, get_file_last_modified, file_is_empty, XMLParser, string_time_to_datetime
)
from openprocurement.medicines.registry import DATA_PATH
from openprocurement.medicines.registry.databridge.base_worker import BaseWorker


monkey.patch_all()
logger = logging.getLogger(__name__)


class Registry(BaseWorker):
    def __init__(self, source_registry, time_update_at, delay, registry_delay, services_not_available):
        super(Registry, self).__init__(services_not_available)
        self.start_time = get_now()

        self.INFINITY_LOOP = True
        self.DATA_PATH = DATA_PATH
        self.registry_xml = os.path.join(self.DATA_PATH, 'registry.xml')

        self.source_registry = source_registry

        if type(time_update_at).__name__ == 'str':
            self.time_update_at = string_time_to_datetime(time_update_at or '05:30:00')
        else:
            self.time_update_at = time_update_at

        self.delay = delay
        self.registry_delay = registry_delay

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
        try:
            response = urlopen(self.source_registry)
        except ValueError:
            logger.info(
                'Error! Unknown url type: {}'.format(self.source_registry),
                extra=journal_context({'MESSAGE_ID': BRIDGE_REGISTER}, {})
            )
            return

        if response and response.code != 200:
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

        content = response.readlines()

        try:
            content = ''.join(map(decode_cp1251, content)).encode('utf-8').strip()
        except UnicodeDecodeError as e:
            logger.info(e)
            return

        self.save_registry(content)

        return content

    @property
    def registry_update_time(self):
        now = get_now()

        if self.time_update_at and (now.hour == self.time_update_at.hour):
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

    def _start_jobs(self):
        logger.info('Starting jobs...')
        jobs = {
            'update_local_registry': spawn(self.update_local_registry),
        }
        logger.info(str(jobs.keys()))
        return jobs

    def check_and_revive_jobs(self):
        for name, job in self.immortal_jobs.items():
            if job.dead and not job.value:
                self.revive_job(name)


class JsonFormer(BaseWorker):
    def __init__(self, db, delay, json_files_delay, cache_monitoring_delay, services_not_available):
        super(JsonFormer, self).__init__(services_not_available)
        self.start_time = get_now()

        self.INFINITY_LOOP = True
        self.DATA_PATH = DATA_PATH
        self.registry_xml = os.path.join(self.DATA_PATH, 'registry.xml')

        self.db = db
        self.delay = delay
        self.json_files_delay = json_files_delay
        self.cache_monitoring_delay = cache_monitoring_delay

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

        self.inn_json = os.path.join(self.DATA_PATH, 'inn.json')
        self.atc_json = os.path.join(self.DATA_PATH, 'atc.json')
        self.inn2atc_json = os.path.join(self.DATA_PATH, 'inn2atc.json')
        self.atc2inn_json = os.path.join(self.DATA_PATH, 'atc2inn.json')

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
            values = {v.decode('utf-8').lower(): v.decode('utf-8') for v in xml_parser.get_values(name) if v}
            self.inn_json_last_check = get_now()
        elif name == 'atc1':
            values = {v.decode('utf-8'): v.decode('utf-8') for v in xml_parser.get_values(name) if v}
            self.atc_json_last_check = get_now()
        elif name == 'inn2atc':
            values = xml_parser.inn2atc_atc2inn(root='inn')
            values = {k.lower(): v for k, v in values.items()}
            self.inn2atc_json_last_check = get_now()
        elif name == 'atc2inn':
            values = xml_parser.inn2atc_atc2inn(root='atc')
            values = {k: [i.lower() for i in v] for k, v in values.items()}
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
                data = dict()
            else:
                data = json.loads(f.read())

        if 'data' in data and set(values.keys()) == set(data.get('data').keys()):
            if name in ['inn2atc', 'atc2inn']:
                last_modified = lambda key: {
                    'inn2atc': get_file_last_modified(self.inn_json),
                    'atc2inn': get_file_last_modified(self.atc_json)
                }.get(key)

                data = dict(
                    data=values,
                    dateModified=str(last_modified(name))
                )
                with open(file_path, 'w') as f:
                    f.write(json.dumps(data))

                logger.info(
                    'DONE. Local {}.json file updated.'.format(name),
                    extra=journal_context({'MESSAGE_ID': BRIDGE_FILE}, {})
                )
                self._update_cache(name)
            else:
                logger.info(
                    '{} values in remote registry not changed. Skipping update local {}.json file'.format(
                        name, name
                    ),
                    extra=journal_context({'MESSAGE_ID': BRIDGE_FILE}, {})
                )
        else:
            with open(file_path, 'w') as f:
                data = dict(
                    data=values,
                    dateModified=str(get_file_last_modified(self.registry_xml))
                )
                f.write(json.dumps(data))

            logger.info(
                'DONE. Local {}.json file updated.'.format(name),
                extra=journal_context({'MESSAGE_ID': BRIDGE_FILE}, {})
            )
            self._update_cache(name)

    def update_json_files(self):
        while True:
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

            eq_valid_names = (('mnn', 'inn'), ('atc1', 'atc'), ('inn2atc', 'inn2atc'), ('atc2inn', 'atc2inn'))

            for name, eq_name in eq_valid_names:
                if file_is_empty(files_dict.get(eq_name)):
                    self.update_json(name)
                else:
                    if now.date() >= registry_last_modified.date():
                        last_check = last_check_dict.get(eq_name)

                        if not last_check or registry_last_modified.date() > last_check.date():
                            self.update_json(name)

            gevent.sleep(self.json_files_delay)

    def _update_cache(self, name):
        logger.info('Update cache for {}...'.format(name), extra=journal_context({'MESSAGE_ID': BRIDGE_INFO}, {}))
        file_path = os.path.join(self.DATA_PATH, '{}.json'.format(name))

        with open(file_path, 'r') as f:
            if not file_is_empty(file_path):
                data = json.loads(f.read())

                self.db.remove(name)
                self.db.put(name, data)

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
        while True:
            gevent.sleep(self.cache_monitoring_delay)

            for _, name in self.eq_valid_names.items():
                if not len(self.db.keys(name)) > 0:
                    self._update_cache(name)

    def _start_jobs(self):
        logger.info('Starting jobs...')
        jobs = {
            'update_json_files': spawn(self.update_json_files),
            'cache_monitoring': spawn(self.cache_monitoring)
        }
        logger.info(str(jobs.keys()))
        return jobs

    def check_and_revive_jobs(self):
        for name, job in self.immortal_jobs.items():
            if job.dead and not job.value:
                self.revive_job(name)
