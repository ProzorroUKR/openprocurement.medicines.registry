# -*- coding: utf-8 -*-

# API main entry point


import logging.config
import gevent.monkey

from openprocurement.medicines.registry import VERSION
from openprocurement.medicines.registry.api.utils import (
    Root,
    auth_check,
    add_logging_context,
    set_logging_context,
    set_renderer,
    forbidden,
    request_params,
    read_users
)
from openprocurement.medicines.registry.auth import authenticated_role

gevent.monkey.patch_all()

ROUTE_PREFIX = '/api/{}'.format(VERSION)

logger = logging.getLogger(__name__)


def main(*args, **settings):
    from pyramid.config import Configurator
    from pyramid.events import NewRequest, ContextFound
    from pyramid.authentication import BasicAuthAuthenticationPolicy
    from pyramid.authorization import ACLAuthorizationPolicy
    from pyramid.renderers import JSON, JSONP

    logger.info('Start registry api...')
    read_users(settings['auth.file'])
    config = Configurator(
        autocommit=True,
        settings=settings,
        authentication_policy=BasicAuthAuthenticationPolicy(auth_check, __name__),
        authorization_policy=ACLAuthorizationPolicy(),
        root_factory=Root,
        route_prefix=ROUTE_PREFIX
    )

    config.include('pyramid_exclog')
    config.add_forbidden_view(forbidden)
    config.add_request_method(request_params, 'params', reify=True)
    config.add_request_method(authenticated_role, reify=True)
    config.add_renderer('prettyjson', JSON(indent=4))
    config.add_renderer('jsonp', JSONP(param_name='opt_jsonp'))
    config.add_renderer('prettyjsonp', JSONP(indent=4, param_name='opt_jsonp'))
    config.add_subscriber(add_logging_context, NewRequest)
    config.add_subscriber(set_logging_context, ContextFound)
    config.add_subscriber(set_renderer, NewRequest)
    config.add_route('health', '/health')
    config.add_route('registry', '/registry/{param}.json')
    config.scan('openprocurement.medicines.registry.api.views')
    return config.make_wsgi_app()

