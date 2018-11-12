import logging
import redis
from ConfigParser import ConfigParser

from rediscluster import StrictRedisCluster


logger = logging.getLogger(__name__)


class DB(object):
    def __init__(self, config):
        self.config = config
        cache_backend = self.config_get('cache_backend') or 'redis'

        if cache_backend == 'redis':
            self.__backend = cache_backend
            self.__host = self.config_get('cache_host') or '127.0.0.1'
            self.__port = self.config_get('cache_port') or 6379
            self.__db_name = self.config_get('cache_db_name') or 0

            self.db = redis.StrictRedis(host=self.__host, port=self.__port, db=self.__db_name)
        elif cache_backend == 'redis-cluster':
            self.__backend = cache_backend
            node1_host = self.config_get('node1_host')
            node1_port = self.config_get('node1_port')
            node2_host = self.config_get('node2_host')
            node2_port = self.config_get('node2_port')
            node3_host = self.config_get('node3_host')
            node3_port = self.config_get('node3_port')

            node4_host = self.config_get('node4_host')
            node4_port = self.config_get('node4_port')
            node5_host = self.config_get('node5_host')
            node5_port = self.config_get('node5_port')
            node6_host = self.config_get('node6_host')
            node6_port = self.config_get('node6_port')

            self.__host = (node1_host, node2_host, node3_host, node4_host, node5_host, node6_host)
            self.__port = (node1_port, node2_port, node3_port, node4_port, node5_port, node6_port)
            self.__db_name = 'cluster'

            cluster_nodes = [
                {'host': node1_host, 'port': node1_port},
                {'host': node2_host, 'port': node2_port},
                {'host': node3_host, 'port': node3_port},
                {'host': node4_host, 'port': node4_port},
                {'host': node5_host, 'port': node5_port},
                {'host': node6_host, 'port': node6_port}
            ]

            self.db = StrictRedisCluster(startup_nodes=cluster_nodes, decode_responses=True)

        self.set_value = self.db.set
        self.has_value = self.db.exists
        self.remove_value = self.db.delete

    def config_get(self, name):
        if isinstance(self.config, ConfigParser):
            return self.config.get('app:api', name)
        else:
            return self.config.get('app:api').get(name)

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

    def flushall(self):
        self.db.flushall()

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
