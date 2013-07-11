from utils import *
from const_vars import *
from debug_utils import *
import mtd_part_alloc
from usb_generic import write_sectors

def dyn_id_part_info(dyn_id):
    dyn_id_init_offset = mtd_part_alloc.DYN_ID_INIT_OFFSET
    dyn_id_init_len    = mtd_part_alloc.DYN_ID_INIT_LENGTH
    platform_id = 0x15

    buf = int32_le_to_str_be(dyn_id_init_offset)
    buf += int32_le_to_str_be(dyn_id_init_len)
    buf += NULL_CHAR * 2
    buf += chr(0x98)
    buf += chr(platform_id)
    buf += chr(dyn_id+1)
    buf += NULL_CHAR * (SECTOR_SIZE - len(buf))

    return buf


def set_part_dyn_id(usbdldev, dyn_id):
    buf = dyn_id_part_info(dyn_id)
    write_sectors(usbdldev, buf, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)


def set_part_generic(usbdldev, mtd_part_start_addr, mtd_part_size, is_yaffs2):
    if is_yaffs2:
        dbg("Erase Type is yaffs2")
        buf = '\x01'
        buf += NULL_CHAR * (SECTOR_SIZE - len(buf))
        write_sectors(usbdldev, buf, \
                USB_PROGRAMMER_SET_NAND_SPARE_DATA_CTRL, 1)

    buf = int32_le_to_str_be(mtd_part_start_addr)
    buf += int32_le_to_str_be(mtd_part_size)
    buf += NULL_CHAR * (SECTOR_SIZE - len(buf))
    write_sectors(usbdldev, buf, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)

