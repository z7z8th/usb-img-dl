#!/usr/bin/env python

from const_vars import *
from config import *
from debug_util import *
from utils import *
from py_sg import write as sg_write
from py_sg import read as sg_read
from py_sg import SCSIError
import time


READ_CAPACITY = '\x25'
def get_dev_block_info(sg_fd):
    cmd = READ_CAPACITY + NULL_CHAR * 9  #READ_CAPACITY
    print_str_hex(cmd)
    buf = [0,0,0,0, 0,0,0,0]
    try:
        response = sg_read(sg_fd, cmd, 8, 2000)
    except SCSIError as e:
        print "SCSIError: ", e
        sg_fd.close()
        return (None, None)

    rd_cap_buff = [ord(one_char) for one_char in response]
    print rd_cap_buff
    lastblock = str_to_int32_be(response[0:4])
    print lastblock
    blocksize = str_to_int32_be(response[4:8])
    if debug:
#        print "response: ", len(response), " : ",
        print_str_hex(response)
        disk_cap = (lastblock+1) * blocksize
        info("lastblock=%lu" % lastblock)
        info("blocksize=%lu" % blocksize)
        info("capacity=%lu" % disk_cap)
        info("capacity=%f GB" % ( disk_cap/1024.0/1024.0/1024.0 ))
    return lastblock, blocksize


READ_10='\x28'
def read_blocks(sg_fd, sector_offset, sector_num):
    print "read_blocks"
    cmd = READ_10 + NULL_CHAR
    cmd += int32_to_str(sector_offset)
    cmd += NULL_CHAR
    cmd += chr((sector_num>>8) & 0xFFl)
    cmd += chr(sector_num & 0xFFl)
    cmd += NULL_CHAR
    print "cmd=",
    print_str_hex(cmd)

    try:
        response = sg_read(sg_fd, cmd, sector_num * SECTOR_SIZE, 2000 )
    except SCSIError as e:
        print "SCSIError: ", e
        sg_fd.close()
        return None
    #read_buf = [ord(one_char) for one_char in response]
    read_buf = response
    return read_buf


WRITE_10='\x2a'
def write_blocks(sg_fd, buf, sector_offset, sector_num):
#    print "write_blocks"
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
    dbg(get_cur_func_name() + ": img_total_size=%d" % img_total_size)
    dbg(get_cur_func_name() + ": total sector num=%f" % \
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

