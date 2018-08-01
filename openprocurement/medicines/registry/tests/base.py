# -*- coding: utf-8 -*-
import os
import unittest
import subprocess
import webtest

from time import sleep
from nose import tools
from bottle import Bottle, response, request
from gevent.pywsgi import WSGIServer
from redis import StrictRedis

from openprocurement.medicines.registry import VERSION
from openprocurement.medicines.registry.databridge.caching import DB


config = {
    'proxy_server': 'http://127.0.0.1',
    'proxy_port': 8008,
    'proxy_version': 1.0,
    'cache_db_name': 0,
    'cache_host': '127.0.0.1',
    'cache_port': '6379',
    'delay': 1,
    'time_update_at': '5:30:00',
    'registry_delay': 1,
    'json_files_delay': 1,
    'cache_monitoring_delay': 1,
    'file_cleaner_delay': 1
}


def setup_routing(app, func, path='/api/{}/health'.format(VERSION), method='GET'):
    app.route(path, method, func)


def response_spore():
    response.set_cookie(
        'SERVER_ID', (
            'a7afc9b1fc79e640f2487ba48243ca071c07a823d27'
            '8cf9b7adf0fae467a524747e3c6c6973262130fac2b'
            '96a11693fa8bd38623e4daee121f60b4301aef012c'
        )
    )
    return response


def proxy_response():
    if request.headers.get('sandbox-mode') != 'True':
        response.status = 400
    return response


class PrefixedRequestClass(webtest.app.TestRequest):
    @classmethod
    def blank(cls, path, *args, **kwargs):
        prefix = '/api/{}'.format(VERSION)

        if not path.startswith(prefix):
            path = prefix + path

        return webtest.app.TestRequest.blank(path, *args, **kwargs)


class BaseWebTest(unittest.TestCase):
    initial_auth = ('Basic', ('brokername', ''))
    relative_to = os.path.dirname(__file__)

    def setUp(self):
        self.app = webtest.TestApp('config:tests.ini', relative_to=self.relative_to)
        self.app.RequestClass = PrefixedRequestClass

        self.db = DB(config)
        self.valid_params = ['inn', 'atc', 'inn2atc', 'atc2inn']

    def tearDown(self):
        self.db.flushall()


@tools.nottest
class BaseServersTest(unittest.TestCase):
    relative_to = os.path.dirname(__file__)

    @classmethod
    def setUpClass(cls):
        cls.proxy_server_bottle = Bottle()
        cls.proxy_server = WSGIServer(('127.0.0.1', 8008), cls.proxy_server_bottle, log=None)
        setup_routing(cls.proxy_server_bottle, proxy_response, path='/api/{}/health'.format(VERSION))
        cls.redis_process = subprocess.Popen(
            ['redis-server', '--port', str(config.get('cache_port')), '--logfile /dev/null']
        )
        sleep(0.1)
        cls.redis = StrictRedis(port=str(config.get('cache_port')))
        cls.proxy_server.start()

    @classmethod
    def tearDownClass(cls):
        cls.proxy_server.close()
        cls.redis_process.terminate()
        cls.redis_process.wait()
        del cls.proxy_server_bottle

    def tearDown(self):
        del self.worker
        self.redis.flushall()

