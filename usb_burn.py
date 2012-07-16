from __future__ import print_function
import os
import io
import sys
import struct
import ctypes
import time

from debug_util import *
from utils import *
from const_vars import *
from bsp_part_alloc import *
from usb_generic import read_blocks, write_blocks, write_large_buf, get_dev_block_info
from usb_erase import *



def usb_burn_dyn_id(sg_fd, img_buf, dyn_id):
    # erase and set nand partition info
    usb_erase_dyn_id(sg_fd, dyn_id)
    sector_offset = DYN_ID_INIT_OFFSET / SECTOR_SIZE
    # start write img
    write_large_buf(sg_fd, img_buf, sector_offset)


def usb_burn_raw(sg_fd, img_buf, nand_part_start_addr, nand_part_size):
    sector_offset = nand_part_start_addr / SECTOR_SIZE
    # erase first
    usb_erase_raw(sg_fd, nand_part_start_addr, nand_part_size)
    # start write img
    write_large_buf(sg_fd, img_buf, sector_offset)


def parse_yaffs2_header(header_buf):
    header_size = 0
    yaffs2_head_id = str_to_int32_le(header_buf[0:4])
    yaffs2_version = str_to_int32_le(header_buf[4:8])
    yaffs2_byte_per_chunk = str_to_int32_le(header_buf[8:12])
    yaffs2_byte_nand_spare = str_to_int32_le(header_buf[12:16])

    dbg("yaffs2_image_header: head_id=%d, version=%d, "\
            "chunk_size=%d, spare_size=%d" % \
            (yaffs2_head_id, yaffs2_version, yaffs2_byte_per_chunk,
                yaffs2_byte_nand_spare))
    header_struct_fmt = 'LLLL'
    yaffs2_img_header = struct.pack(header_struct_fmt, yaffs2_head_id, \
            yaffs2_version, yaffs2_byte_per_chunk, yaffs2_byte_nand_spare)
    if yaffs2_head_id == YAFFS2_MAGIC_HEAD_ID and \
                yaffs2_version == YAFFS2_VERSION_4096:
        size_nand_page = YAFFS2_CHUNKSIZE_4K
        size_nand_spare = YAFFS2_SPARESIZE_4K
        header_size = struct.calcsize(header_struct_fmt)
    elif  yaffs2_head_id == YAFFS2_MAGIC_HEAD_ID and \
                yaffs2_version == YAFFS2_VERSION_2048:
        size_nand_page = YAFFS2_CHUNKSIZE_2K
        size_nand_spare = YAFFS2_SPARESIZE_2K
        header_size = struct.calcsize(header_struct_fmt)
    else:
        dbg("yaffs2 version is none")
        # im9828 v1/v3 uses 2KB size page and 64B size spare
        size_nand_page = YAFFS2_CHUNKSIZE_2K
        size_nand_spare = YAFFS2_SPARESIZE_2K

    return (header_size, size_nand_page, size_nand_spare)


def usb_burn_yaffs2(sg_fd, img_buf, nand_part_start_addr, nand_part_size):
    assert(isinstance(sg_fd, int))
    assert(isinstance(nand_part_start_addr, int))
    assert(isinstance(nand_part_size, int))
    ret = False
    dbg(get_cur_func_name() +
        "(): nand_part_start_addr=0x%.8x, nand_part_size=0x%.8x" % 
            (nand_part_start_addr, nand_part_size))
    sector_offset = nand_part_start_addr / SECTOR_SIZE
    img_total_size = len(img_buf)
    dbg("img_total_size=0x%x" % img_total_size)

    # erase nand partition
    usb_erase_yaffs2(sg_fd, nand_part_start_addr, nand_part_size)

    # write yaffs2
    info("start to write yaffs2")

    size_written, size_nand_page, size_nand_spare = \
            parse_yaffs2_header(img_buf[:SIZE_YAFFS2_HEADER])
    pair_cnt_per_nand_block = SIZE_PER_WRITE / size_nand_page
    dbg("size_written=0x%.4x, size_nand_page=0x%.4x, "\
            "size_nand_spare=0x%.4x" %
            (size_written, size_nand_page, size_nand_spare))

    size_per_pair = size_nand_page + size_nand_spare
    size_page_per_nand_block = size_nand_page*pair_cnt_per_nand_block
    size_spare_per_nand_block = size_nand_spare*pair_cnt_per_nand_block
    size_per_nand_block = size_page_per_nand_block + size_spare_per_nand_block
    assert(isinstance(size_per_nand_block, int))

    page_buf = ctypes.create_string_buffer(size_page_per_nand_block)
    spare_buf = ctypes.create_string_buffer(size_spare_per_nand_block)
    while size_written < img_total_size:
        page_buf[:] = NULL_CHAR * size_page_per_nand_block
        spare_buf[:] = NULL_CHAR * size_spare_per_nand_block
        size_to_write = min(img_total_size - size_written, size_per_nand_block)
        pair_cnt = size_to_write / size_per_pair
        # dbg(get_cur_func_name() + \
        #   "(): size_written=%.8x, size_to_write=%.8x, pair_cnt=%.2x"%
        #   (size_written, size_to_write, pair_cnt))

        # create buf
        for i in range(pair_cnt):
            img_buf_page_start  = size_written + i*size_per_pair
            img_buf_page_end    = img_buf_page_start + size_nand_page
            img_buf_spare_start = img_buf_page_end
            img_buf_spare_end   = img_buf_spare_start + size_nand_spare
            page_buf_start = i*size_nand_page
            spare_buf_start = i*size_nand_spare
            page_buf[page_buf_start:page_buf_start+size_nand_page]=\
                    img_buf[img_buf_page_start:img_buf_page_end]
            spare_buf[spare_buf_start:spare_buf_start+size_nand_spare]=\
                    img_buf[img_buf_spare_start:img_buf_spare_end]

        # dbg("pair_cnt=", pair_cnt)
        # do write to disk
        print('.', sep='', end='')
        sys.stdout.flush()
        # dbg("write spare_buf")
        write_blocks(sg_fd, spare_buf.raw,
                USB_PROGRAMMER_WR_NAND_SPARE_DATA,
                size_spare_per_nand_block / SECTOR_SIZE)
        # dbg("write page_buf")
        write_blocks(sg_fd, page_buf.raw, sector_offset, 
                (pair_cnt * size_nand_page) / SECTOR_SIZE)
        size_written += size_to_write
        sector_offset += SECTOR_NUM_PER_WRITE

    print()
    dbg("write yaffs2 to nand finished")
    buf = chr(0x00)
    buf += NULL_CHAR * (SECTOR_SIZE - 1)
    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_SPARE_DATA_CTRL, 1)


if __name__ == "__main__":
    pass
