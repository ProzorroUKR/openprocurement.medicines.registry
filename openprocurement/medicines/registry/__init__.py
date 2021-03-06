# -*- coding: utf-8 -*-
import os
import pkg_resources

from logging import getLogger

try:
    PKG = pkg_resources.get_distribution(__package__)
    logger = getLogger(PKG.project_name)
    VERSION = '{}.{}'.format(
        int(PKG.parsed_version[0]), int(PKG.parsed_version[1]) if PKG.parsed_version[1].isdigit() else 0
    )
except pkg_resources.DistributionNotFound:
    logger = getLogger('openprocurement.medicines.registry')
    VERSION = '0.0'

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data')

