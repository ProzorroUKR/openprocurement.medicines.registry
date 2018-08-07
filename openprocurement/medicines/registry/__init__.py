# -*- coding: utf-8 -*-
import os
from logging import getLogger
from pkg_resources import get_distribution


PKG = get_distribution(__package__)
LOGGER = getLogger(PKG.project_name)
VERSION = '{}.{}'.format(
    int(PKG.parsed_version[0]), int(PKG.parsed_version[1]) if PKG.parsed_version[1].isdigit() else 0
)
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data')

