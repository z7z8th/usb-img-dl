#!/usr/bin/env python

import time
import threading

import pygtk
pygtk.require('2.0')
import gtk
import gobject





if __name__ == '__main__':
    gobject.threads_init()
    dlr_win = usb_dlr_win()
    dlr_win.connect('delete-event', gtk.main_quit)
    dlr_win.show_all()
    
    gtk.main()
