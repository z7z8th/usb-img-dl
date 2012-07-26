# coding: utf-8
# Copyright (c) 2008-2011 Volvox Development Team
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Author: Konstantin Lepa <konstantin.lepa@gmail.com>

"""ANSII Color formatting for output in terminal."""
from __future__ import print_function
import os


__ALL__ = [ 'colored', 'cprint' ]

VERSION = (1, 1, 0)

ATTRIBUTES = dict(
        list(zip([
            'bold',
            'dark',
            '',
            'underline',
            'blink',
            '',
            'reverse',
            'concealed'
            ],
            list(range(1, 9))
            ))
        )
del ATTRIBUTES['']


COLORS = dict(
        list(zip([
            'black',
            'red',
            'green',
            'yellow',
            'blue',
            'magenta',
            'cyan',
            'white',
            ],
            list(range(30, 38))
            ))
        )


BACKGROUND_COLORS= dict(
        list(zip([
            'black',
            'red',
            'green',
            'yellow',
            'blue',
            'magenta',
            'cyan',
            'white'
            ],
            list(range(40, 48))
            ))
        )


RESET = '\033[0m'


def colored_print(color, bg_color, attrs, *args):
    """Colorize text.

    Available text colors:
        red, green, yellow, blue, magenta, cyan, white.

    Available background colors:
        red, green, yellow, blue, magenta, cyan, white.

    Available attributes:
        bold, dark, underline, blink, reverse, concealed.
    """
    text = ""
    if os.getenv('ANSI_COLORS_DISABLED') is None:
        fmt_str = '\033[%dm%s'
        if color is not None:
            text = fmt_str % (COLORS[color], text)

        if bg_color is not None:
            text = fmt_str % (BACKGROUND_COLORS[bg_color], text)

        if attrs is not None:
            for attr in attrs:
                text = fmt_str % (ATTRIBUTES[attr], text)
    print(text, sep='', end='')
    print(*args, end='')
    print(RESET)


if __name__ == "__main__":
    colored_print('green', None, ['bold'], "Hello world")
    colored_print('blue', 'black', None, "Hello world")
    colored_print('red', 'white', None, "Hello world")
    colored_print('yellow', 'green', None, "Hello world")
    colored_print('green', 'yellow', None, "Hello world")
