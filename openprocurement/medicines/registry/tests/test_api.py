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
            response = self.app.get(reg_prefix+'{}.json'.format(param))
            self.assertEqual(response.status_code, 200)

    def test_registry_invalid_params(self):
        invalid_params = [' ', '123', 'qwe', 'V']
        for param in valid_params:
            response = self.app.get(reg_prefix+'{}.json'.format(param))
            self.assertEqual(response.status_code, 400)

    def test_registry_unallowed_methods(self):
        for param in valid_params:
            post_response = self.app.post(reg_prefix+'{}.json'.format(param))
            self.assertEqual(post_response.status_code, 404)
            put_response = self.app.put(reg_prefix+'{}.json'.format(param))
            self.assertEqual(put_response.status_code, 404)
            patch_response = self.app.patch(reg_prefix+'{}.json'.format(param))
            self.assertEqual(patch_response.status_code, 404)
            delete_response = self.app.delete(reg_prefix+'{}.json'.format(param))
            self.assertEqual(delete_response.status_code, 404)

    def test_response_content_type(self):
        for param in valid_params:
            response = self.app.get(reg_prefix+'{}.json'.format(param))
            self.assertEqual(response.headers['Content-Type'], 'application/json')

    def test_registry_existing_of_test_val(self):
        test_vals = {'inn': 'betaxolol',
                     'atc': 'B02AB01',
                     'inn2atc': 'omoconazole',
                     'atc2inn': 'J05AF30'}
        for k, v in test_vals.items():
            response = reg_prefix + '{}.json'.format(k)
            self.assertNotEqual(None, json.loads(response.text).get(v))
    def test_registry_invalid_api_version(self):
        for param in valid_params:
            response = self.app.get('/api/2.0/registry/{}.json'.format(param))
            self.assertNotEqual(response.status_code, 200)

    def test_health_get(self):
        response = self.app.get('/api/1.0/health')
        self.assertEqual(response.status_code, 200)

    def test_health_success_response(self):
        expect_response = {'method': 'GET', 'success': True}
        response = json.loads(self.app.get(health_addr).text)
        self.app.assertEqual(response, expect_response)