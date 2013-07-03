#!/usr/bin/env python

import time
import threading

import pygtk
pygtk.require('2.0')
import gtk
import gobject

class usb_dlr_win(gtk.Window):
    __gtype_name__  = 'usb_dlr_win'
    
    def __init__(self):
        gtk.Window.__init__(self)
        self.set_default_size(800, 600)
        self.set_border_width(4)
        self.connect('delete-event', self.on_delete_event)
        self.downloading = False

        self.vbox = gtk.VBox(spacing=4)
        self.add(self.vbox)
        
        # self.menu = None
        # self.add(menu)
        hbox = gtk.HBox(spacing=4)
        self.pkg_path_entry = gtk.Entry()
        hbox.pack_start(self.pkg_path_entry, True, True)
        self.choose_pkg_btn = gtk.Button("Choose Package")
        self.choose_pkg_btn.set_border_width(4)
        self.choose_pkg_btn.connect("clicked", self.choose_pkg_cb)
        hbox.pack_start(self.choose_pkg_btn, False, False)
        self.vbox.pack_start(hbox, False, False)

        dev_frame = gtk.Frame("Devices")
        self.vbox.pack_start(dev_frame, True, True)

        self.dev_table = gtk.Table(8, 2)
        dev_frame.add(self.dev_table)
#        self.vbox.pack_start(self.dev_table, True, True)

        for i in range(16):
            col = i / 8;
            row = i % 8;
            label = gtk.Label("Device %d" % i)
            self.dev_table.attach(label, col, col+1, row, row+1)

            
        

    def on_delete_event(self, widget, event):
        return False
        


    def choose_pkg_cb(self, btn):
        dialog = gtk.FileChooserDialog("Open..",
                                       None,
                                       gtk.FILE_CHOOSER_ACTION_OPEN,
                                       (gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.pkg_path_entry.set_text(dialog.get_filename())
        elif response == gtk.RESPONSE_CANCEL:
            self.pkg_path_entry.set_text('')
            
        dialog.destroy()
        
if __name__ == '__main__':
    dlr_win = usb_dlr_win()
    dlr_win.connect('delete-event', gtk.main_quit)
    dlr_win.show_all()
    
    gtk.main()
