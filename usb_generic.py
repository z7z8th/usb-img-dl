#!/usr/bin/env python

import time
from py_sg import write as sg_write
from py_sg import read as sg_read
from py_sg import SCSIError

import configs
from const_vars import *
from debug_utils import *
from utils import *

INQUIRY = 0x12
INQUIRY_DATA_LEN = 0xFF
def inquiry_sg_dev_info(sg_fd):
    cmd = chr(INQUIRY) + NULL_CHAR*3 + chr(INQUIRY_DATA_LEN) + NULL_CHAR
    try:
        inquiry_buf = sg_read(sg_fd, cmd, INQUIRY_DATA_LEN, 800)
    except SCSIError as e:
        #warn("SCSIError: ", e)
        return None
    assert(len(inquiry_buf) >= min(36, INQUIRY_DATA_LEN) )
    periheral_qualifer = (ord(inquiry_buf[0]) & 0xE0) >> 5
    periheral_dev_type = ord(inquiry_buf[0]) & 0x1F
    rmb = (ord(inquiry_buf[1]) & 0x80) >> 7
    version = ord(inquiry_buf[2])
    t10_vendor_ident = inquiry_buf[8:16]
    product_ident = inquiry_buf[16:32]
    product_rev_lvl = inquiry_buf[32:36]
    #vendor_specific = inquiry_buf[36:56]
    
    dbg("len(inquiry_buf)=", len(inquiry_buf))
    dbg("periheral_qualifer=0x%02x" % periheral_qualifer)
    dbg("periheral_dev_type=0x%02x" % periheral_dev_type)
    dbg("removable=0x%02x" % rmb)
    dbg("version=0x%02x" % version)
    dbg("t10_vendor_ident=", t10_vendor_ident)
    dbg("product_ident=", product_ident)
    dbg("product_rev_lvl=", product_rev_lvl)
    #dbg("vendor_specific=", vendor_specific)
    return (periheral_qualifer, periheral_dev_type, t10_vendor_ident, product_ident)


READ_CAPACITY = 0x25
def get_dev_block_info(sg_fd):
    cmd = chr(READ_CAPACITY) + NULL_CHAR * 9  #READ_CAPACITY
    try:
        read_buf = sg_read(sg_fd, cmd, 8, 800)
    except SCSIError as e:
        warn("SCSIError: ", e)
        return (None, None)

    lastblock = str_to_int32_be(read_buf[0:4])
    blocksize = str_to_int32_be(read_buf[4:8])

    disk_cap = (lastblock+1) * blocksize
    dbg("lastblock=", lastblock)
    dbg("blocksize=", blocksize)
    dbg("capacity=%ul, %f GB" % (disk_cap, disk_cap/1024.0/1024.0/1024.0))
    return lastblock, blocksize


READ_10 = 0x28
def read_blocks(sg_fd, sector_offset, sector_num):
    cmd = chr(READ_10) + NULL_CHAR
    cmd += int32_to_str(sector_offset)
    cmd += NULL_CHAR
    cmd += chr((sector_num>>8) & 0xFF)
    cmd += chr(sector_num & 0xFF)
    cmd += NULL_CHAR

    try:
        read_buf = sg_read(sg_fd, cmd, sector_num * SECTOR_SIZE, 800 )
    except SCSIError as e:
        warn(get_cur_func_name()+"(): SCSIError: ", e)
        return None
    return read_buf


WRITE_10 = 0x2a
def write_blocks(sg_fd, buf, sector_offset, sector_num, timeout=1500):
    dbg("sg_fd=%d, sector_offset=%x, sector_num=%x, timeout=%d" % \
            (sg_fd, sector_offset, sector_num, timeout))
    cmd = chr(WRITE_10) + NULL_CHAR
    cmd += int32_to_str(sector_offset)
    cmd += NULL_CHAR
    cmd += chr((sector_num>>8) & 0xFF)
    cmd += chr(sector_num & 0xFF)
    cmd += NULL_CHAR

    ret = False
    try:
        response = sg_write(sg_fd, cmd, buf, timeout)
        ret = True
    except SCSIError as e:
        warn(get_cur_func_name()+"(): SCSIError:", e)
    #except OSError as e:
    #    warn(get_cur_func_name()+"(): OSError: ", e)

    # sleep for yaffs2 tragedy, I think it's not need
    # the tragedy should be caused by multi process access
    #time.sleep(0.005)
    return ret


def write_large_buf(sg_fd, large_buf, sector_offset, size_per_write = SIZE_PER_WRITE):
    img_total_size = len(large_buf)
    dbg(get_cur_func_name(), "(): img_total_size=", img_total_size)
    dbg(get_cur_func_name(), "(): total sector num=",
            (float(img_total_size)/SECTOR_SIZE))
    size_written = 0
    while size_written < img_total_size:
        buf_end_offset = min(img_total_size, size_written + size_per_write)
        sector_num_write = (buf_end_offset - size_written + \
                SECTOR_SIZE - 1)/SECTOR_SIZE
        buf = large_buf[size_written : buf_end_offset]
        buf_len = buf_end_offset - size_written
        if buf_len < size_per_write:
            buf += NULL_CHAR * (sector_num_write*SECTOR_SIZE - buf_len)
        write_blocks(sg_fd, buf, sector_offset, sector_num_write)
        size_written += size_per_write
        sector_offset += sector_num_write
    dbg("end of " + get_cur_func_name())


if __name__ == "__main__":
    configs.debug = True
    import sys
    sg_path = sys.argv[1]
    sg_fd = os.open(sg_path, os.O_SYNC | os.O_RDWR)
    assert(sg_fd >= 0)
    inquiry_sg_dev_info(sg_fd)
    print(get_dev_block_info(sg_fd))
    os.close(sg_fd)



