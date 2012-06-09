import os
import io
import sys
from debug_util import *
from util import *
from const_vars import *
from usb_generic import read_blocks, write_blocks, get_dev_block_info
import struct


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
    #if CFG_MAX_ERASE_SIZE:
    #    
    num_of_data_group_sector = 8
    num_of_space_area_group_sector = 8
    num_cnt_to_bb_per_time = SIZE_PER_WRITE / SECTOR_SIZE / num_of_data_group_sector
    dbg( "num_cnt_to_bb_per_time=%d" % num_cnt_to_bb_per_time)
    raw_data_cnt = 0
    sector_offset = start_addr_hw / SECTOR_SIZE
    data_buf = NULL_CHAR * SECTOR_SIZE
    ret = False
    img_total_size = len(img_buf)
    yaffs_head_id = str_to_int32(img_buf[0:4])
    yaffs_version = str_to_int32(img_buf[4:8])
    yaffs_byte_per_chunk = str_to_int32(img_buf[8:12])
    yaffs_byte_per_spare = str_to_int32(img_buf[12:16])

    yaffs_img_header = struct.pack('LLL', yaffs_head_id, \
            yaffs_version, yaffs_byte_per_chunk, yaffs_byte_per_spare)
    if yaffs_head_id == YAFFS_MAGIC_HEAD_ID and yaffs_version = YAFFS_VERSION_4096:
        num_of_data_group_sector = 8
        num_of_space_area_group_sector = 8
        # DataBuf += sizeof header
        #size -= sizeof header
    elif  yaffs_head_id == YAFFS_MAGIC_HEAD_ID and yaffs_version = YAFFS_VERSION_2048:
        num_of_data_group_sector = 4
        num_of_space_area_group_sector = 4
    else
        num_of_data_group_sector = 4
        num_of_space_area_group_sector = 4
        err("the program should not go here, something must be wrong")

    num_cnt_to_bb_per_time = SIZE_PER_WRITE / SECTOR_SIZE / num_of_data_group_sector
    buf = ctypes.create_string_buf(NULL_CHAR*SECTOR_SIZE, SECTOR_SIZE)
    buf[0] = '\x01'
    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_SPARE_DATA_CTRL, 1)
    buf = NULL_CHAR * SECTOR_SIZE
    buf[0:4] = int32_to_str(start_addr_hw)
    buf[4:8] = int32_to_str(img_len_hw)
    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)
    start_addr_erase_hw = start_addr_hw
    img_len_erase_hw = img_len_hw
    erase_len = NAND_ERASE_MAX_LEN_PER_TIME
    while img_len_erase_hw > 0:
        buf = NULL_CHAR * SECTOR_SIZE
        if img_len_erase_hw < NAND_ERASE_MAX_LEN_PER_TIME:
            erase_len = img_len_erase_hw
        buf[0:4] = int32_to_str(start_addr_hw)
        buf[4:8] = int32_to_str(erase_len)
        start_addr_erase_hw += erase_len
        img_len_erase_hw -= erase_len
        write_blocks(sg_fd, buf, USB_PROGRAMMER_ERASE_NAND_CMD, 1)







    



def usb_burn(sg_fd, ):
    

if __name__ == "__main__":
    set_dl_img_type("/dev/sg2", 48, 0)
