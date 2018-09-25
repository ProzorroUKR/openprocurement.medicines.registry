import json

from gevent import event

from openprocurement.medicines.registry.tests.base import BaseWebTest
from openprocurement.medicines.registry.api import ROUTE_PREFIX
from openprocurement.medicines.registry.databridge.components import JsonFormer
from openprocurement.medicines.registry.tests.base import config
from openprocurement.medicines.registry.utils import str_to_obj


INITIAL_ATC_KEYS_DATA = [
    u'J07BD52', u'J07BD54', u'C07BB12', u'C02AA04', u'C09DX01', u'C09DX04', u'B05AA', u'G01AX06',
    u'P03AX05', u'G01AX05', u'P03AX01', u'N02AA51', u'S01GX08', u'S01GX09', u'S01GX07', u'S01GX01',
    u'B02AA01', u'B02AA02', u'G04CX', u'G04CB02', u'G04CB01', u'G01AA10', u'J01', u'J06BB16', u'D07AB09'
]

INITIAL_INN_KEYS_DATA = [
    u"allergen extracts", u"betaxolol", u"telmisartan", u"trastuzumab", u"omoconazole",
    u"zidovudine and lamivudine", u"procainamide", u"troxerutin, combinations", u"ivabradine",
    u"pantoprazole", u"vincamine", u"degarelix", u"citalopram", u"glimepiride", u"lincomycin"
]


class TestApi(BaseWebTest):
    def test_api_with_invalid_params(self):
        request_path = '{}/registry/'.format(ROUTE_PREFIX)
        response = self.app.get(request_path + '.json', status=404)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content_type, 'text/plain')

        response = self.app.get(request_path + 'some_param.json', status=403)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(
            response.json['errors'][0],
            {u'description': u'Forbidden', u'name': u'permission', u'location': u'url'}
        )

        self.app.authorization = ('Basic', ('brokername', 'brokername'))

        response = self.app.get(request_path + 'some_param.json', status=400)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(
            response.json['message'],
            u'{} {}'.format(
                'URL parameter "some_param" not valid.',
                'URL parameter must be "inn.json", "atc.json", "inn2atc.json" or "atc2inn.json"'
            )
        )

        response = self.app.get(request_path + 'ATC.json', status=400)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(
            response.json['message'],
            u'{} {}'.format(
                'URL parameter "ATC" not valid.',
                'URL parameter must be "inn.json", "atc.json", "inn2atc.json" or "atc2inn.json"'
            )
        )

        response = self.app.get(request_path + 'some_param', status=404)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content_type, 'text/plain')

    def test_api_with_valid_params(self):
        self.app.authorization = ('Basic', ('brokername', 'brokername'))
        request_path = '{}/registry/'.format(ROUTE_PREFIX)

        # get ATC data without cache
        response = self.app.get(request_path + 'atc.json', status=200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = response.json
        self.assertTrue(any([True for i in INITIAL_ATC_KEYS_DATA if i in data.get('data')]))
        self.assertFalse(self.db.get('atc'))

        # get ATC data with cache
        services_not_available = event.Event()
        services_not_available.set()

        json_former = JsonFormer(
            self.db, delay=config.get('delay'),
            json_files_delay=config.get('json_files_delay'),
            cache_monitoring_delay=config.get('cache_monitoring_delay'),
            services_not_available=services_not_available
        )
        json_former._update_cache('atc')

        response = self.app.get(request_path + 'atc.json', status=200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = response.json
        self.assertTrue(self.db.get('atc'))
        self.assertTrue(any([True for i in INITIAL_ATC_KEYS_DATA if i in data.get('data')]))
        self.assertEqual(data, str_to_obj(self.db.get('atc')))

        # get INN data without cache
        response = self.app.get(request_path + 'inn.json', status=200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = response.json
        self.assertTrue(any([True for i in INITIAL_INN_KEYS_DATA if i in data.get('data')]))
        self.assertFalse(self.db.get('inn'))

        # get INN data with cache
        json_former._update_cache('inn')

        response = self.app.get(request_path + 'inn.json', status=200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = response.json
        self.assertTrue(self.db.get('inn'))
        self.assertTrue(any([True for i in INITIAL_INN_KEYS_DATA if i in data.get('data')]))
        self.assertEqual(data, str_to_obj(self.db.get('inn')))

        # get INN2ATC data without cache
        response = self.app.get(request_path + 'inn2atc.json', status=200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = response.json
        self.assertTrue(any([True for i in INITIAL_INN_KEYS_DATA if i in data.get('data')]))
        self.assertFalse(self.db.get('inn2atc'))

        # get INN2ATC data with cache
        json_former._update_cache('inn2atc')

        response = self.app.get(request_path + 'inn2atc.json', status=200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = response.json
        self.assertTrue(self.db.get('inn2atc'))
        self.assertTrue(any([True for i in INITIAL_INN_KEYS_DATA if i in data.get('data')]))
        self.assertEqual(data, str_to_obj(self.db.get('inn2atc')))

        # get ATC2INN data without cache
        response = self.app.get(request_path + 'atc2inn.json', status=200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = response.json
        self.assertTrue(any([True for i in INITIAL_ATC_KEYS_DATA if i in data.get('data')]))
        self.assertFalse(self.db.get('atc2inn'))

        # get ATC2INN data with cache
        json_former._update_cache('atc2inn')

        response = self.app.get(request_path + 'atc2inn.json', status=200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = response.json
        self.assertTrue(self.db.get('atc2inn'))
        self.assertTrue(any([True for i in INITIAL_ATC_KEYS_DATA if i in data.get('data')]))
        self.assertEqual(data, str_to_obj(self.db.get('atc2inn')))

    def test_registry_invalid_api_version(self):
        for param in self.valid_params:
            self.app.authorization = ('Basic', ('brokername', 'brokername'))
            response = self.app.get('/api/2.0/registry/{}.json'.format(param), status=404)
            self.assertEqual(response.status_code, 404)

    def test_registry_unallowed_methods(self):
        request_path = '{}/registry/'.format(ROUTE_PREFIX)

        for param in self.valid_params:
            post_response = self.app.post(request_path + '{}.json'.format(param), status=404)
            self.assertEqual(post_response.status_code, 404)
            put_response = self.app.put(request_path + '{}.json'.format(param), status=404)
            self.assertEqual(put_response.status_code, 404)
            patch_response = self.app.patch(request_path + '{}.json'.format(param), status=404)
            self.assertEqual(patch_response.status_code, 404)
            delete_response = self.app.delete(request_path + '{}.json'.format(param), status=404)
            self.assertEqual(delete_response.status_code, 404)

    def test_health_get(self):
        response = self.app.get('/api/1.0/health')
        success_response = {u'method': u'GET', u'success': True}
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.text), success_response)
