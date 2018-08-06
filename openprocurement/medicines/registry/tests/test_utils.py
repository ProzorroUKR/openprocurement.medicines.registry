# -*- coding: utf-8 -*-
import os
import subprocess
import datetime

from unittest import TestCase
from pyramid import testing
from time import sleep
from redis import StrictRedis
from datetime import timedelta

from openprocurement.medicines.registry.api.utils import *
from openprocurement.medicines.registry import BASE_DIR
from openprocurement.medicines.registry.databridge.caching import DB
from openprocurement.medicines.registry.utils import *
from genshi.input import ParseError
from .small_xml import raw_xml


cache_config = {
    'main': {
        'cache_host': '127.0.0.1',
        'cache_port': '6379',
        'cache_db_name': 0
    }
}

xml = XMLParser(raw_xml)

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

    def test_decode_cp1251(self):
        self.assertEqual(decode_cp1251('test'), 'test'.decode('cp1251'))
        self.assertNotEqual('test'.encode('utf-32'), decode_cp1251('test'))


    def test_file_exists(self):
        file_path = BASE_DIR + '/test_file'
        self.assertEqual(file_exists(file_path), False)
        os.system('touch {}'.format(file_path))
        self.assertEqual(file_exists(file_path), True)
        os.system('rm {}'.format(file_path))


    def test_file_is_empty(self):
        file_path = BASE_DIR + '/test_file'
        os.system('touch {}'.format(file_path))
        self.assertEqual(file_is_empty(file_path), True)
        test_file = open(file_path, 'w')
        test_file.write('some_data')
        test_file.close()
        self.assertEqual(file_is_empty(file_path), False)
        os.system('rm {}'.format(file_path))

    def test_create_file(self):
        file_path = BASE_DIR + '/create_test_file'
        self.assertEqual(file_exists(file_path), False)
        create_file(file_path)
        self.assertEqual(file_exists(file_path), True)

    def test_get_file_last_modified(self):
        file_path = BASE_DIR + '/test_file'
        test_file = open(file_path, 'w')
        test_file.close()
        curr_time = datetime.now().replace(microsecond=0)
        self.assertEqual(get_file_last_modified(file_path), curr_time)
        self.assertNotEqual(get_file_last_modified(file_path), curr_time-timedelta(367647, 53971))
        self.assertEqual(get_file_last_modified('/some/wrong/file/path'), None)

    def test_string_time_to_datetime(self):
        now = datetime.now().replace(microsecond=0)
        now_time_str = '{}:{}:{}'.format(now.hour, now.minute, now.second)
        self.assertEqual(string_time_to_datetime(now_time_str), now)
        self.assertRaises(ValueError, string_time_to_datetime, time= '')
        self.assertRaises(ValueError, string_time_to_datetime)

    def test_journal_context(self):
        expected_res =  {'JOURNAL_test_key': 'test_val'}
        params = {'test_key': 'test_val'}
        self.assertEqual(journal_context(params=params), expected_res)
        self.assertEqual(journal_context(), {})
        with self.assertRaises(AttributeError):
            journal_context(params=1)

    def test_str_to_obj(self):
        self.assertEqual(str_to_obj('\'test\''), 'test')
        self.assertEqual(str_to_obj('{1: 1}'), {1: 1})
        self.assertEqual(str_to_obj('''{'test': 'test'}'''), {'test': 'test'})
        with self.assertRaises(SyntaxError):
            str_to_obj('')
        with self.assertRaises(TypeError):
            str_to_obj()


    def test_xml_parser_init(self):
        with self.assertRaises(TypeError):
            XMLParser()
        with self.assertRaises(TypeError):
            XMLParser(1)
#        self.assertEqual(type(id(XMLParser(xml))), type(1))

    def test_xml_parser_get_values(self):
        self.assertEqual(xml.get_values('mnn'), {'Comb drug', 'Umifenovir'})
        self.assertEqual(xml.get_values('wrong_key'), {None})

    def test_inn2atc_atc2inn(self):
        self.assertEqual(xml.inn2atc_atc2inn('inn'), {u'Comb drug': [], u'Umifenovir': []})
        self.assertEqual(xml.inn2atc_atc2inn(123), {})
        self.assertEqual(xml.inn2atc_atc2inn('atc'), {})
        with self.assertRaises(TypeError):
            xml.inn2atc_atc2inn()

