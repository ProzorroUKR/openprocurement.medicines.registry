# -*- coding: utf-8 -*-

# Bridge main entry point


import os
import argparse
import logging.config

from ConfigParser import SafeConfigParser

from openprocurement.medicines.registry.databridge.bridge import MedicinesRegistryBridge


logger = logging.getLogger(__name__)


def main(*args, **settings):
    parser = argparse.ArgumentParser(description='Medicines registry')
    parser.add_argument('config', type=str, help='Path to config file')
    params = parser.parse_args()

    if os.path.isfile(params.config):
        config = SafeConfigParser()
        config.read(params.config)
        logging.config.fileConfig(params.config)
        MedicinesRegistryBridge(config).launch()
    else:
        logger.info('Invalid configuration file. Exiting...')


if __name__ == '__main__':
    main()
