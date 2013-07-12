#!/usr/bin/env python

import sys
import time
import os
import threading
import mmap
import copy
import cPickle as pickle

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

class usb_dlr_options(object):
    def __init__(self, win):
        self.default_options_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".dlr_options")
        ret = self.load()
        self.win = win
        self.img_buf_dict = {}
        if ret is False:
            self.pkg_path = ""
            self.erase_all = True
            self.reserve_mdata = False
            self.usb_id = configs.USB_ID_ROM
            self.bsp_alloc = configs.BSP12_NAME


        print self.__dict__


    def load(self, file=None):
        if file is None:
            file = self.default_options_file
        if os.path.exists(file):
            with open(file, 'rb') as f:
                self.__dict__.update(pickle.load(f))
                return True
        else:
            return False


    def dump(self, file=None):
        if file is None:
            file = self.default_options_file
        opts = copy.copy(self.__dict__)
        opts['img_buf_dict'] = {}
        opts['win'] = None
        # options['pkg_path'] = self.pkg_path
        # options['erase_all'] = self.erase_all
        # options['reserve_mdata'] = self.reserve_mdata
        print opts
        print self.win
        with open(file, 'wb') as f:
             pickle.dump(opts, f)


class usb_dlr_win(gtk.Window):
    __gtype_name__  = 'usb_dlr_win'
    
    def __init__(self):
        gtk.Window.__init__(self)
        self.set_default_size(800, 500)
        self.set_border_width(4)
        self.connect('delete-event', self.on_delete_event)

        self.options = usb_dlr_options(self)
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

        # rom/fastboot selection
        hbox = gtk.HBox(spacing=4)
        self.vbox.pack_start(hbox, False, False)
        group = None
        usb_id_sel_rom = (gtk.RadioButton(group, "ROM %04X:%04X" % \
                                              configs.USB_ID_ROM),
                               configs.USB_ID_ROM)
        group = usb_id_sel_rom[0]
        group.connect("toggled", self.usb_id_on_sel)
        usb_id_sel_fb = (gtk.RadioButton(group, "Fastboot %04X:%04X" % \
                                                configs.USB_ID_FASTBOOT),
                                configs.USB_ID_FASTBOOT)
        self.usb_id_sel = [usb_id_sel_rom, usb_id_sel_fb]
        for t in self.usb_id_sel:
            hbox.pack_start(t[0], False, False)
            if t[1] == self.options.usb_id:
                t[0].set_active(True)

        
        # choose pkg path
        hbox = gtk.HBox(spacing=4)
        self.vbox.pack_start(hbox, False, False)
        self.pkg_path_entry = gtk.Entry(max=4096)
        self.pkg_path_entry.set_text(self.options.pkg_path)
        self.pkg_path_entry.connect("changed", self.on_pkg_path_entry_changed)
        hbox.pack_start(self.pkg_path_entry, True, True)
        self.choose_pkg_btn = gtk.Button("Choose Package")
        self.choose_pkg_btn.set_border_width(4)
        self.choose_pkg_btn.connect("clicked", self.choose_pkg_cb)
        hbox.pack_start(self.choose_pkg_btn, False, False)

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
            col = i / 8
            row = i % 8
            label = "Device #"
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

    def usb_id_on_sel(self, widget):
        for w, id in self.usb_id_sel:
            if w.get_active():
                info(w.get_label(), "is selected")
                self.options.usb_id = id
                self.options.dump()
                break

    def on_active_about_menu(self, widget):
        # info(self.options.__dict__)
        pass

    def on_active_erase_all(self, widget):
        self.options.erase_all = widget.get_active()
        self.options.dump()

    def on_active_reset_port_map(self, widget):
        pass

    def on_active_reserve_mdata(self, widget):
        self.options.reserve_mdata = widget.get_active()
        self.options.dump()
        info(self.options.__dict__)

    def on_bsp_alloc_changed(self, widget):
        info("BSP Alloc changed")
        for (w, f, n) in self.bsp_alloc_item_list:
            if w.get_active():
                info(w.get_label(), "is selected")
                self.options.bsp_alloc = n
                self.options.dump()
                f()
                break
        type_call_dict.update_type_call_dict()
        mtd_part_alloc.print_allocation()
        print type_call_dict.type_call_dict
            
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
        bsp12_alloc_item = gtk.RadioMenuItem(group, "BSP1_2")
        group = bsp12_alloc_item
        group.connect("activate", self.on_bsp_alloc_changed)
        bsp13_alloc_item = gtk.RadioMenuItem(group, "BSP1_3")
        self.bsp_alloc_item_list = [(bsp12_alloc_item,
                                mtd_part_alloc.use_bsp12_allocation,
                                configs.BSP12_NAME),
                                (bsp13_alloc_item,
                                mtd_part_alloc.use_bsp13_allocation,
                                configs.BSP13_NAME)]
        for t in self.bsp_alloc_item_list:
            bsp_alloc_menu.add(t[0])
            if t[2] == self.options.bsp_alloc:
                t[0].set_active(True)
                t[1]()
                type_call_dict.update_type_call_dict()
        gen_menu.append(bsp_alloc_item)
        
        reset_port_map_item = gtk.MenuItem("_Reset Port Map")
        reset_port_map_item.connect("activate", self.on_active_reset_port_map)
        gen_menu.append(reset_port_map_item)

        reserve_mdata_item = gtk.CheckMenuItem("Re_serve MData")
        reserve_mdata_item.set_active(self.options.reserve_mdata)
        reserve_mdata_item.connect("toggled", self.on_active_reserve_mdata)
        gen_menu.append(reserve_mdata_item)

        return gen_item
        

    def on_pkg_path_entry_changed(self, widget):
        self.options.pkg_path = widget.get_text()
        self.options.dump()
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

    def alert(self, msg, level = gtk.MESSAGE_INFO):
        gobject.idle_add(self._alert, msg, level)

    def start_manager(self, widget=None):
        widget.set_sensitive(False)

        # self.pkg_path_entry.set_text("/opt2/bsp-packages/BSP12.7.5_DSIM_HVGA_20121012/BSP12_DSIM_HVGA_20121012_Image")
        if not self.map_img_buf():
            return
        class device_options(object):
            pass
        dev_opts = device_options()
        self.manager = dl_manager(self.options, dev_opts)
        self.manager.start()
        warn("(WW) manager started")


    def on_delete_event(self, widget, event):
        pinfo("(II) main quit")
        sys.stdout.flush()
        sys.stderr.flush()
        pinfo("(II) stdout/stderr flushed")
        gtk.main_quit()
        print "****** after quit"
        os._exit(0)
        return False
        
        
        
if __name__ == '__main__':
    configs.debug = True
    gobject.threads_init()
    dlr_win = usb_dlr_win()
    #dlr_win.connect('delete-event', gtk.main_quit)
    dlr_win.show_all()
    # dlr_win.start_manager()
    
    gtk.main()
