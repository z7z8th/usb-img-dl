from __future__ import print_function
import os
import io
import sys
import struct
import ctypes

from const_vars import *
from debug_util import *
from utils import *
from usb_generic import read_blocks, write_blocks, get_dev_block_info


def usb_erase_dyn_id(sg_fd, dyn_id):
    dyn_id_init_offset = DYN_ID_INIT_OFFSET
    dyn_id_init_len    = DYN_ID_INIT_LENGTH
    platform_id = 0x15

    buf = int32_to_str(dyn_id_init_offset)
    buf += int32_to_str(dyn_id_init_len)
    buf += NULL_CHAR * 2
    buf += chr(0x98)
    buf += chr(platform_id)
    buf += chr(dyn_id+1)
    buf += NULL_CHAR * (SECTOR_SIZE - len(buf))

    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)
    write_blocks(sg_fd, buf, USB_PROGRAMMER_ERASE_NAND_CMD, 1)


def usb_erase_raw(sg_fd, mtd_part_start_addr, mtd_part_size):
    buf = int32_to_str(mtd_part_start_addr)
    buf += int32_to_str(mtd_part_size)
    buf += NULL_CHAR * (SECTOR_SIZE - len(buf))
    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)
    write_blocks(sg_fd, buf, USB_PROGRAMMER_ERASE_NAND_CMD, 1)

def usb_erase_yaffs2(sg_fd, mtd_part_start_addr, mtd_part_size):
    buf = ctypes.create_string_buffer(SECTOR_SIZE)
    buf[0] = '\x01'
    write_blocks(sg_fd, buf.raw, \
            USB_PROGRAMMER_SET_NAND_SPARE_DATA_CTRL, 1)

    buf[:] = NULL_CHAR * SECTOR_SIZE
    buf[0:4] = int32_to_str(mtd_part_start_addr)
    buf[4:8] = int32_to_str(mtd_part_size)
    write_blocks(sg_fd, buf.raw, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)

    info("start to erase yaffs2")
    nand_start_erase_addr = mtd_part_start_addr
    nand_erase_size = mtd_part_size
    while nand_erase_size > 0:
        buf[:] = NULL_CHAR * SECTOR_SIZE
        size_to_erase = min(nand_erase_size, NAND_ERASE_MAX_LEN_PER_TIME)
        buf[0:4] = int32_to_str(nand_start_erase_addr)
        buf[4:8] = int32_to_str(size_to_erase)
        write_blocks(sg_fd, buf.raw, USB_PROGRAMMER_ERASE_NAND_CMD, 1)
        nand_start_erase_addr += size_to_erase
        nand_erase_size    -= size_to_erase
        print('.', sep='', end='')
        sys.stdout.flush()
    info("\nerase yaffs2 succeed")


if __name__ == "__main__":
    pass
