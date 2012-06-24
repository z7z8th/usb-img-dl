import io, os
import inspect
#import logging
from termcolor import colored

from config import *

def dbg(msg):
    if(debug):
        print colored(msg, 'magenta')


def info(msg):
    print colored(msg, 'green')


def warn(msg):
    print colored(msg, 'magenta', attrs = ['bold'])


def err(msg):
    print colored(msg, 'red', attrs = ['bold'])


def wtf(msg):
    print colored(msg, 'red', attrs = ['bold'])
    print colored('exit...', 'red', attrs = ['bold'])
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
