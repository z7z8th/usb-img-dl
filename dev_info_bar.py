#!/usr/bin/env python

import time

import pygtk
pygtk.require('2.0')
import gtk
import gobject

class dev_info_bar(gtk.Box):
    __gtype_name__ = 'dev_info_bar'

    status_dict = {}

    def __init__(self):
        gtk.Widget.__init__(self)
#        self.set_default_size(300, 50)
        self.hbox = gtk.HBox(spacing=4)
        self.pack_start(self.hbox, True, True)

        self.init_status_dict()

        self.label = gtk.Label("Device")
        self.progress = gtk.ProgressBar()
        self.test_btn = gtk.Button("Test")
        self.test_btn.connect("clicked", self.on_click_test_btn, "download")
        # self.dl_btn = gtk.Button("Download")
        # self.dl_btn.connect("clicked", self.on_click_dl_btn)
        self.status = gtk.Image()
        self.set_status("disconnect")
        self.hbox.pack_start(self.label, False, False, 2)
        self.hbox.pack_start(self.progress, True, True, 2)
        self.hbox.pack_start(self.status, False, False, 4)
        self.hbox.pack_end(self.test_btn, False, False, 4)

        
    def init_status_dict(self):
        if len(dev_info_bar.status_dict) > 0:
            return
        print "(II) init_status_dict"
        size = gtk.ICON_SIZE_LARGE_TOOLBAR
        dev_info_bar.status_dict = {
            "disconnect" : gtk.image_new_from_stock(gtk.STOCK_DISCONNECT, size),
            "test" : gtk.image_new_from_stock(gtk.STOCK_FIND, size),
            "update" : gtk.image_new_from_stock(gtk.STOCK_FIND_AND_REPLACE, size),
            "download" : gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, size),
            "success" : gtk.image_new_from_stock(gtk.STOCK_YES, size),
            "fail" : gtk.image_new_from_stock(gtk.STOCK_NO, size)
            }

        
    def set_fraction(self, fraction):
        gobject.idle_add(self.progress.set_fraction, fraction)


    def set_info(self, text):
        gobject.idle_add(self.progress.set_text, text)

    def set_label(self, text):
        gobject.idle_add(self.label.set_text, text)
        
    def set_status(self, status):
        gobject.idle_add(self.status.set_from_stock,
                         *dev_info_bar.status_dict[status].get_stock())


    def on_click_test_btn(self, btn, status):
        print dev_info_bar.status_dict[status].get_stock()
        self.set_status(status)
        self.set_fraction(0.6)
        # self.status.queue_draw()
        
        
if __name__ == '__main__':
#    configs.debug = True
    info_bar = dev_info_bar()
    info_bar2 = dev_info_bar()
    info_bar.connect('delete-event', gtk.main_quit)
    info_bar.show_all()
    
    gtk.main()
