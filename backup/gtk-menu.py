#!/usr/bin/env python

import pygtk
import gtk
import gobject

def menuitem_response():
    pass

window = gtk.Window()
menu_bar = gtk.MenuBar()

window.add(menu_bar)


file_menu = gtk.Menu()    # Don't need to show menus


# Create the menu items
file_item = gtk.MenuItem("_File")
open_item = gtk.CheckMenuItem("Open")
save_item = gtk.MenuItem("Save")
quit_item = gtk.MenuItem("Quit")

# Add them to the menu
file_menu.append(open_item)
file_menu.append(save_item)
file_menu.append(quit_item)

# Attach the callback functions to the activate signal
open_item.connect_object("activate", menuitem_response, "file.open")
save_item.connect_object("activate", menuitem_response, "file.save")

# We can attach the Quit menu item to our exit function
quit_item.connect_object ("activate", gtk.main_quit, "file.quit")

file_item.set_submenu(file_menu)
menu_bar.append(file_item)
window.show_all()

# # We do need to show menu items
# open_item.show()
# save_item.show()
# quit_item.show()

gtk.main()
