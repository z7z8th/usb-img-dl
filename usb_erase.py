from __future__ import print_function
import os
import io
import sys
import struct

from const_vars import *
from debug_utils import *
from utils import *
import mtd_part_alloc
from usb_generic import write_sectors
from usb_part import *

ERASE_TIMEOUT = 12 * 1000

def usb_erase_dyn_id(usbdldev, dyn_id):
    dbg("Erasing dyn id")
    set_part_dyn_id(dyn_id)
    buf = dyn_id_part_info(usbdldev, dyn_id)
    write_sectors(usbdldev, buf, USB_PROGRAMMER_ERASE_NAND_CMD, 1, ERASE_TIMEOUT)
    dbg("erase dyn id finished")


def usb_erase_generic(usbdldev, mtd_part_start_addr, mtd_part_size, is_yaffs2):
    set_part_generic(usbdldev, mtd_part_start_addr, mtd_part_size, is_yaffs2)
    usbdldev.dev_info.set_fraction(0.01)

    dbg("Start to erase")
    nand_start_erase_addr = mtd_part_start_addr
    nand_erase_size = mtd_part_size
    while nand_erase_size > 0:
        size_to_erase = min(nand_erase_size, NAND_ERASE_MAX_LEN_PER_TIME)
        buf = int32_le_to_str_be(nand_start_erase_addr)
        buf += int32_le_to_str_be(size_to_erase)
        buf += NULL_CHAR * (SECTOR_SIZE - len(buf))
        write_sectors(usbdldev, buf, USB_PROGRAMMER_ERASE_NAND_CMD, 1, ERASE_TIMEOUT)
        nand_start_erase_addr += size_to_erase
        nand_erase_size    -= size_to_erase
        usbdldev.dev_info.set_fraction(float((mtd_part_size-nand_erase_size))/mtd_part_size)
    usbdldev.dev_info.set_fraction(1)
    dbg("Erase succeed")

def usb_erase_whole_nand_flash(usbdldev):
    usb_erase_generic(usbdldev, mtd_part_alloc.IM9828_NAND_OFFSET,
            mtd_part_alloc.IM9828_NAND_LENGTH, False)


if __name__ == "__main__":
    pass
