import logging
import redis
from ConfigParser import ConfigParser


logger = logging.getLogger(__name__)


class DB(object):
    def __init__(self, config):
        self.config = config

        self.__backend = 'redis'
        self.__host = self.config_get('cache_host') or '127.0.0.1'
        self.__port = self.config_get('cache_port') or 6379
        self.__db_name = self.config_get('cache_db_name') or 0

        self.db = redis.StrictRedis(host=self.__host, port=self.__port, db=self.__db_name)

        self.set_value = self.db.set
        self.has_value = self.db.exists
        self.remove_value = self.db.delete

    def config_get(self, name):
        if isinstance(self.config, ConfigParser):
            return self.config.get('app:api', name)
        else:
            return self.config.get(name)

    def get(self, key):
        return self.db.get(key)

    def keys(self, prefix):
        keys = self.db.keys(prefix)
        return keys

    def put(self, key, value, ex=90000):
        self.set_value(key, value, ex)

    def remove(self, key):
        self.remove_value(key)

    def has(self, key):
        return self.has_value(key)

    def scan_iter(self, prefix=None):
        return [key for key in self.db.scan_iter(prefix)]

    def remove_pattern(self, prefix):
        for key in self.db.scan_iter(prefix):
            self.remove(key)

    @property
    def backend(self):
        return self.__backend

    @property
    def host(self):
        return self.__host

    @property
    def port(self):
        return self.__port

    @property
    def db_name(self):
        return self.__db_name
