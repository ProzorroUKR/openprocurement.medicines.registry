from mock import patch, MagicMock
from restkit import RequestError

from openprocurement.medicines.registry.tests.base import BaseServersTest, config
from openprocurement.medicines.registry.databridge.bridge import MedicinesRegistryBridge
from openprocurement.medicines.registry.client import ProxyClient


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

    def test_proxy_server_mock(self):
        self.worker = MedicinesRegistryBridge(config)
        self.worker.proxy_client = MagicMock(health=MagicMock(side_effect=RequestError()))
        with self.assertRaises(RequestError):
            self.worker.check_proxy()

        self.worker.proxy_client = MagicMock(return_value=True)
        self.assertTrue(self.worker.check_proxy())

    @patch('gevent.sleep')
    def test_launch(self, gevent_sleep):
        self.worker = MedicinesRegistryBridge(config)
        self.worker.run = MagicMock()
        self.worker.all_available = MagicMock(return_value=True)
        self.worker.launch()
        self.worker.run.assert_called_once()

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
