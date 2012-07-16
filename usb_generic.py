#!/usr/bin/env python

import time
from py_sg import write as sg_write
from py_sg import read as sg_read
from py_sg import SCSIError

from const_vars import *
from config import *
from debug_util import *
from utils import *


READ_CAPACITY = '\x25'
def get_dev_block_info(sg_fd):
    cmd = READ_CAPACITY + NULL_CHAR * 9  #READ_CAPACITY
    try:
        read_buf = sg_read(sg_fd, cmd, 8, 200)
    except SCSIError as e:
        print "SCSIError: ", e
        return (None, None)

    lastblock = str_to_int32_be(read_buf[0:4])
    blocksize = str_to_int32_be(read_buf[4:8])

    disk_cap = (lastblock+1) * blocksize
    info("lastblock=", lastblock)
    info("blocksize=", blocksize)
    info("capacity=%ul, %f GB" % (disk_cap, disk_cap/1024.0/1024.0/1024.0))
    return lastblock, blocksize


READ_10='\x28'
def read_blocks(sg_fd, sector_offset, sector_num):
    cmd = READ_10 + NULL_CHAR
    cmd += int32_to_str(sector_offset)
    cmd += NULL_CHAR
    cmd += chr((sector_num>>8) & 0xFF)
    cmd += chr(sector_num & 0xFF)
    cmd += NULL_CHAR

    try:
        read_buf = sg_read(sg_fd, cmd, sector_num * SECTOR_SIZE, 200 )
    except SCSIError as e:
        print "SCSIError: ", e
        return None
    return read_buf


WRITE_10='\x2a'
def write_blocks(sg_fd, buf, sector_offset, sector_num):
    cmd = WRITE_10 + NULL_CHAR
    cmd += int32_to_str(sector_offset)
    cmd += NULL_CHAR
    cmd += chr((sector_num>>8) & 0xFF)
    cmd += chr(sector_num & 0xFF)
    cmd += NULL_CHAR

    ret = False
    try:
        response = sg_write(sg_fd, cmd, buf, 2000 )
        ret = True
    except SCSIError as e:
        print "SCSIError: %s" % e
    except OSError as e:
        print "OSError: ", e
    return ret


def write_large_buf(sg_fd, large_buf, sector_offset):
    img_total_size = len(large_buf)
    dbg(get_cur_func_name(), "(): img_total_size=", img_total_size)
    dbg(get_cur_func_name(), "(): total sector num=",
            (float(img_total_size)/SECTOR_SIZE))
    size_written = 0
    while size_written < img_total_size:
        buf_end_offset = min(img_total_size, size_written + SIZE_PER_WRITE)
        sector_num_write = (buf_end_offset - size_written + \
                SECTOR_SIZE - 1)/SECTOR_SIZE
        buf = large_buf[size_written : buf_end_offset]
        buf_len = buf_end_offset - size_written
        if buf_len < SIZE_PER_WRITE:
            align_len = ((buf_len+SECTOR_SIZE-1)/SECTOR_SIZE)*SECTOR_SIZE
            buf += NULL_CHAR * (align_len-buf_len)
        write_blocks(sg_fd, buf, sector_offset, sector_num_write)
        size_written += SIZE_PER_WRITE
        sector_offset += sector_num_write


if __name__ == "__main__":
    import sys
    print get_dev_block_info(sys.argv[1])

