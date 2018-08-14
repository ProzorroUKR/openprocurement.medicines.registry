import os

from mock import MagicMock, patch

from openprocurement.medicines.registry.tests.base import BaseServersTest, config
from openprocurement.medicines.registry.databridge.components import Registry, JsonFormer
from openprocurement.medicines.registry.utils import (
    file_is_empty, file_exists, string_time_to_datetime, get_now, create_file, str_to_obj
)


class TestRegistry(BaseServersTest):
    __test__ = True

    def test_init(self):
        self.worker = Registry(
            config.get('source_registry'), config.get('time_update_at'), config.get('delay'),
            config.get('registry_delay'), config.get('services_not_available')
        )
        self.assertEqual(self.worker.delay, config.get('delay'))
        self.assertEqual(None, self.worker.services_not_available)

    def test_start_jobs(self):
        self.worker = Registry(
            config.get('source_registry'), config.get('time_update_at'), config.get('delay'),
            config.get('registry_delay'), config.get('services_not_available')
        )
        update_local_registry = MagicMock(return_value=1)
        self.worker.update_local_registry = update_local_registry
        self.worker._start_jobs()
        self.assertFalse(update_local_registry.called)

        with self.assertRaises(AttributeError):
            jobs = self.worker.jobs

    def test_get_registry(self):
        self.worker = Registry(
            config.get('source_registry'), config.get('time_update_at'), config.get('delay'),
            config.get('registry_delay'), config.get('services_not_available')
        )

        self.worker.DATA_PATH = self.DATA_PATH
        self.assertTrue(file_is_empty(os.path.join(self.worker.DATA_PATH, 'registry.xml')))
        self.worker.source_registry = 'some_url'
        registry = self.worker.get_registry()
        self.assertEqual(registry, None)
        self.assertTrue(file_is_empty(os.path.join(self.worker.DATA_PATH, 'registry.xml')))

        self.worker.source_registry = 'http://www.drlz.com.ua/'
        self.worker.get_registry()
        self.assertFalse(file_is_empty(os.path.join(self.worker.DATA_PATH, 'registry.xml')))

    def test_save_registry(self):
        self.worker = Registry(
            config.get('source_registry'), config.get('time_update_at'), config.get('delay'),
            config.get('registry_delay'), config.get('services_not_available')
        )

        self.worker.DATA_PATH = self.DATA_PATH
        self.assertTrue(file_exists(os.path.join(self.worker.DATA_PATH, 'registry.xml')))
        self.assertTrue(file_is_empty(os.path.join(self.worker.DATA_PATH, 'registry.xml')))

        self.worker.save_registry('<?xml version="1.0" encoding="Windows-1251"?>')
        self.assertFalse(file_is_empty(os.path.join(self.worker.DATA_PATH, 'registry.xml')))

    def test_registry_update_time(self):
        self.worker = Registry(
            config.get('source_registry'), config.get('time_update_at'), config.get('delay'),
            config.get('registry_delay'), config.get('services_not_available')
        )
        self.worker.time_update_at = string_time_to_datetime('00:00:00')
        self.assertFalse(self.worker.registry_update_time)
        self.worker.time_update_at = get_now()
        self.assertTrue(self.worker.registry_update_time)

    def test_update_local_registry(self):
        self.worker = Registry(
            config.get('source_registry'), config.get('time_update_at'), config.get('delay'),
            config.get('registry_delay'), config.get('services_not_available')
        )
        start_jobs = self.worker._start_jobs()
        self.assertEquals(start_jobs.keys(), ['update_local_registry'])

        for name, job in start_jobs.items():
            self.assertTrue(job.started)
            self.assertFalse(job.dead)
            job.kill()
            self.assertFalse(job.started)
            self.assertTrue(job.dead)

    @patch('gevent.sleep')
    def test_update_local_registry(self, gevent_sleep):
        self.worker = Registry(
            config.get('source_registry'), config.get('time_update_at'), config.get('delay'),
            config.get('registry_delay'), config.get('services_not_available')
        )
        self.worker._start_jobs()

    def test_check_and_revive_jobs(self):
        self.worker = Registry(
            config.get('source_registry'), config.get('time_update_at'), config.get('delay'),
            config.get('registry_delay'), config.get('services_not_available')
        )
        self.worker.jobs = {'test': MagicMock(dead=MagicMock(return_value=True))}
        self.worker.revive_job = MagicMock()

        with self.assertRaises(AttributeError):
            self.worker.check_and_revive_jobs()

        with self.assertRaises(AssertionError):
            self.worker.revive_job.assert_called_once_with('test')


class TestJsonFormer(BaseServersTest):
    __test__ = True

    def test_init(self):
        self.worker = JsonFormer(
            self.db, config.get('delay'), config.get('json_files_delay'),
            config.get('cache_monitoring_delay'), config.get('services_not_available')
        )

        self.assertEqual(self.worker.delay, config.get('delay'))
        self.assertEqual(None, self.worker.services_not_available)

    def test_start_jobs(self):
        self.worker = JsonFormer(
            self.db, config.get('delay'), config.get('json_files_delay'),
            config.get('cache_monitoring_delay'), config.get('services_not_available')
        )

        update_json_files, cache_monitoring = [MagicMock(return_value=i) for i in range(2)]
        self.worker.update_json_files = update_json_files
        self.worker.cache_monitoring = cache_monitoring

        self.worker._start_jobs()

        self.assertFalse(update_json_files.called)
        self.assertFalse(cache_monitoring.called)

        with self.assertRaises(AttributeError):
            jobs = self.worker.jobs

    def test_update_json(self):
        self.worker = JsonFormer(
            self.db, config.get('delay'), config.get('json_files_delay'),
            config.get('cache_monitoring_delay'), config.get('services_not_available')
        )

        self.worker.DATA_PATH = self.DATA_PATH
        self.worker.registry_xml = os.path.join(self.worker.DATA_PATH, 'registry.xml')
        self.worker.inn_json = os.path.join(self.worker.DATA_PATH, 'inn.json')
        self.worker.atc_json = os.path.join(self.worker.DATA_PATH, 'atc.json')
        self.worker.inn2atc_json = os.path.join(self.worker.DATA_PATH, 'inn2atc.json')
        self.worker.atc2inn_json = os.path.join(self.worker.DATA_PATH, 'atc2inn.json')

        # updates json`s with empty registry
        self.assertTrue(file_exists(os.path.join(self.worker.DATA_PATH, 'registry.xml')))
        self.assertTrue(file_is_empty(os.path.join(self.worker.DATA_PATH, 'registry.xml')))

        json_names = ['mnn', 'atc1', 'inn2atc', 'atc2inn']
        for name in json_names:
            self.assertEqual(self.worker.update_json(name), None)

        # updates json`s with registry with invalid data
        with open(os.path.join(self.BASE_DIR, 'test_registry.xml'), 'r') as f:
            xml = f.read()

        with open(os.path.join(self.worker.DATA_PATH, 'registry.xml'), 'w') as f:
            f.write(xml)

        self.assertFalse(file_is_empty(os.path.join(self.worker.DATA_PATH, 'registry.xml')))

        # update json`s with invalid xml tag
        self.assertEqual(self.worker.update_json('xxx'), None)

        # update inn json with valid xml tag
        self.assertEqual(file_exists(self.worker.inn_json), False)
        self.assertEqual(file_exists(self.worker.atc_json), False)

        create_file(os.path.join(self.worker.DATA_PATH, 'inn.json'))
        create_file(os.path.join(self.worker.DATA_PATH, 'atc.json'))
        create_file(os.path.join(self.worker.DATA_PATH, 'inn2atc.json'))
        create_file(os.path.join(self.worker.DATA_PATH, 'atc2inn.json'))

        self.assertEqual(file_exists(self.worker.inn_json), True)
        self.assertEqual(file_is_empty(self.worker.inn_json), True)

        self.assertEqual(file_exists(self.worker.atc_json), True)
        self.assertEqual(file_is_empty(self.worker.atc_json), True)

        self.assertFalse(file_is_empty(self.worker.registry_xml))

        self.worker.update_json('mnn')
        self.assertFalse(file_is_empty(self.worker.inn_json))

        self.worker.update_json('atc1')
        self.assertFalse(file_is_empty(self.worker.atc_json))

        self.worker.update_json('inn2atc')
        self.assertFalse(file_is_empty(self.worker.inn2atc_json))

        self.worker.update_json('atc2inn')
        self.assertFalse(file_is_empty(self.worker.atc2inn_json))

        # check cache
        cache = self.db.get('inn')
        self.assertEqual(str_to_obj(cache).get('data'), {u'methyluracil': u'Methyluracil'})

        cache = self.db.get('atc')
        self.assertEqual(str_to_obj(cache).get('data'), {})

        cache = self.db.get('inn2atc')
        self.assertIn(u'methyluracil', str_to_obj(cache).get('data'))

        if file_is_empty(self.worker.atc2inn_json):
            cache = self.db.get('atc2inn')
            self.assertEqual(str_to_obj(cache).get('data'), {})
        else:
            cache = self.db.get('atc2inn')
            with open(self.worker.atc2inn_json) as f:
                data = f.read()

            if str_to_obj(data).get('data'):
                self.assertEqual(str_to_obj(data).get('data'), str_to_obj(cache).get('data'))
            else:
                self.assertEqual(str_to_obj(data).get('data'), dict())

        self.db.flushall()
        self.assertEqual(self.db.has('inn'), False)

        self.worker._update_cache('inn')
        self.assertEqual(self.db.has('inn'), True)

    @patch('gevent.sleep')
    def test_start_jobs(self, gevent_sleep):
        self.worker = JsonFormer(
            self.db, config.get('delay'), config.get('json_files_delay'),
            config.get('cache_monitoring_delay'), config.get('services_not_available')
        )
        self.worker._start_jobs()

    def test_check_and_revive_jobs(self):
        self.worker = JsonFormer(
            self.db, config.get('delay'), config.get('json_files_delay'),
            config.get('cache_monitoring_delay'), config.get('services_not_available')
        )
        self.worker.jobs = {'test': MagicMock(dead=MagicMock(return_value=True))}
        self.worker.revive_job = MagicMock()

        with self.assertRaises(AttributeError):
            self.worker.check_and_revive_jobs()

        with self.assertRaises(AssertionError):
            self.worker.revive_job.assert_called_once_with('test')



