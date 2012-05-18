import io, os
#import logging
from termcolor import colored


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

