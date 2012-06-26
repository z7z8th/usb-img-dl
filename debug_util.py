import io, os
import inspect
#import logging
from colored_print import *

from config import *

def dbg(*msg):
    if(debug):
        colored_print('blue',None, None, *msg)


def info(*msg):
    colored_print('green',None, None, *msg)


def warn(*msg):
    colored_print('magenta',None, ['bold'], *msg)


def err(*msg):
    colored_print('red',None, ['bold'], *msg)


def wtf(*msg):
    colored_print('red',None, ['bold'], *msg)
    colored_print('red',None, ['bold'], "exit....")
    exit(1)

def print_str_hex(str):
    for x in str:
        print "0x%02x" % ord(x),
    print

def print_int_arr_hex(str):
    for x in str:
        print "0x%02x" % x,
    print

def get_cur_func_name():
    return inspect.stack()[1][3]
