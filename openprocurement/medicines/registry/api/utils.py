import logging.config

from hashlib import sha512
from json import dumps
from pyramid.security import Allow, Everyone
from pyramid.httpexceptions import exception_response
from webob.multidict import NestedMultiDict

from openprocurement.medicines.registry import VERSION
from openprocurement.medicines.registry.journal_msg_ids import API_ERROR_HANDLER


logger = logging.getLogger(__name__)

USERS = dict()


class Root(object):
    __name__ = None
    __parent__ = None
    __acl__ = [(Allow, Everyone, 'view')]

    def __init__(self, request):
        self.request = request


def authenticated_role(request):
    principals = request.effective_principals
    groups = [g for g in reversed(principals) if g.startswith('g:')]
    return groups[0][2:] if groups else 'anonymous'


def auth_check(username, password):
    if username in USERS and USERS[username]['password'] == sha512(password).hexdigest():
        return ['g:{}'.format(USERS[username]['group'])]


def add_logging_context(event):
    request = event.request
    params = {
        'API_VERSION': VERSION,
        'TAGS': 'python,api',
        'USER': str(request.authenticated_userid or ''),
        'ROLE': str(request.authenticated_role or ''),
        'CURRENT_URL': request.url,
        'CURRENT_PATH': request.path_info,
        'REMOTE_ADDR': request.remote_addr or '',
        'USER_AGENT': request.user_agent or '',
        'REQUEST_METHOD': request.method,
        'REQUEST_ID': request.environ.get('REQUEST_ID', ''),
        'CLIENT_REQUEST_ID': request.headers.get('X-Client-Request-ID', ''),
    }

    request.logging_context = params


def update_logging_context(request, params):
    if not request.__dict__.get('logging_context'):
        request.logging_context = {}

    for x, j in params.items():
        request.logging_context[x.upper()] = j


def set_logging_context(event):
    request = event.request
    params = dict()
    params['ROLE'] = str(request.authenticated_role)

    if request.params:
        params['PARAMS'] = str(dict(request.params))

    update_logging_context(request, params)


def set_renderer(event):
    request = event.request
    try:
        json = request.json_body
    except ValueError:
        json = {}
    pretty = isinstance(json, dict) and json.get('options', {}).get('pretty') or request.params.get('opt_pretty')
    accept = request.headers.get('Accept')
    jsonp = request.params.get('opt_jsonp')
    if jsonp and pretty:
        request.override_renderer = 'prettyjsonp'
        return True
    if jsonp:
        request.override_renderer = 'jsonp'
        return True
    if pretty:
        request.override_renderer = 'prettyjson'
        return True
    if accept == 'application/yaml':
        request.override_renderer = 'yaml'
        return True


def context_unpack(request, msg, params=None):
    if params:
        update_logging_context(request, params)

    logging_context = request.logging_context
    journal_context = msg

    for key, value in logging_context.items():
        journal_context['JOURNAL_{}'.format(key)] = value

    return journal_context


def error_handler(request, status, error):
    params = {
        'ERROR_STATUS': status
    }

    for key, value in error.items():
        params['ERROR_{}'.format(key)] = str(value)

    logger.info(
        'Error on processing request \'{}\''.format(dumps(error)),
        extra=context_unpack(request, {'MESSAGE_ID': API_ERROR_HANDLER}, params)
    )
    request.response.status = status
    request.response.content_type = 'application/json'

    return {'status': 'error', 'errors': [error]}


def request_params(request):
    try:
        params = NestedMultiDict(request.GET, request.POST)
    except UnicodeDecodeError:
        response = exception_response(422)
        response.body = dumps(
            error_handler(request, response.code, {
                'location': 'body',
                'name': 'data',
                'description': 'Could not decode params'
            })
        )
        response.content_type = 'application/json'
        raise response
    except Exception as e:
        response = exception_response(422)
        response.body = dumps(
            error_handler(request, response.code, {
                'location': 'body',
                'name': str(e.__class__.__name__),
                'description': str(e)
            })
        )
        response.content_type = 'application/json'
        raise response
    return params


def forbidden(request):
    request.response.json_body = error_handler(
        request, 403, {'location': 'url', 'name': 'permission', 'description': 'Forbidden'}
    )
    return request.response
