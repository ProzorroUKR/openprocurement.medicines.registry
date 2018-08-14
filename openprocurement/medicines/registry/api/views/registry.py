import os
import json
import logging.config

from pyramid.view import view_defaults, view_config
from pyramid.response import FileResponse, Response
from openprocurement.medicines.registry.databridge.caching import DB
from openprocurement.medicines.registry import BASE_DIR
from openprocurement.medicines.registry.utils import str_to_obj, journal_context
from openprocurement.medicines.registry.journal_msg_ids import API_INFO

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

    @view_config(request_method='GET', permission='registry')
    def get(self):
        param = self.request.matchdict.get('param')

        if param in self.valid_params:
            try:
                data = str_to_obj(self.db.get(param))
            except ValueError:
                data = None
                logger.warn('Cache is empty!', extra=journal_context({'MESSAGE_ID': API_INFO}, {}))

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


