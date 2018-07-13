# -*- coding: utf-8 -*-
import json
from pyramid.view import view_config
from pyramid.response import Response


@view_config(route_name='health', renderer='json', request_method='GET')
def health(request):
    data = {'method': request.method, 'success': True}
    return Response(body=json.dumps(data), content_type='application/json', status=200)
