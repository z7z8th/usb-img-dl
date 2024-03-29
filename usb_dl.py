from __future__ import print_function
import os
import io
import sys
import struct
import time
import array
import mmap
import random
from usb.core import USBError

from const_vars import *
from debug_utils import *
from utils import *
import mtd_part_alloc
from usb_misc import set_dl_img_type
from usb_generic import read_sectors, write_sectors, RETRY_MAX
from usb_part import *
from usb_erase import *


def write_large_buf(usbdldev, large_buf, sector_offset,
                    size_per_write = SIZE_PER_WRITE, retry_cnt=RETRY_MAX):
    img_total_size = len(large_buf)
    dbg(get_cur_func_name(), "(): img_total_size=", img_total_size)
    dbg(get_cur_func_name(), "(): total sector num=",
            (float(img_total_size)/SECTOR_SIZE))
    usbdldev.dev_info.set_fraction(0)
    size_written = 0
    while size_written < img_total_size:
        buf_end_offset = min(img_total_size, size_written + size_per_write)
        sector_num_write = (buf_end_offset - size_written + \
                SECTOR_SIZE - 1)/SECTOR_SIZE
        buf = large_buf[size_written : buf_end_offset]
        buf_len = buf_end_offset - size_written
        if buf_len < size_per_write:
            buf += NULL_CHAR * (sector_num_write*SECTOR_SIZE - buf_len)
        write_sectors(usbdldev, buf, sector_offset, sector_num_write, retry_cnt=retry_cnt)
        size_written += size_per_write
        sector_offset += sector_num_write
        usbdldev.dev_info.set_fraction(float(size_written)/img_total_size)
    dbg("End of " + get_cur_func_name())


def usb_dl_ram_loader(usbdldev, img_buf):
    dbg("enter: ", get_cur_func_name())
    sys.stdout.flush()
    usbdldev.dev_info.set_info("Updating Ramloader")
    usbdldev.dev_info.set_status("update")
    usbdldev.dev_info.set_fraction(0)

    RAMLOADER_SECTOR_OFFSET = 0   # the first sector, of course
    write_large_buf(usbdldev, img_buf, RAMLOADER_SECTOR_OFFSET, SECTOR_SIZE)
    usbdldev.dev_info.set_fraction(1)
    
    info("^^^^^^^ ram loader sent")
    usbdldev.dev_info.set_info("Ramloader restarting ...")
    time.sleep(random.randint(0, usbdldev.reboot_delay))
    try:
        write_sectors(usbdldev, img_buf[:SECTOR_SIZE],
                      USB_PROGRAMMER_FINISH_MAGIC_WORD, 1, retry_cnt=0)
    except USBError as e:
        #warn("USBError", e)
        warn("Updated ram loader is restarting...")
    info("Waiting for new ram_loader to take affect")


def usb_dl_ram_loader_file_to_ram(usbdldev, loader_path):
    dbg("enter: ", get_cur_func_name())
    if not os.path.exists(loader_path):
        wtf("No such file: ", loader_path)
    set_dl_img_type(usbdldev, DOWNLOAD_TYPE_RAM, RAM_BOOT_BASE_ADDR)
    with open(loader_path, 'rb') as img_fd:
        img_buf = mmap.mmap(img_fd.fileno(), 0, mmap.MAP_PRIVATE, mmap.PROT_READ)
        usb_dl_ram_loader(usbdldev, img_buf)
        img_buf.close()


def usb_dl_dyn_id(usbdldev, img_buf, dyn_id):
#    usb_erase_dyn_id(usbdldev, dyn_id)
    # set nand partition info
    set_part_dyn_id(usbdldev, dyn_id)
    sector_offset = mtd_part_alloc.DYN_ID_INIT_OFFSET / SECTOR_SIZE
    # start write img
    write_large_buf(usbdldev, img_buf, sector_offset)


def usb_dl_raw(usbdldev, img_buf, mtd_part_start_addr, mtd_part_size):
    sector_offset = mtd_part_start_addr / SECTOR_SIZE
    # set part info first
    set_part_generic(usbdldev, mtd_part_start_addr, mtd_part_size, False)
    # start write img
    write_large_buf(usbdldev, img_buf, sector_offset)


def parse_yaffs2_header(header_buf):
    header_size = 0
    yaffs2_head_id = str_le_to_int32_le(header_buf[0:4])
    yaffs2_version = str_le_to_int32_le(header_buf[4:8])
    yaffs2_byte_per_chunk = str_le_to_int32_le(header_buf[8:12])
    yaffs2_byte_nand_spare = str_le_to_int32_le(header_buf[12:16])

    dbg("Yaffs2_image_header: head_id=%d, version=%d, "\
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
        dbg("Yaffs2 version is none")
        # im9828 v1/v3 uses 2KB size page and 64B size spare
        size_nand_page = YAFFS2_CHUNKSIZE_2K
        size_nand_spare = YAFFS2_SPARESIZE_2K

    return (header_size, size_nand_page, size_nand_spare)


def usb_dl_yaffs2(usbdldev, img_buf, mtd_part_start_addr, mtd_part_size):
    # assert(isinstance(usbdldev, int))
    assert(isinstance(mtd_part_start_addr, int))
    assert(isinstance(mtd_part_size, int))

    ret = False
    dbg(get_cur_func_name() +
        "(): mtd_part_start_addr=0x%.8x, mtd_part_size=0x%.8x" % 
            (mtd_part_start_addr, mtd_part_size))
    sector_offset = mtd_part_start_addr / SECTOR_SIZE
    img_total_size = len(img_buf)
    dbg("img_total_size=0x%x" % img_total_size)

    set_part_generic(usbdldev, mtd_part_start_addr, mtd_part_size, True)

    # write yaffs2
    dbg("Start to write yaffs2")
    usbdldev.dev_info.set_fraction(0)
    
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

    page_buf = array.array('c', NULL_CHAR * size_page_per_nand_block)
    spare_buf = array.array('c', NULL_CHAR * size_spare_per_nand_block)
    while size_written < img_total_size:
        #page_buf[:] = NULL_CHAR * size_page_per_nand_block
        #spare_buf[:] = NULL_CHAR * size_spare_per_nand_block
        size_to_write = min(img_total_size - size_written, size_per_nand_block)
        if size_to_write < size_per_pair:
            break
        is_last_block = (size_to_write < size_per_nand_block)
        pair_cnt = size_to_write / size_per_pair
        # dbg(get_cur_func_name() + \
        #    "(): size_written=%.8x, size_to_write=%.8x, pair_cnt=%.2x"%
        #    (size_written, size_to_write, pair_cnt))

        # create buf
        for i in range(pair_cnt):
            img_buf_page_start  = size_written + i*size_per_pair
            img_buf_page_end    = img_buf_page_start + size_nand_page
            img_buf_spare_start = img_buf_page_end
            img_buf_spare_end   = img_buf_spare_start + size_nand_spare
            page_buf_start = i*size_nand_page
            spare_buf_start = i*size_nand_spare
            page_buf[page_buf_start:page_buf_start+size_nand_page]=\
                    array.array('c', img_buf[img_buf_page_start:img_buf_page_end])
            spare_buf[spare_buf_start:spare_buf_start+size_nand_spare]=\
                    array.array('c', img_buf[img_buf_spare_start:img_buf_spare_end])

        page_buf_fill_cnt = pair_cnt * size_nand_page
        spare_buf_fill_cnt = pair_cnt * size_nand_spare
        page_buf[page_buf_fill_cnt:] = array.array('c', 
                NULL_CHAR * (size_page_per_nand_block - page_buf_fill_cnt))
        spare_buf[spare_buf_fill_cnt:] = array.array('c', 
                NULL_CHAR * (size_spare_per_nand_block - spare_buf_fill_cnt))

        # do write to disk
        if is_last_block:
            dbg("Write spare_buf, size=0x%x" % (size_nand_spare * pair_cnt))
        # dbg("write spare_buf")
        write_sectors(usbdldev, spare_buf,
                USB_PROGRAMMER_WR_NAND_SPARE_DATA,
                size_spare_per_nand_block / SECTOR_SIZE)
        if is_last_block:
            dbg("Write page_buf, size=0x%x" % (size_nand_page * pair_cnt))
        #sys.stdout.flush()
        # dbg("write page_buf")
        #write_sectors(usbdldev, page_buf, sector_offset, 
        #        (pair_cnt * size_nand_page) / SECTOR_SIZE)
        write_sectors(usbdldev, page_buf, sector_offset, 
                SECTOR_NUM_PER_WRITE)
        size_written += size_to_write
        sector_offset += SECTOR_NUM_PER_WRITE
        usbdldev.dev_info.set_fraction(float(size_written)/img_total_size)

    dbg("Write yaffs2 to nand finished")
    buf = chr(0x00)
    buf += NULL_CHAR * (SECTOR_SIZE - 1)
    write_sectors(usbdldev, buf, USB_PROGRAMMER_SET_NAND_SPARE_DATA_CTRL, 1)


if __name__ == "__main__":
    pass
