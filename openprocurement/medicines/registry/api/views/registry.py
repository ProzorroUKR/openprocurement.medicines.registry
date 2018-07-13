import os
import json
import logging.config

from pyramid.view import view_defaults, view_config
from pyramid.response import FileResponse, Response
from openprocurement.medicines.registry.databridge.caching import DB
from openprocurement.medicines.registry import BASE_DIR
from openprocurement.medicines.registry.utils import get_file_last_modified, file_exists, strings_to_dict

logger = logging.getLogger(__name__)


@view_defaults(route_name='registry')
class RegistryView(object):
    def __init__(self, request):
        self.request = request
        self.DATA_PATH = os.path.join(BASE_DIR, 'data')

        db_config = {'app:api': {
            'cache_host': self.request.registry.settings.get('cache_host'),
            'cache_port': self.request.registry.settings.get('cache_port'),
            'cache_db_name': self.request.registry.settings.get('cache_db_name'),
        }}
        self.db = DB(db_config)

        self.valid_params = ['inn', 'atc', 'inn2atc', 'atc2inn']

    @view_config(request_method='GET', permission='view')
    def get(self):
        param = self.request.matchdict.get('param')

        if param in self.valid_params:
            if param in ['inn2atc', 'atc2inn']:
                data = strings_to_dict(map(self.db.get, self.db.scan_iter('{}:*'.format(param))))
            else:
                data = filter(lambda value: value, map(self.db.get, self.db.scan_iter('{}:*'.format(param))))

            if data:
                response = Response(body=json.dumps(data), content_type='application/json', status=200)
            else:
                file_path = os.path.join(self.DATA_PATH, '{}.json'.format(param))
                response = FileResponse(path=file_path, request=self.request, content_type='application/json')
        else:
            msg = 'URL parameter must be "inn.json", "atc.json", "inn2atc.json" or "atc2inn.json"'
            data = {
                'success': False,
                'error': True,
                'message': 'URL parameter "{}" not valid. {}'.format(param, msg)
            }
            response = Response(body=json.dumps(data), content_type='application/json', status=400)

        return response


@view_defaults(route_name='registry_file')
class RegistryFileView(RegistryView):
    @view_config(request_method='GET', permission='view')
    def get(self):
        param = self.request.matchdict.get('param')

        if param in self.valid_params:
            source_file_path = os.path.join(self.DATA_PATH, '{}.json'.format(param))
            file_name = '{}-{}.json'.format(
                param, get_file_last_modified(source_file_path).replace(tzinfo=None).strftime('%Y-%m-%d')
            )
            file_path = os.path.join(self.DATA_PATH, file_name)

            if file_exists(file_path):
                response = FileResponse(path=file_path, request=self.request, content_type='application/json')
                response.headers['Content-Disposition'] = ('attachment; filename={}'.format(file_name))
                return response

            if param in ['inn2atc', 'atc2inn']:
                data = strings_to_dict(map(self.db.get, self.db.scan_iter('{}:*'.format(param))))
            else:
                data = filter(lambda value: value, map(self.db.get, self.db.scan_iter('{}:*'.format(param))))

            if data:
                with open(file_path, 'w') as f:
                    f.write(json.dumps(data))

                response = FileResponse(path=file_path, request=self.request, content_type='application/json')
                response.headers['Content-Disposition'] = ('attachment; filename={}'.format(file_name))
            else:
                with open(source_file_path, 'r') as f:
                    data = json.loads(f.read())

                with open(file_path, 'w') as f:
                    f.write(json.dumps(data))

                response = FileResponse(path=file_path, request=self.request, content_type='application/json')
                response.headers['Content-Disposition'] = ('attachment; filename={}'.format(file_name))
        else:
            msg = 'URL parameter must be "inn.json", "atc.json", "inn2atc.json" or "atc2inn.json"'
            data = {
                'success': False,
                'error': True,
                'message': 'URL parameter "{}" not valid. {}'.format(param, msg)
            }
            response = Response(body=json.dumps(data), content_type='application/json', status=400)

        return response


