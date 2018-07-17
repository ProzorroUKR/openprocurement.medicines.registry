#!/bin/sh
virtualenv --clear --never-download .
./bin/pip install -r requirements.txt
yes | .bin/pip install setuptools==18.3.2 --user
python bootstrap.py