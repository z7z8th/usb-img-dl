import site   # for cx_freeze to import symbol exit(1)
import io, os
import inspect
#import logging

import configs

from colored_print import *


def dbg(*msg):
    if(configs.debug):
        colored_print('green', None, None, *msg)


def info(*msg):
    colored_print('blue', None, None, *msg)


def warn(*msg):
    colored_print('magenta', None, ['bold'], *msg)


def err(*msg):
    colored_print('red', None, ['bold'], *msg)


def wtf(*msg):
    colored_print('red', None, ['bold'], *msg)
    colored_print('red', None, ['bold'], "exit....")
    exit(1)


def get_cur_func_name():
    return inspect.stack()[1][3]


def assert_number(n):
    assert(isinstance(n, int) or isinstance(n, long))
