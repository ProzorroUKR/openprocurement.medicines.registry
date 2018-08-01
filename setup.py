from setuptools import setup, find_packages

version = '1.0.0'

requires = [
    'setuptools',
    'chaussette',
    'gevent',
    'retrying',
    'pytz',
    'redis',
    'pyramid',
    'request_id_middleware',
    'server_cookie_middleware'
]

test_requires = requires + [
    'webtest',
    'python-coveralls',
    'mock==1.0.1',
    'requests_mock==1.3.0',
    'bottle'
]

bridge_requires = requires + [
    'requests',
    'iso8601'
]

api_requires = requires + [
    'pyramid_exclog'
]

docs_requires = requires + [
    'sphinxcontrib-httpdomain',
]

entry_points = {
    'paste.app_factory': [
        'main = openprocurement.medicines.registry.api:main'
    ],
    'console_scripts': [
        'medicines_registry = openprocurement.medicines.registry.databridge:main',
        'medicines_registry_api = openprocurement.medicines.registry.api:main',
        'main = openprocurement.medicines.registry.api:main'
    ]
}

setup(
    name='openprocurement.medicines.registry',
    version=version,
    description="",
    long_description=open("README.md").read(),
    classifiers=[
        "Framework :: Pylons",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application"
    ],
    keywords='',
    author='Quintagroup, Ltd.',
    author_email='info@quintagroup.com',
    license='Apache License 2.0',
    url='https://github.com/ProzorroUKR/openprocurement.medicines.registry',
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    extras_require={
        'api': api_requires,
        'bot': bridge_requires,
        'test': test_requires,
        'docs': docs_requires,
    },
    entry_points=entry_points
)
