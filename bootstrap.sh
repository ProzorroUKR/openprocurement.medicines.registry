#!/bin/sh
virtualenv --clear --never-download .
./bin/pip install -r requirements.txt
#/usr/bin/pip install setuptools==18.3.2 --user
#/usr/bin/python bootstrap.py
