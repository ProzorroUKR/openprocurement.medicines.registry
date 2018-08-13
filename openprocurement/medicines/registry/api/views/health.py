# -*- coding: utf-8 -*-
import json
from pyramid.view import view_config
from pyramid.response import Response

from openprocurement.medicines.registry.utils import SANDBOX_MODE


@view_config(route_name='health', renderer='json', request_method='GET')
def health(request):
    if SANDBOX_MODE and request.headers.get('sandbox-mode', str(SANDBOX_MODE)).lower() != 'true':
        request.response.status = '400 Sandbox modes mismatch between proxy and bot'

    data = {'method': request.method, 'success': True}
    return Response(body=json.dumps(data), content_type='application/json', status=200)
