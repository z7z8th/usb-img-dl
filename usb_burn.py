import os
import io
import sys
from debug_util import *
from util import *
from const_vars import *
from usb_generic import read_blocks, write_blocks, get_dev_block_info
import struct


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

def parse_yaffs2_header(header_buf):

    yaffs_head_id = str_to_int32(header_buf[0:4])
    yaffs_version = str_to_int32(header_buf[4:8])
    yaffs_byte_per_chunk = str_to_int32(header_buf[8:12])
    yaffs_byte_per_spare = str_to_int32(header_buf[12:16])

    yaffs_img_header = struct.pack('LLL', yaffs_head_id, \
            yaffs_version, yaffs_byte_per_chunk, yaffs_byte_per_spare)
    if yaffs_head_id == YAFFS_MAGIC_HEAD_ID and yaffs_version = YAFFS_VERSION_4096:
        num_data_group_sector = 8
        num_spare_group_sector = 8
        # DataBuf += sizeof header
        #size -= sizeof header
    elif  yaffs_head_id == YAFFS_MAGIC_HEAD_ID and yaffs_version = YAFFS_VERSION_2048:
        num_data_group_sector = 4
        num_spare_group_sector = 4
    else
        num_data_group_sector = 4
        num_spare_group_sector = 4
        err("the program should not go here, something must be wrong")
    return (num_data_group_sector, num_spare_group_sector)

def usb_burn_yaffs2(sg_fd, img_buf, start_addr_hw, img_len_hw):
    ret = False
    dbg( "num_cnt_to_bb_per_time=%d" % num_cnt_to_bb_per_time)

    raw_data_cnt = 0
    sector_offset = start_addr_hw / SECTOR_SIZE
    data_buf = NULL_CHAR * SECTOR_SIZE
    img_total_size = len(img_buf)

    SIZE_YAFFS2_HEADER = 16
    num_data_group_sector, num_spare_group_sector \
            = parse_yaffs2_header(img_buf[:SIZE_YAFFS2_HEADER])


    num_cnt_to_bb_per_time = SIZE_PER_WRITE / SECTOR_SIZE / num_data_group_sector

    buf = ctypes.create_string_buf(NULL_CHAR*SECTOR_SIZE, SECTOR_SIZE)
    buf[0] = '\x01'
    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_SPARE_DATA_CTRL, 1)

    buf[:] = NULL_CHAR * SECTOR_SIZE
    buf[0:4] = int32_to_str(start_addr_hw)
    buf[4:8] = int32_to_str(img_len_hw)
    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)
    start_addr_erase_hw = start_addr_hw
    img_len_erase_hw = img_len_hw
    erase_len = NAND_ERASE_MAX_LEN_PER_TIME
    # erase nand partition
    while img_len_erase_hw > 0:
        buf = NULL_CHAR * SECTOR_SIZE
        if img_len_erase_hw < NAND_ERASE_MAX_LEN_PER_TIME:
            erase_len = img_len_erase_hw
        buf[0:4] = int32_to_str(start_addr_hw)
        buf[4:8] = int32_to_str(erase_len)
        start_addr_erase_hw += erase_len
        img_len_erase_hw -= erase_len
        write_blocks(sg_fd, buf, USB_PROGRAMMER_ERASE_NAND_CMD, 1)

    # write yaffs
    SIZE_PER_SPARE = 16
    size_per_data_group = SECTOR_SIZE * num_data_group_sector
    size_per_spare_group = SIZE_PER_SPARE * num_spare_group_sector
    size_per_group = size_per_data_group + size_per_spare_group
    size_per_nand_write = size_per_group*num_cnt_to_bb_per_time

    data_buf = ctypes.create_string_buf(size_per_data_group*num_cnt_to_bb_per_time)
    spare_buf = ctypes.create_string_buf(size_per_spare_group*num_cnt_to_bb_per_time)
    size_written = SIZE_YAFFS2_HEADER
    while size_written < img_total_size:
        size_to_write = min(img_total_size - size_written, size_per_nand_write)
        group_cnt = size_to_write / size_per_group
        dbg(get_cur_func_name+"size_to_write=%d, group_cnt=%d" % \
                (size_to_write, group_cnt))
        # create buf
        for i in rang(group_cnt):
            img_buf_data_start = size_written + i*size_per_group
            img_buf_spare_start = img_buf_data_offset + SIZE_PER_WRITE
            img_buf_spare_end = size_to_write + (i+1)*size_per_group
            data_buf[i*size_per_data_group : (i+1)*size_per_data_group] =\
                    img_buf[img_buf_data_start:img_buf_spare_start]
            spare_buf[i*size_per_spare_group : (i+1)*size_per_spare_group] =\
                    img_buf[img_buf_spare_start:img_buf_spare_end]
        # do write to disk
        write_blocks(sg_fd, spare_buf, USB_PROGRAMMER_WR_NAND_SPARE_DATA, \
                (group_cnt*size_per_spare_group+SECTOR_SIZE-1)/SECTOR_SIZE)
        write_blocks(sg_fd, data_buf, sector_offset, \
                (group_cnt*size_per_data_group+SECTOR_SIZE-1)/SECTOR_SIZE)
        size_written += size_to_write
        




def usb_burn(sg_fd, ):
    


if __name__ == "__main__":
    set_dl_img_type("/dev/sg2", 48, 0)
