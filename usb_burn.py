import os
import io
import sys
from debug_util import *
from utils import *
from const_vars import *
from usb_generic import read_blocks, write_blocks,write_large_buf, get_dev_block_info
import struct
import ctypes
import time


def set_dl_img_type(sg_fd, dl_img_type, nand_part_start_addr):
    buf = chr(dl_img_type) + NULL_CHAR * (SECTOR_SIZE - 1)
    dbg( get_cur_func_name() + ": len of buf=%d" % len(buf))
    ret = write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_BOOT_DEVICE, 1)
    if not ret:
        wtf("fail to set download img type")
    buf = int32_to_str(nand_part_start_addr)
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
    # start write img
    write_large_buf(sg_fd, img_buf, sector_offset)


def usb_burn_raw(sg_fd, img_buf, nand_part_start_addr, nand_part_size):
    sector_offset = nand_part_start_addr / SECTOR_SIZE
    buf = int32_to_str(nand_part_start_addr)
    buf += int32_to_str(nand_part_size)
    buf += NULL_CHAR * (SECTOR_SIZE - len(buf))
    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)
    write_blocks(sg_fd, buf, USB_PROGRAMMER_ERASE_NAND_CMD, 1)
    # start write img
    write_large_buf(sg_fd, img_buf, sector_offset)


def parse_yaffs2_header(header_buf):
    header_size = 0
    yaffs_head_id = str_to_int32_le(header_buf[0:4])
    yaffs_version = str_to_int32_le(header_buf[4:8])
    yaffs_byte_per_chunk = str_to_int32_le(header_buf[8:12])
    yaffs_byte_nand_spare = str_to_int32_le(header_buf[12:16])

    info("yaffs_image_header: head_id=%d, version=%d, chunk_size=%d, spare_size=%d" % \
            (yaffs_head_id, yaffs_version, yaffs_byte_per_chunk, yaffs_byte_nand_spare))
    header_struct_fmt = 'LLLL'
    yaffs_img_header = struct.pack(header_struct_fmt, yaffs_head_id, \
            yaffs_version, yaffs_byte_per_chunk, yaffs_byte_nand_spare)
    if yaffs_head_id == YAFFS_MAGIC_HEAD_ID and yaffs_version == YAFFS_VERSION_4096:
        size_nand_page = YAFFS_CHUNKSIZE_4K
        size_nand_spare = YAFFS_SPARESIZE_4K
        header_size = struct.calcsize(header_struct_fmt)
    elif  yaffs_head_id == YAFFS_MAGIC_HEAD_ID and yaffs_version == YAFFS_VERSION_2048:
        size_nand_page = YAFFS_CHUNKSIZE_2K
        size_nand_spare = YAFFS_SPARESIZE_2K
        header_size = struct.calcsize(header_struct_fmt)
    else:
        dbg("yaffs version is none")
        # im9828 v1/v3 uses 2KB size page and 64B size spare
        size_nand_page = YAFFS_CHUNKSIZE_2K
        size_nand_spare = YAFFS_SPARESIZE_2K

    return (header_size, size_nand_page, size_nand_spare)


def usb_burn_yaffs2(sg_fd, img_buf, nand_part_start_addr, nand_part_size):
    ret = False
    dbg(get_cur_func_name()+"(): nand_part_start_addr=%.8x, nand_part_size=%.8x" % 
            (nand_part_start_addr, nand_part_size))

    # erase nand partition
    buf = ctypes.create_string_buffer(SECTOR_SIZE)
    buf[0] = '\x01'
    write_blocks(sg_fd, buf.raw, USB_PROGRAMMER_SET_NAND_SPARE_DATA_CTRL, 1)

    buf[0:4] = int32_to_str(nand_part_start_addr)
    buf[4:8] = int32_to_str(nand_part_size)
    write_blocks(sg_fd, buf.raw, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)

    info("start to erase yaffs")
    nand_start_erase_addr = nand_part_start_addr
    nand_erase_size = nand_part_size
    while nand_erase_size > 0:
        size_to_erase = min(nand_erase_size, NAND_ERASE_MAX_LEN_PER_TIME)
        buf[0:4] = int32_to_str(nand_start_erase_addr)
        buf[4:8] = int32_to_str(size_to_erase)
        write_blocks(sg_fd, buf.raw, USB_PROGRAMMER_ERASE_NAND_CMD, 1)
        nand_start_erase_addr += size_to_erase
        nand_erase_size    -= size_to_erase
        print '.',
        sys.stdout.flush()
    #endof erase nand partition
    #exit(0)
    print
    # write yaffs
    info("start to write yaffs")
    sector_offset = nand_part_start_addr / SECTOR_SIZE
    img_total_size = len(img_buf)
    dbg("img_total_size=", img_total_size)

    size_written, size_nand_page, size_nand_spare = \
            parse_yaffs2_header(img_buf[:SIZE_YAFFS2_HEADER])
    pair_cnt_per_nand_block = SIZE_PER_WRITE/ size_nand_page
    dbg("size_written=0x%.4x, size_nand_page=%.4x, size_nand_spare=%.4x" %
            (size_written, size_nand_page, size_nand_spare))
    dbg( "pair_cnt_per_nand_block=", num_cnt_to_bb_per_time)
    size_per_pair = size_nand_page + size_nand_spare
    size_page_per_nand_block = size_nand_page*pair_cnt_per_nand_block
    size_spare_per_nand_block = size_nand_spare*pair_cnt_per_nand_block
    size_per_nand_block = size_per_pair*pair_cnt_per_nand_block

    page_buf = ctypes.create_string_buffer(size_page_per_nand_block)
    spare_buf = ctypes.create_string_buffer(size_spare_per_nand_block)
    while size_written < img_total_size:
        page_buf[:] = NULL_CHAR * size_page_per_nand_block
        spare_buf[:] = NULL_CHAR * size_spare_per_nand_block
        size_to_write = min(img_total_size - size_written, size_per_nand_block)
        pair_cnt = size_to_write/size_per_pair
#        dbg(get_cur_func_name() + \
#                "(): size_written=%.8x, size_to_write=%.8x, pair_cnt=%.2x" % \
#                (size_written, size_to_write, pair_cnt))

        # create buf
        for i in range(pair_cnt):
            img_buf_page_start  = size_written + i*size_per_pair
            img_buf_page_end    = img_buf_page_start + size_nand_page
            img_buf_spare_start = img_buf_page_end
            img_buf_spare_end   = img_buf_spare_start + size_nand_spare
            page_buf_start = i*size_nand_page
            spare_buf_start = i*size_nand_spare
            page_buf[page_buf_start:page_buf_start+size_nand_page] =\
                    img_buf[img_buf_page_start:img_buf_page_end]
            if page_buf[page_buf_start:page_buf_start+size_nand_page] !=\
                    img_buf[img_buf_page_start:img_buf_page_end]:
                wtf("why????")
            spare_buf[spare_buf_start:spare_buf_start+size_nand_spare] =\
                    img_buf[img_buf_spare_start:img_buf_spare_end]
            if spare_buf[spare_buf_start:spare_buf_start+size_nand_spare] !=\
                    img_buf[img_buf_spare_start:img_buf_spare_end]:
                wtf("why????????????")
        # do write to disk
        print ".",
        sys.stdout.flush()
#        dbg("pair_cnt=", pair_cnt)
#        dbg("write spare_buf")
        write_blocks(sg_fd, spare_buf.raw, USB_PROGRAMMER_WR_NAND_SPARE_DATA,
                size_spare_per_nand_block/SECTOR_SIZE)
#        dbg("write page_buf")
        write_blocks(sg_fd, page_buf.raw, sector_offset, 
                (pair_cnt * size_nand_page) / SECTOR_SIZE)
        size_written += size_to_write
        sector_offset += SECTOR_NUM_PER_WRITE
    print
    dbg("write yaffs to nand finished")
    buf[:] = NULL_CHAR * SECTOR_SIZE
    buf[0] = chr(0x00)
    write_blocks(sg_fd, buf.raw, USB_PROGRAMMER_SET_NAND_SPARE_DATA_CTRL, 1)
        


#def usb_burn(sg_fd, ):
    

if __name__ == "__main__":
    set_dl_img_type("/dev/sg2", 48, 0)
