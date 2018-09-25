# -*- coding: utf-8 -*-
import shutil

from gevent import sleep


def custom_sleep(seconds=0):
    return sleep(seconds=0)


class AlmostAlwaysFalse(object):
    def __init__(self, total_iterations=1):
        self.total_iterations = total_iterations
        self.current_iteration = 0

    def __nonzero__(self):
        if self.current_iteration < self.total_iterations:
            self.current_iteration += 1
            return bool(0)
        return bool(1)


def rm_dir(path_dir):
    shutil.rmtree(path=path_dir)


