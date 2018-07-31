import os
import unittest
import subprocess
from openprocurement.medicines.registry.tests.base import BaseWebTest
import json

valid_params = ['inn', 'atc', 'inn2atc', 'atc2inn']
reg_prefix = '/api/1.0/registry/'
reg_addr_inn = '/api/1.0/registry/inn.json'
health_addr = '/api/1.0/health'

class TestApi(BaseWebTest):

    def test_registry_valid_params(self):
        for param in valid_params:
            self.app.authorization = self.initial_auth
            response = self.app.get('{}{}.json'.format(reg_prefix, param), )
            self.assertNotEqual(response.status_code, 200)

    def test_registry_invalid_params(self):
        invalid_params = [' ', '123', 'qwe', 'V']
        invalid_response = u'URL parameter "{}" not valid. URL parameter must be "inn.json", \
                                               "atc.json", "inn2atc.json" or "atc2inn.json"'

        for param in invalid_params:
            self.app.authorization = ('Basic', ('brokername', 'brokername'))
            response = self.app.get('{}{}.json'.format(reg_prefix, param), status=400)
            self.assertEqual(response.status_code, 400)


    def test_registry_unallowed_methods(self):
        for param in valid_params:
            post_response = self.app.post('{}{}.json'.format(reg_prefix, param))
            self.assertEqual(post_response.status_code, 404)
            put_response = self.app.put('{}{}.json'.format(reg_prefix, param))
            self.assertEqual(put_response.status_code, 404)
            patch_response = self.app.patch('{}{}.json'.format(reg_prefix, param))
            self.assertEqual(patch_response.status_code, 404)
            delete_response = self.app.delete('{}{}.json'.format(reg_prefix, param))
            self.assertEqual(delete_response.status_code, 404)

    def test_response_content_type(self):
        headers = {'Content-Type': 'application/json'}
        for param in valid_params:
            self.app.authorization = self.initial_auth
            response = self.app.get('{}{}.json'.format(reg_prefix, param), headers=headers)
            self.assertEqual(response.headers['Content-Type'], 'application/json')

    def test_registry_existing_of_test_val(self):
        test_vals = {'inn': 'betaxolol',
                     'atc': 'B02AB01',
                     'inn2atc': 'omoconazole',
                     'atc2inn': 'J05AF30'}
        for k, v in test_vals.items():
            self.app.authorization = ('Basic', ('brokername', 'brokername'))
            response = self.app.get('{}{}.json'.format(reg_prefix, k), status=400)
            self.assertNotEqual(None, json.loads(response.text).get(v))

    def test_registry_invalid_api_version(self):
        for param in valid_params:
            self.app.authorization = ('Basic', ('brokername', 'brokername'))
            response = self.app.get('/api/2.0/registry/{}.json'.format(param))
            self.assertNotEqual(response.status_code, 200)

    def test_health_get(self):
        response = self.app.get('/api/1.0/health')
        success_response =  {u'method': u'GET', u'success': True}
        self.app.authorization = ('Basic', ('brokername', 'brokername'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.text), success_response)