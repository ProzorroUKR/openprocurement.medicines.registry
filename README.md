# openprocurement.medicines.registry

## Description
Service for obtaining up-to-date information on the medicines registry (State Register of Drugs of Ukraine - Державний реєстр лікарських засобів України) and formation json`s for the return to site.
Synchronization with the remote registry is occurs every day at 5.30 am.


## Installation
* clone repository
* python bootstrap.py
* ./bin/buildout -N

## Requirements
* python 2.7.13
* setuptools 18.3.2
* redis

## Run tests
./bin/nosetests