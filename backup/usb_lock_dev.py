#!/usr/bin/env python
import os
import sys
import fcntl
import re
import glob
import shlex, subprocess
import tempfile

import time

from debug_utils import *


#KERNEL=="sd*", SUBSYSTEM=="block", SUBSYSTEMS=="usb", ATTRS{idVendor}=="0851", 
#ATTRS{idProduct}=="0002", ATTRS{manufacturer}=="Infomax", MODE:="0660", GROUP:="plugdev"
Infomax_Match_Patterns = (
        r'SUBSYSTEM=="block"',
        r'SUBSYSTEMS=="usb"',
        r'ATTRS{idVendor}=="0851"',
        r'ATTRS{idProduct}=="0002"',
        r'ATTRS{manufacturer}=="Infomax"',
        )


def find_usb_storage_dev():
    global Infomax_Match_Patterns
    usb_storage_dev_found = []
    sd_list = glob.glob("/dev/sd?")
    for sd_path in sd_list:
        cmd_str = "udevadm info --query=all --attribute-walk --path=/sys/block/%s" % os.path.basename(sd_path)
        args = shlex.split(cmd_str)
        dbg(args)
        udev_info_ps = subprocess.Popen(args, stdout=subprocess.PIPE)
        udev_info_contents = udev_info_ps.stdout.read()
        for pattern in Infomax_Match_Patterns:
            if not re.search(pattern, udev_info_contents):
                break
        else:
            usb_storage_dev_found.append(sd_path)
    return usb_storage_dev_found


def lock_usb_storaga_dev(sd_list):
    for sd_path in sd_list:
        sd_fd = os.open(sd_path, os.O_SYNC | os.O_RDWR)
        if sd_fd < 0:
            info("open sd dev failed. sd_fd=", sd_fd)
            continue
        info("\nlocking: ", sd_path)
        try:
            fcntl.flock(sd_fd, fcntl.LOCK_EX)
            #time.sleep(1000)
        except IOError as e:
            os_errno = os.errno
            err(e)
            wtf(os.strerror(os_errno))
        os.close(sd_fd)


# lock the cresponding usb storage devices of sg devices
def find_and_lock_all_usb_storage():
    info("The usb storage devices (/dev/sd[cd]) must not be accessed by other process,\n\
Otherwise our img downloading will not process correctly.\n\
If the usb storage devices can not be locked, this program will exit !!!\n")
    sd_list = find_usb_storage_dev()
    info("devices to lock:", sd_list)
    time.sleep(1)
    lock_usb_storaga_dev(sd_list)


if __name__ == "__main__":
    find_and_lock_all_usb_storage()
