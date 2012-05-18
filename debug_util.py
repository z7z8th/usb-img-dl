import io, os
#import logging
from termcolor import colored


def info(msg):
    print msg


def warn(msg):
    print colored(msg, 'magenta', attrs = ['bold'])


def err(msg):
    print colored(msg, 'red', attrs = ['bold'])


def wtf(msg):
    print colored(msg, 'red', attrs = ['bold'])
    print colored('exit...', 'red', attrs = ['bold'])
    exit(1)
