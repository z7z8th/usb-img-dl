import os
import io
import sys
from debug_util import *
from util import *
from const_vars import *
from usb_generic import read_blocks, write_blocks, get_dev_block_info


# download second boot loader to RAM
DOWNLOAD_TYPE_RAM = 2
# download code to flash directory
DOWNLOAD_TYPE_FLASH = 1

# Command to tell Magic that the image boot from RAM or FLASH
USB_PROGRAMMER_SET_BOOT_DEVICE = 0x50000200
# Command to tell Magic that the image boot from which address
USB_PROGRAMMER_SET_BOOT_ADDR = 0x50000204

ID_BAREBOX     = 0x0
ID_BAREBOX_ENV = 0x1
ID_LDR_APP     = 0x2
ID_IMEI        = 0x3
ID_ICON        = 0x4

DYN_ID_INIT_OFFSET = 0x00020000
DYN_ID_INIT_LENGTH = (15*0x00020000)
DYN_ID_SIZE        = 0x00020000



def set_dl_img_type(sg_fd, dl_img_type, start_addr_hw):
    buf = chr(dl_img_type) + NULL_CHAR * (SECTOR_SIZE - 1)
    print buf
    dbg( get_cur_func_name() + ": len of buf=%d" % len(buf))
    ret = write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_BOOT_DEVICE, 1)
    if not ret:
        wtf("fail to set download img type")
    buf = int32_to_str(start_addr_hw)
    buf += NULL_CHAR * (SECTOR_SIZE - 4)
    ret = write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_BOOT_ADDR, 1)
    if not ret:
        wtf("fail to set download img addr")

def usb_burn_dyn_id(sg_fd, img_buf, dyn_id):
    dyn_id_init_offset = DYN_ID_INIT_OFFSET
    dyn_id_init_len    = DYN_ID_INIT_LENGTH
    sector_offset = dyn_id_init_offset / SECTOR_SIZE
    platform_id = 0x15

    buf = int32_to_str(dyn_id_init_offset)
    buf += int32_to_str(dyn_id_init_len)
    buf += NULL_CHAR * 2
    buf += chr(platform_id)
    buf += chr(dyn_id+1)
    buf += NULL_CHAR * (SECTOR_SIZE - len(buf))

    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)
    write_blocks(sg_fd, buf, USB_PROGRAMMER_ERASE_NAND_CMD, 1)

    write_large_buf(sg_fd, img_buf, sector_offset)


def usb_burn_raw(sg_fd, img_buf, start_addr_hw, img_len_hw):
    sector_offset = start_addr_hw / SECTOR_SIZE
    buf = int32_to_str(start_addr_hw)
    buf += int32_to_str(img_len_hw)
    buf += NULL_CHAR * (SECTOR_SIZE - len(buf))
    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)
    write_blocks(sg_fd, buf, USB_PROGRAMMER_ERASE_NAND_CMD, 1)
    img_total_size = len(img_buf)
    write_large_buf(sg_fd, img_buf, sector_offset)

def usb_burn_yaffs2(sg_fd, img_buf, start_addr_hw, img_len_hw):
    erase_len = 0
    if CFG_MAX_ERASE_SIZE:
        



def usb_burn(sg_fd, ):
    

if __name__ == "__main__":
    set_dl_img_type("/dev/sg2", 48, 0)
