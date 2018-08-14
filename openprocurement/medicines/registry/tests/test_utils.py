# -*- coding: utf-8 -*-
import os
import subprocess
import datetime

from unittest import TestCase
from pyramid import testing
from time import sleep
from redis import StrictRedis

from openprocurement.medicines.registry.api.utils import *
from openprocurement.medicines.registry.utils import (
    string_time_to_datetime,
    file_exists,
    file_is_empty,
    create_file,
    get_file_last_modified,
    str_to_obj,
    XMLParser
)
from openprocurement.medicines.registry import BASE_DIR
from openprocurement.medicines.registry.databridge.caching import DB
from openprocurement.medicines.registry.tests.utils import rm_dir


cache_config = {
    'main': {
        'cache_host': '127.0.0.1',
        'cache_port': '6379',
        'cache_db_name': 0
    }
}


class TestUtils(TestCase):
    __test__ = True

    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
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
        self.DATA_PATH = os.path.join(self.BASE_DIR, 'temp')

        if not os.path.exists(self.DATA_PATH):
            os.makedirs(self.DATA_PATH)

    @classmethod
    def tearDownClass(cls):
        cls.redis_process.terminate()
        cls.redis_process.wait()

    def tearDown(self):
        self.redis.flushall()
        self.DATA_PATH = os.path.join(self.BASE_DIR, 'temp')
        rm_dir(self.DATA_PATH)

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

    def test_db_remove(self):
        self.assertFalse(self.db.remove('key'))
        self.assertTrue(self.db.set_value('key', 'value'))
        self.assertEqual(self.db.get('key'), 'value')
        self.db.remove('key')
        self.assertIsNone(self.db.get('key'))

    def test_read_user(self):
        with open(os.path.join(BASE_DIR, 'tests/auth.ini'), 'r') as f:
            self.assertEqual(read_users(f), None)

    def test_request_params(self):
        request = testing.DummyRequest()
        self.assertEqual(request_params(request), NestedMultiDict())

    def test_request_params_exception(self):
        request = testing.DummyRequest().response
        self.assertRaises(Exception, lambda: request_params(request))

    def test_string_time_to_datetime(self):
        self.assertEqual(string_time_to_datetime(''), None)
        self.assertIsNotNone(string_time_to_datetime('00:00:00'))
        self.assertEquals(type(string_time_to_datetime('00:00:00')), type(datetime.datetime.now()))

    def test_file_exists(self):
        file_path = os.path.join(self.DATA_PATH, 'test_file')
        self.assertEqual(file_exists(file_path), False)

        with open(file_path, 'w'):
            pass

        self.assertEqual(file_exists(file_path), True)
        os.remove(file_path)

    def test_file_is_empty(self):
        file_path = os.path.join(self.DATA_PATH, 'test_file')

        with open(file_path, 'w'):
            pass

        self.assertEqual(file_is_empty(file_path), True)

        with open(file_path, 'w') as test_file:
            test_file.write('some_data')

        self.assertEqual(file_is_empty(file_path), False)
        os.remove(file_path)

    def test_create_file(self):
        file_path = os.path.join(self.DATA_PATH, 'test_file')

        self.assertEqual(file_exists(file_path), False)
        create_file(file_path)
        self.assertEqual(file_exists(file_path), True)
        os.remove(file_path)

    def test_get_file_last_modified(self):
        file_path = os.path.join(self.DATA_PATH, 'test_file')

        with open(file_path, 'w') as _:
            pass

        curr_time = datetime.datetime.now().replace(microsecond=0)
        self.assertEqual(get_file_last_modified(file_path), curr_time)
        self.assertNotEqual(get_file_last_modified(file_path), curr_time - datetime.timedelta(367647, 53971))
        self.assertEqual(get_file_last_modified('/some/wrong/file/path'), None)

    def test_str_to_obj(self):
        self.assertEqual(str_to_obj('\'test\''), 'test')
        self.assertEqual(str_to_obj('{1: 1}'), {1: 1})
        self.assertEqual(str_to_obj('''{'test': 'test'}'''), {'test': 'test'})
        self.assertEqual(str_to_obj('[1, 2, 3]'), [1, 2, 3])

        with self.assertRaises(SyntaxError):
            str_to_obj('')

        with self.assertRaises(TypeError):
            str_to_obj()

    def test_xml_parser_init(self):
        with self.assertRaises(TypeError):
            XMLParser()
        with self.assertRaises(TypeError):
            XMLParser(1)

    def test_xml_parser_get_values(self):
        with open(os.path.join(self.BASE_DIR, 'test_registry.xml'), 'r') as f:
            xml = f.read()

        xml = XMLParser(xml)
        self.assertEqual(xml.get_values('mnn'), {'Methyluracil'})
        self.assertEqual(xml.get_values('wrong_key'), {None})

    def test_inn2atc_atc2inn(self):
        with open(os.path.join(self.BASE_DIR, 'test_registry.xml'), 'r') as f:
            xml = f.read()

        xml = XMLParser(xml)

        self.assertEqual(xml.inn2atc_atc2inn('inn'), {u'Methyluracil': []})
        self.assertEqual(xml.inn2atc_atc2inn(123), {})
        self.assertEqual(xml.inn2atc_atc2inn('atc'), {})

        with self.assertRaises(TypeError):
            xml.inn2atc_atc2inn()

