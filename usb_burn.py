import os
import io
import sys
from debug_util import *
from const_vars import *
from usb_generic import read_blocks, write_blocks, get_dev_block_info


# Command to tell Magic that the image boot from RAM or FLASH
USB_PROGRAMMER_SET_BOOT_DEVICE = 0x50000200
# Command to tell Magic that the image boot from which address
USB_PROGRAMMER_SET_BOOT_ADDR = 0x50000204


def set_dl_img_type(sg_path, dl_img_type, img_start_addr):
    buf = chr(dl_img_type) + NULL_CHAR * (SECTOR_SIZE - 1)
    print buf
    dbg( get_cur_func_name() + ": len of buf=%d" % len(buf))
    ret = write_blocks(sg_path, buf, USB_PROGRAMMER_SET_BOOT_DEVICE, 1)
    if not ret:
        wtf("fail to set download img type")
    buf = chr((img_start_addr >> 24) & 0xFF) + \
            chr((img_start_addr >> 16) & 0xFF) + \
            chr((img_start_addr >> 8) & 0xFF) + \
            chr(img_start_addr & 0xFF)
    buf += NULL_CHAR * (SECTOR_SIZE - 4)
    ret = write_blocks(sg_path, buf, USB_PROGRAMMER_SET_BOOT_ADDR, 1)
    if not ret:
        wtf("fail to set download img addr")




if __name__ == "__main__":
    set_dl_img_type("/dev/sg2", 48, 0)
