#!/usr/bin/env python

import time
import threading

import pygtk
pygtk.require('2.0')
import gtk
import gobject

import configs
from debug_utils import *

class usb_dlr_win(gtk.Window):
    __gtype_name__  = 'usb_dlr_win'
    
    def __init__(self):
        gtk.Window.__init__(self)
        self.set_default_size(800, 600)
        self.set_border_width(4)
        self.connect('delete-event', self.on_delete_event)
        self.downloading = False

        self.init_usb_dlr_options()

        self.vbox = gtk.VBox(spacing=4)
        self.add(self.vbox)

        # menu
        self.menu_bar = gtk.MenuBar()
        self.vbox.pack_start(self.menu_bar, False, False)
        self.menu_bar.add(self.create_menu())
        self.about_menu_item = gtk.MenuItem("_About")
        self.about_menu_item.connect("activate", self.on_active_about_menu)
        self.menu_bar.add(gtk.Button("About Btn"))

        # choose pkg path
        hbox = gtk.HBox(spacing=4)
        self.pkg_path_entry = gtk.Entry()
        self.pkg_path_entry.connect("changed", self.on_pkg_path_entry_changed)
        hbox.pack_start(self.pkg_path_entry, True, True)
        self.choose_pkg_btn = gtk.Button("Choose Package")
        self.choose_pkg_btn.set_border_width(4)
        self.choose_pkg_btn.connect("clicked", self.choose_pkg_cb)
        hbox.pack_start(self.choose_pkg_btn, False, False)
        self.vbox.pack_start(hbox, False, False)

        # device area
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


    def init_usb_dlr_options(self):
        class usb_dlr_options(object):
            pass
        options = usb_dlr_options()
        options.pkg_path = None
        options.erase_all = True
        options.reserve_mdata = False
        self.options = options

    def on_active_about_menu(self, widget):
        info(self.options.__dict__)

    def on_active_erase_all(self, widget):
        self.options.erase_all = widget.get_active()

    def on_active_reset_port_map(self, widget):
        pass

    def on_active_reserve_mdata(self, widget):
        self.options.reserve_mdata = widget.get_active()
        info(self.options.__dict__)
            
    def create_menu(self):
        gen_item = gtk.MenuItem("_Options")
        gen_menu = gtk.Menu()
        gen_item.set_submenu(gen_menu)

        erase_op_item = gtk.MenuItem("_Erase Operation")
        erase_op_menu = gtk.Menu()
        erase_op_item.set_submenu(erase_op_menu)
        erase_op_all_item = gtk.CheckMenuItem("_Erase All")
        erase_op_all_item.set_active(self.options.erase_all)
        erase_op_all_item.connect("toggled", self.on_active_erase_all)
        erase_op_menu.append(erase_op_all_item)
        gen_menu.append(erase_op_item)

        reset_port_map_item = gtk.MenuItem("_Reset Port Map")
        reset_port_map_item.connect("activate", self.on_active_reset_port_map)
        gen_menu.append(reset_port_map_item)

        reserve_mdata_item = gtk.CheckMenuItem("Re_serve MData")
        reserve_mdata_item.set_active(self.options.reserve_mdata)
        reserve_mdata_item.connect("toggled", self.on_active_reserve_mdata)
        gen_menu.append(reserve_mdata_item)

        return gen_item
        

    def on_delete_event(self, widget, event):
        return False
        

    def on_pkg_path_entry_changed(self, widget):
        self.options.pkg_path = widget.get_text()
        info("pkg_path:", self.options.pkg_path)

        
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
    configs.debug = True
    dlr_win = usb_dlr_win()
    dlr_win.connect('delete-event', gtk.main_quit)
    dlr_win.show_all()
    
    gtk.main()
