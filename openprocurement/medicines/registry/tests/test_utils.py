# -*- coding: utf-8 -*-
import os
import subprocess

from unittest import TestCase
from pyramid import testing
from time import sleep
from redis import StrictRedis

from openprocurement.medicines.registry.api.utils import *
from openprocurement.medicines.registry import BASE_DIR
from openprocurement.medicines.registry.databridge.caching import DB


cache_config = {
    'main': {
        'cache_host': '127.0.0.1',
        'cache_port': '6379',
        'cache_db_name': 0
    }
}


class TestUtils(TestCase):
    __test__ = True

    relative_to = os.path.dirname(__file__)
    redis = None
    redis_process = None
    PORT = 6379

    @classmethod
    def setUpClass(cls):
        cls.redis_process = subprocess.Popen(['redis-server', '--port', str(cls.PORT), '--logfile /dev/null'])
        sleep(0.1)
        cls.db = DB(cache_config)
        cls.redis = StrictRedis(port=cls.PORT)

    def setUp(self):
        self.config = testing.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.redis_process.terminate()
        cls.redis_process.wait()

    def tearDown(self):
        self.redis.flushall()

    def test_db_init(self):
        self.assertEqual(self.db.backend, 'redis')
        self.assertEqual(self.db.db_name, 0)
        self.assertEqual(self.db.port, 6379)
        self.assertEqual(self.db.host, '127.0.0.1')

    def test_db_get(self):
        self.assertIsNone(self.db.get('111'))
        self.db.put('111', 'test data')
        self.assertEqual(self.db.get('111'), 'test data')

    def test_db_set(self):
        self.db.put('111', 'test data')
        self.assertEqual(self.db.get('111'), 'test data')

    def test_db_has(self):
        self.assertFalse(self.db.has('111'))
        self.db.put('111', 'test data')
        self.assertTrue(self.db.has('111'))

    def test_read_user(self):
        with open(os.path.join(BASE_DIR, 'tests/auth.ini'), 'r') as f:
            self.assertEqual(read_users(f), None)

    def test_request_params(self):
        request = testing.DummyRequest()
        self.assertEqual(request_params(request), NestedMultiDict())

    def test_request_params_exception(self):
        request = testing.DummyRequest().response
        self.assertRaises(Exception, lambda: request_params(request))

