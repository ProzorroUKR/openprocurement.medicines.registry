# -*- coding: utf-8 -*-
import os
import pkg_resources

from logging import getLogger

try:
    PKG = pkg_resources.get_distribution(__package__)
    LOGGER = getLogger(PKG.project_name)
    LOGGER.info(PKG.parsed_version)
    VERSION = '1.0'
#    VERSION = '{}.{}'.format(
#        int(PKG.parsed_version[0]), int(PKG.parsed_version[1]) if PKG.parsed_version[1].isdigit() else 0
#    )
except pkg_resources.DistributionNotFound:
    LOGGER = getLogger('openprocurement.medicines.registry')
    VERSION = '1.0'

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data')

