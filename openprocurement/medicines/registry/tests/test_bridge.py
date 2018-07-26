from mock import patch, MagicMock

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

    @patch('gevent.sleep')
    def test_bridge_run(self, sleep):
        self.worker = MedicinesRegistryBridge(config)
        registry, json_former = [MagicMock() for _ in range(2)]

        self.worker.registry = registry
        self.worker.json_former = json_former

