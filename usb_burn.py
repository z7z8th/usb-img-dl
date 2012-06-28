import os
import io
import sys
from debug_util import *
from utils import *
from const_vars import *
from usb_generic import read_blocks, write_blocks,write_large_buf, get_dev_block_info
import struct
import ctypes


def set_dl_img_type(sg_fd, dl_img_type, start_addr_hw):
    buf = chr(dl_img_type) + NULL_CHAR * (SECTOR_SIZE - 1)
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
    buf += chr(0x98)
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

    yaffs_head_id = str_to_int32_le(header_buf[0:4])
    yaffs_version = str_to_int32_le(header_buf[4:8])
    yaffs_byte_per_chunk = str_to_int32_le(header_buf[8:12])
    yaffs_byte_per_spare = str_to_int32_le(header_buf[12:16])

    info("yaffs_image_header: head_id=%d, version=%d, chunk_size=%d, spare_size=%d" % \
            (yaffs_head_id, yaffs_version, yaffs_byte_per_chunk, yaffs_byte_per_spare))
    yaffs_img_header = struct.pack('LLLL', yaffs_head_id, \
            yaffs_version, yaffs_byte_per_chunk, yaffs_byte_per_spare)
    if yaffs_head_id == YAFFS_MAGIC_HEAD_ID and yaffs_version == YAFFS_VERSION_4096:
        size_per_page = YAFFS_CHUNKSIZE_4K
        size_per_spare = YAFFS_SPARESIZE_4K
        # DataBuf += sizeof header
        #size -= sizeof header
    elif  yaffs_head_id == YAFFS_MAGIC_HEAD_ID and yaffs_version == YAFFS_VERSION_2048:
        size_per_page = YAFFS_CHUNKSIZE_2K
        size_per_spare = YAFFS_SPARESIZE_2K
    else:
        # im9828 v1/v3 uses 2KB size page and 64B size spare
        size_per_page = YAFFS_CHUNKSIZE_2K
        size_per_spare = YAFFS_SPARESIZE_2K

    return (size_per_page, size_per_spare)


def usb_burn_yaffs2(sg_fd, img_buf, start_addr_hw, img_len_hw):
    ret = False

    # erase nand partition
    buf = ctypes.create_string_buffer(NULL_CHAR*SECTOR_SIZE, SECTOR_SIZE)
    buf[0] = '\x01'
    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_SPARE_DATA_CTRL, 1)

    buf[:] = NULL_CHAR * SECTOR_SIZE
    buf[0:4] = int32_to_str(start_addr_hw)
    buf[4:8] = int32_to_str(img_len_hw)
    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)

    start_addr_erase_hw = start_addr_hw
    img_len_erase_hw = img_len_hw
    erase_len = NAND_ERASE_MAX_LEN_PER_TIME
    while img_len_erase_hw > 0:
        buf[:] = NULL_CHAR * SECTOR_SIZE
        if img_len_erase_hw < NAND_ERASE_MAX_LEN_PER_TIME:
            erase_len = img_len_erase_hw
        buf[0:4] = int32_to_str(start_addr_hw)
        buf[4:8] = int32_to_str(erase_len)
        start_addr_erase_hw += erase_len
        img_len_erase_hw -= erase_len
        write_blocks(sg_fd, buf, USB_PROGRAMMER_ERASE_NAND_CMD, 1)
    #endof erase nand partition

    # write yaffs
    sector_offset = start_addr_hw / SECTOR_SIZE
    img_total_size = len(img_buf)
    dbg("img_total_size=", img_total_size)

    size_per_page, size_per_spare = \
            parse_yaffs2_header(img_buf[:SIZE_YAFFS2_HEADER])
    num_cnt_to_bb_per_time = SIZE_PER_WRITE / size_per_page
    dbg("size_per_page=%d, size_per_spare=%d" % (size_per_page, size_per_spare))
    dbg( "num_cnt_to_bb_per_time=%d" % num_cnt_to_bb_per_time)
    size_per_group = size_per_page + size_per_spare
    size_per_nand_write = size_per_group*num_cnt_to_bb_per_time
    size_page_per_write = size_per_page*num_cnt_to_bb_per_time
    size_spare_per_write = size_per_spare*num_cnt_to_bb_per_time
    page_buf = ctypes.create_string_buffer(size_page_per_write)
    spare_buf = ctypes.create_string_buffer(size_spare_per_write)
    size_written = SIZE_YAFFS2_HEADER
    while size_written < img_total_size:
        page_buf[:] = NULL_CHAR * size_page_per_write
        spare_buf[:] = NULL_CHAR * size_spare_per_write
        size_to_write = min(img_total_size - size_written, size_per_nand_write)
        group_cnt = size_to_write/size_per_group
        dbg(get_cur_func_name() + \
                "(): size_written=%d, size_to_write=%d, group_cnt=%d" % \
                (size_written, size_to_write, group_cnt))
        # create buf
        for i in range(group_cnt):
            #dbg("group idx=", i)
            img_buf_page_start  = size_written + i*size_per_group
            img_buf_page_end    = min(img_buf_page_start + size_per_page, img_total_size)
            img_buf_spare_start = img_buf_page_end
            img_buf_spare_end   = min(img_buf_spare_start + size_per_spare, img_total_size)
            page_size_this = img_buf_page_end - img_buf_page_start
            spare_size_this = img_buf_spare_end - img_buf_spare_start
            page_buf_start = i*size_per_page
            spare_buf_start = i*size_per_spare
            #dbg("page_size_this=%d, spare_size_this=%d" % (page_size_this, spare_size_this))
            page_buf[page_buf_start:page_buf_start+page_size_this] =\
                    img_buf[img_buf_page_start:img_buf_page_end]
            spare_buf[spare_buf_start:spare_buf_start+spare_size_this] =\
                    img_buf[img_buf_spare_start:img_buf_spare_end]
        # do write to disk
        #dbg("sector_offset=", sector_offset)
        #dbg("write spare")
        print ".",
        write_blocks(sg_fd, spare_buf, USB_PROGRAMMER_WR_NAND_SPARE_DATA, size_spare_per_write/SECTOR_SIZE)
        #dbg("write page")
        write_blocks(sg_fd, page_buf, sector_offset, SECTOR_NUM_PER_WRITE)
        size_written += size_to_write
        sector_offset += SECTOR_NUM_PER_WRITE
        


#def usb_burn(sg_fd, ):
    

if __name__ == "__main__":
    set_dl_img_type("/dev/sg2", 48, 0)
