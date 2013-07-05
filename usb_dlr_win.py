#!/usr/bin/env python

import time
import threading

import pygtk
pygtk.require('2.0')
import gtk
import gobject

import configs
from debug_utils import *
import mtd_part_alloc

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

    def on_bsp_alloc_changed(self, widget):
        info("BSP Alloc changed")
        for (w, f) in self.options.bsp_alloc_item_list:
            if w.get_active():
                info(w.get_label(), "is selected")
                f()
                break
            
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


    def mmap_pkg(self):
        pkg_path = self.options.pkg_path
        if not os.path.exists(pkg_path):
            wtf("Package not found in: ", pkg_path)
        chk_rslt, pkg_img_pos_dict = bsp_pkg_check(pkg_path)
        if not chk_rslt:
            wtf("Failed to verify bsp package: ", pkg_path)
        info(pkg_img_pos_dict)
        # open pkg buffer
        pkg_fd = open(pkg_path, 'rb')
        pkg_buf = mmap.mmap(pkg_fd.fileno(), 0, access = mmap.ACCESS_READ)
        # gen burn list
        self.options.burn_list = ''
        self.options.pkg_img_pos_list = []
        for i, pkg_img_pos in pkg_img_pos_dict.items():
            self.options.burn_list += img_type_dict[i][1]
            self.options.pkg_img_pos_list.append(pkg_img_pos)

        
        info("BSP PKG INFO: ", self.options.burn_list, self.options.pkg_img_pos_list)

        


        
if __name__ == '__main__':
    configs.debug = True
    dlr_win = usb_dlr_win()
    dlr_win.connect('delete-event', gtk.main_quit)
    dlr_win.show_all()
    
    gtk.main()
