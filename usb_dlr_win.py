#!/usr/bin/env python

import sys
import time
import os
import threading
import mmap

import pygtk
pygtk.require('2.0')
import gtk
import gobject

from dev_info_bar import dev_info_bar
from dl_manager import dl_manager

import configs
from debug_utils import *
import mtd_part_alloc
import type_call_dict
from bsp_pkg_check import bsp_pkg_check


class usb_dlr_win(gtk.Window):
    __gtype_name__  = 'usb_dlr_win'
    
    def __init__(self):
        gtk.Window.__init__(self)
        self.set_default_size(800, 500)
        self.set_border_width(4)
        self.connect('delete-event', self.on_delete_event)

        self.init_usb_dlr_options()
        self.manager = None

        self.vbox = gtk.VBox(spacing=4)
        self.add(self.vbox)

        # menu
        self.menu_bar = gtk.MenuBar()
        self.vbox.pack_start(self.menu_bar, False, False)
        self.menu_bar.add(self.create_menu())
        self.about_menu_item = gtk.MenuItem("_About")
        self.about_menu_item.connect("activate", self.on_active_about_menu)
        self.menu_bar.add(self.about_menu_item)

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

        run_btn = gtk.Button("Run")
        run_btn.connect("clicked", self.start_manager)
        hbox.pack_end(run_btn, False, False)
        

        # device area
        dev_frame = gtk.Frame("Devices")
        self.vbox.pack_start(dev_frame, True, True)

        self.dev_table = gtk.Table(8, 2)
        self.dev_table.set_homogeneous(True)
        dev_frame.add(self.dev_table)
        # self.vbox.pack_start(self.dev_table, True, True)
        self.dev_info_list = []

        for i in range(16):
            col = i / 8;
            row = i % 8;
            label = "Device %2d" % (i+1)
            dev_info = dev_info_bar()
            dev_info.set_label(label)
            dev_info.set_info("Disconnected")
            self.dev_table.attach(dev_info,
                                  col, col+1, row, row+1,
                                  xpadding=6, ypadding=6)
            self.dev_info_list.append(dev_info)
            
        # self.status_bar = gtk.Statusbar()
        # self.status_bar_ctx_id = self.status_bar.get_context_id("default")
        # self.vbox.pack_start(self.status_bar, False, False)
        # self.status_bar.push(self.status_bar_ctx_id, "Ready")
        # self.status_bar.push(self.status_bar_ctx_id, "Hello")


    def init_usb_dlr_options(self):
        class usb_dlr_options(object):
            pass
        options = usb_dlr_options()
        options.win = self
        options.pkg_path = ""
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

    def on_bsp_alloc_changed(self, widget):
        info("BSP Alloc changed")
        for (w, f) in self.options.bsp_alloc_item_list:
            if w.get_active():
                info(w.get_label(), "is selected")
                f()
                break
        type_call_dict.update_type_call_dict()
            
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

        bsp_alloc_item = gtk.MenuItem("_BSP Allocation")
        bsp_alloc_menu = gtk.Menu()
        bsp_alloc_item.set_submenu(bsp_alloc_menu)
        group = None
        bsp_alloc_item_list = []
        bsp_alloc_bsp12_item = gtk.RadioMenuItem(group, "BSP1_2")
        group = bsp_alloc_bsp12_item
        bsp_alloc_bsp13_item = gtk.RadioMenuItem(group, "BSP1_3")
        bsp_alloc_bsp12_item.set_active(True)
        bsp_alloc_bsp12_item.connect("activate", self.on_bsp_alloc_changed)
        bsp_alloc_item_list.append((bsp_alloc_bsp12_item,
                                    mtd_part_alloc.use_bsp12_allocation))
        bsp_alloc_item_list.append((bsp_alloc_bsp13_item,
                                    mtd_part_alloc.use_bsp13_allocation))
        self.options.bsp_alloc_item_list = bsp_alloc_item_list
        bsp_alloc_menu.add(bsp_alloc_bsp12_item)
        bsp_alloc_menu.add(bsp_alloc_bsp13_item)
        gen_menu.append(bsp_alloc_item)
        
        reset_port_map_item = gtk.MenuItem("_Reset Port Map")
        reset_port_map_item.connect("activate", self.on_active_reset_port_map)
        gen_menu.append(reset_port_map_item)

        reserve_mdata_item = gtk.CheckMenuItem("Re_serve MData")
        reserve_mdata_item.set_active(self.options.reserve_mdata)
        reserve_mdata_item.connect("toggled", self.on_active_reserve_mdata)
        gen_menu.append(reserve_mdata_item)

        return gen_item
        

    def on_delete_event(self, widget, event):
        pinfo("(II) main quit")
        sys.stdout.flush()
        sys.stderr.flush()
        pinfo("(II) stdout/stderr flushed")
        # os._exit(0)
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


    def map_img_buf(self):
        pkg_path = self.options.pkg_path
        if not os.path.exists(pkg_path):
            self.alert("Package not found in: " + pkg_path)
        chk_rslt, pkg_img_pos_dict = bsp_pkg_check(pkg_path)
        if not chk_rslt:
            self.alert("Failed to verify bsp package: ", pkg_path)
            return False
        info(pkg_img_pos_dict)
        # open pkg buffer
        pkg_fd = open(pkg_path, 'rb')
        pkg_buf = mmap.mmap(pkg_fd.fileno(), 0, access = mmap.ACCESS_READ)
        # gen burn list
        self.options.img_buf_dict = dict()
        for i, pkg_img_pos in pkg_img_pos_dict.items():
            img_start, img_size = pkg_img_pos
            img_end = img_start + img_size
            img_buf = pkg_buf[img_start:img_end]
            self.options.img_buf_dict[i] = img_buf
        return True

            
    def _update_status(self, text):
        self.status_bar.set_text(text)

    def _alert(self, msg, level = gtk.MESSAGE_INFO):
        dialog = gtk.MessageDialog(
            self,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            level, gtk.BUTTONS_OK,
            msg)
        dialog.run()
        dialog.destroy()

    def update_status(self, text):
        gobject.idle_add(self._update_status, text)

    def alert(self, level, msg):
        gobject.idle_add(self._alert, level, msg)

    def start_manager(self, widget=None):
        if not self.map_img_buf():
            return
        class device_options(object):
            pass
        dev_opts = device_options()
        self.manager = dl_manager(self.options, dev_opts)
        self.manager.start()

        
        
if __name__ == '__main__':
    configs.debug = True
    dlr_win = usb_dlr_win()
    #dlr_win.connect('delete-event', gtk.main_quit)
    dlr_win.show_all()
    # dlr_win.start_manager()
    
    gtk.main()
