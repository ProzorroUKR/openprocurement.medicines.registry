from mock import MagicMock

from openprocurement.medicines.registry.tests.base import BaseServersTest, config
from openprocurement.medicines.registry.databridge.components import Registry


class TestRegistryWorker(BaseServersTest):
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



