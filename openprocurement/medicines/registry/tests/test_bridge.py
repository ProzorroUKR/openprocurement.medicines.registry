import os

from mock import patch, MagicMock
from restkit import RequestError
from requests import RequestException
from gevent.event import Event

from openprocurement.medicines.registry.tests.base import BaseServersTest, config
from openprocurement.medicines.registry.databridge.bridge import MedicinesRegistryBridge
from openprocurement.medicines.registry.client import ProxyClient
from openprocurement.medicines.registry.utils import file_exists, file_is_empty
from openprocurement.medicines.registry.tests.utils import rm_dir, custom_sleep


class TestBridgeWorker(BaseServersTest):
    __test__ = True

    def test_init(self):
        self.worker = MedicinesRegistryBridge(config)
        self.assertEqual(self.worker.delay, config.get('delay'))
        self.assertTrue(isinstance(self.worker.proxy_client, ProxyClient))
        self.assertTrue(self.worker.services_not_available.is_set())
        self.assertEqual(self.worker.db.backend, 'redis')
        self.assertEqual(self.worker.db.db_name, 0)
        self.assertEqual(self.worker.db.port, '6379')
        self.assertEqual(self.worker.db.host, '127.0.0.1')

    def test_start_jobs(self):
        self.worker = MedicinesRegistryBridge(config)
        registry, json_former = [MagicMock(return_value=i) for i in range(2)]
        self.worker.registry = registry
        self.worker.json_former = json_former

        self.worker._start_jobs()

        self.assertTrue(registry.called)
        self.assertTrue(json_former.called)

        self.assertEqual(self.worker.jobs['registry'], 0)
        self.assertEqual(self.worker.jobs['json_former'], 1)

    def test_files_init(self):
        self.worker = MedicinesRegistryBridge(config)
        self.worker.BASE_DIR = self.BASE_DIR
        self.DATA_PATH = os.path.join(self.worker.BASE_DIR, 'data')
        self.assertFalse(os.path.exists(self.DATA_PATH))

        self.worker._files_init()

        self.registry_xml = os.path.join(self.DATA_PATH, 'registry.xml')
        self.inn_json = os.path.join(self.DATA_PATH, 'inn.json')
        self.atc_json = os.path.join(self.DATA_PATH, 'atc.json')
        self.inn2atc_json = os.path.join(self.DATA_PATH, 'inn2atc.json')
        self.atc2inn_json = os.path.join(self.DATA_PATH, 'atc2inn.json')

        self.DATA_PATH = os.path.join(self.worker.BASE_DIR, 'data')
        self.assertTrue(os.path.exists(self.DATA_PATH))
        self.assertTrue(file_exists(self.registry_xml))
        self.assertTrue(file_exists(self.inn_json))
        self.assertTrue(file_exists(self.atc_json))
        self.assertTrue(file_exists(self.inn2atc_json))
        self.assertTrue(file_exists(self.atc2inn_json))

        self.assertTrue(file_is_empty(self.registry_xml))
        rm_dir(self.DATA_PATH)

    def test_proxy_server(self):
        self.worker = MedicinesRegistryBridge(config)
        self.worker.sandbox_mode = 'True'
        self.proxy_server.stop()
        with self.assertRaises(RequestException):
            self.worker.check_proxy()
        self.proxy_server.start()
        self.assertTrue(self.worker.check_proxy())

    def test_proxy_server_mock(self):
        self.worker = MedicinesRegistryBridge(config)
        self.worker.proxy_client = MagicMock(health=MagicMock(side_effect=RequestError()))

        with self.assertRaises(RequestError):
            self.worker.check_proxy()

        self.worker.proxy_client = MagicMock(return_value=True)
        self.assertTrue(self.worker.check_proxy())

    def test_proxy_server_success(self):
        self.worker = MedicinesRegistryBridge(config)
        self.worker.sandbox_mode = 'True'
        self.assertTrue(self.worker.check_proxy())

    def test_proxy_sandbox_mismatch(self):
        self.worker = MedicinesRegistryBridge(config)
        self.worker.sandbox_mode = 'False'

        with self.assertRaises(RequestException):
            self.worker.check_proxy()

        self.worker.sandbox_mode = 'True'
        self.assertTrue(self.worker.check_proxy())

    def test_check_services(self):
        self.worker = MedicinesRegistryBridge(config)
        self.worker.services_not_available = MagicMock(set=MagicMock(), clear=MagicMock())
        self.worker.check_services()
        self.assertTrue(self.worker.services_not_available.clear.called)
        self.worker.check_services()
        self.assertFalse(self.worker.services_not_available.set.called)

    def test_check_services_mock(self):
        self.worker = MedicinesRegistryBridge(config)
        self.worker = MagicMock()
        self.worker.set_wake_up = MagicMock()
        self.worker.set_sleep = MagicMock()
        self.worker.check_services()
        self.assertFalse(self.worker.set_wake_up.called)
        self.worker.check_services()
        self.assertFalse(self.worker.set_sleep.called)

    def test_available_service(self):
        self.worker = MedicinesRegistryBridge(config)
        self.worker.sandbox_mode = 'True'

        self.proxy_server.stop()

        with self.assertRaises(RequestException):
            self.worker.check_proxy()

        self.assertFalse(self.worker.all_available())

        self.worker.check_services()
        self.proxy_server.start()
        self.assertTrue(self.worker.all_available())

    def test_sleep_wakeup(self):
        self.worker = MedicinesRegistryBridge(config)
        self.assertTrue(isinstance(self.worker.services_not_available, Event))

        self.assertEqual(self.worker.services_not_available.set(), None)

    @patch('gevent.killall')
    def test_run_exception(self, killlall):
        self.worker = MedicinesRegistryBridge(config)
        self.worker.delay = 1
        self.worker._start_jobs = MagicMock(return_value={'a': 1})
        self.worker.check_and_revive_jobs = MagicMock(side_effect=Exception('test error'))
        self.worker.run()
        killlall.assert_called_once_with([1], timeout=5)

        self.db.flushall()

    @patch('gevent.killall')
    @patch('gevent.sleep')
    def test_run_exception(self, gevent_sleep, killlall):
        self.worker = MedicinesRegistryBridge(config)
        gevent_sleep.side_effect = custom_sleep
        self.worker._start_jobs = MagicMock(return_value={'a': 1})
        self.worker.check_and_revive_jobs = MagicMock(side_effect=Exception('test error'))

        with self.assertRaises(AttributeError):
            self.worker.run()
        with self.assertRaises(AssertionError):
            killlall.assert_called_once_with([1], timeout=5)

        self.db.flushall()

    @patch('gevent.sleep')
    def test_launch(self, gevent_sleep):
        self.worker = MedicinesRegistryBridge(config)
        self.worker.run = MagicMock()
        self.worker.all_available = MagicMock(return_value=True)
        self.worker.launch()
        self.worker.run.assert_called_once()

        self.db.flushall()

    def test_check_and_revive_jobs(self):
        self.worker = MedicinesRegistryBridge(config)
        self.worker.jobs = {'test': MagicMock(dead=MagicMock(return_value=True))}
        self.worker.revive_job = MagicMock()
        self.worker.check_and_revive_jobs()
        self.worker.revive_job.assert_called_once_with('test')

    def test_revive_job(self):
        self.worker = MedicinesRegistryBridge(config)
        self.worker.test = MagicMock()
        self.worker.jobs = {'test': MagicMock(dead=MagicMock(return_value=True))}
        self.worker.revive_job('test')
        self.assertEqual(self.worker.jobs['test'].dead, False)
