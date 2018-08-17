import os
import json

from webtest import TestApp

from openprocurement.medicines.registry.tests import base
from openprocurement.medicines.registry.databridge.caching import DB
from openprocurement.medicines.registry.tests.base import BaseWebTest, PrefixedRequestClass, config
from openprocurement.medicines.registry.api import ROUTE_PREFIX
from openprocurement.medicines.registry.utils import str_to_obj


class DumpsTestAppWebtest(TestApp):
    def do_request(self, req, status=None, expect_errors=None):
        req.headers.environ["HTTP_HOST"] = 'medicines-registry-sandbox.prozorro.gov.ua'
        if hasattr(self, 'file_obj') and not self.file_obj.closed:
            self.file_obj.write(req.as_bytes(True))
            self.file_obj.write("\n")
            if req.body:
                try:
                    self.file_obj.write(
                            'DATA:\n' + json.dumps(json.loads(req.body), indent=2, ensure_ascii=False).encode('utf8'))
                    self.file_obj.write("\n")
                except:
                    pass
            self.file_obj.write("\n")
        resp = super(DumpsTestAppWebtest, self).do_request(req, status=status, expect_errors=expect_errors)
        if hasattr(self, 'file_obj') and not self.file_obj.closed:
            headers = [(n.title(), v)
                       for n, v in resp.headerlist
                       if n.lower() != 'content-length']
            headers.sort()
            self.file_obj.write(str('Response: %s\n%s\n') % (
                resp.status,
                str('\n').join([str('%s: %s') % (n, v) for n, v in headers]),
            ))

            if resp.testbody:
                if 'data' in resp.testbody:
                    data = str_to_obj(resp.testbody)
                    data.update({'data': {k: data.get('data').get(k) for k in data.get('data').keys()[:20]}})

                    try:
                        self.file_obj.write(
                            json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
                        )
                    except:
                        pass
                else:
                    try:
                        self.file_obj.write(
                            json.dumps(json.loads(resp.testbody), indent=2, ensure_ascii=False).encode('utf8')
                        )
                    except:
                        pass
            self.file_obj.write("\n\n")
        return resp


class ApiTest(BaseWebTest):
    def setUp(self):
        self.app = DumpsTestAppWebtest('config:tests.ini', relative_to=os.path.dirname(base.__file__))
        self.app.RequestClass = PrefixedRequestClass

        self.db = DB(config)

    def test_docs(self):
        request_path = '{}/registry/'.format(ROUTE_PREFIX)

        with open('docs/source/tutorial/http/unauthorized-inn-get.http', 'w') as self.app.file_obj:
            response = self.app.get(request_path + 'inn.json', status=403)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.content_type, 'application/json')

        self.app.authorization = ('Basic', ('brokername', 'brokername'))

        with open('docs/source/tutorial/http/invalid-param-get.http', 'w') as self.app.file_obj:
            response = self.app.get(request_path + 'mnn.json', status=400)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.content_type, 'application/json')

        with open('docs/source/tutorial/http/inn-get.http', 'w') as self.app.file_obj:
            response = self.app.get(request_path + 'inn.json', status=200)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content_type, 'application/json')

        with open('docs/source/tutorial/http/atc-get.http', 'w') as self.app.file_obj:
            response = self.app.get(request_path + 'atc.json', status=200)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content_type, 'application/json')

        with open('docs/source/tutorial/http/inn2atc-get.http', 'w') as self.app.file_obj:
            response = self.app.get(request_path + 'inn2atc.json', status=200)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content_type, 'application/json')

        with open('docs/source/tutorial/http/atc2inn-get.http', 'w') as self.app.file_obj:
            response = self.app.get(request_path + 'atc2inn.json', status=200)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content_type, 'application/json')






