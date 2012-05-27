#!/usr/bin/env python

from const_vars import *
from debug_util import *
import py_sg


READ_CAPACITY = '\x25'
def get_dev_block_info(sg_path):
    cmd = READ_CAPACITY + NULL_CHAR * 9  #READ_CAPACITY
    print_str_hex(cmd)
    buf = [0,0,0,0, 0,0,0,0]
    sg_fd = open(sg_path, 'rb')
    try:
        response = py_sg.read(sg_fd, cmd, 8, 2000)
    except py_sg.SCSIError as e:
        print "SCSIError: ", e
        sg_fd.close()
        return (None, None)

    rd_cap_buff = [ord(one_char) for one_char in response]
    lastblock = (rd_cap_buff[0]<<24)|(rd_cap_buff[1]<<16)| \
            (rd_cap_buff[2]<<8)|(rd_cap_buff[3])
    blocksize =  (rd_cap_buff[4]<<24)|(rd_cap_buff[5]<<16)| \
            (rd_cap_buff[6]<<8)|(rd_cap_buff[7])
    if debug:
#        print "response: ", len(response), " : ",
        print_str_hex(response)
        disk_cap = (lastblock+1) * blocksize
        print "lastblock=", lastblock
        print "blocksize=", blocksize
        print "capacity=%lu" % disk_cap
        print "capacity=%f GB" % ( disk_cap/1024.0/1024.0/1024.0 )
    sg_fd.close()
    return lastblock, blocksize


READ_10='\x28'
def read_blocks(sg_path, sector_offset, sector_num):
    print "read_blocks"
    cmd = READ_10 + NULL_CHAR
    cmd += chr((sector_offset>>24) & 0xFFl)
    cmd += chr((sector_offset>>16) & 0xFFl)
    cmd += chr((sector_offset>>8) & 0xFFl)
    cmd += chr(sector_offset & 0xFFl)
    cmd += NULL_CHAR
    cmd += chr((sector_num>>8) & 0xFFl)
    cmd += chr(sector_num & 0xFFl)
    cmd += NULL_CHAR
    print "cmd=",
    print_str_hex(cmd)

    sg_fd = open(sg_path, 'rb')
    try:
        response = py_sg.read(sg_fd, cmd, sector_num * SECTOR_SIZE, 2000 )
    except py_sg.SCSIError as e:
        print "SCSIError: ", e
        sg_fd.close()
        return None
    #read_buf = [ord(one_char) for one_char in response]
    read_buf = response
    sg_fd.close()
    return read_buf


WRITE_10='\x2a'
def write_blocks(sg_path, buf, sector_offset, sector_num):
#    print "write_blocks"
    cmd = WRITE_10 + NULL_CHAR
    cmd += chr((sector_offset>>24) & 0xFFl)
    cmd += chr((sector_offset>>16) & 0xFFl)
    cmd += chr((sector_offset>>8) & 0xFFl)
    cmd += chr(sector_offset & 0xFFl)
    cmd += NULL_CHAR
    cmd += chr((sector_num>>8) & 0xFFl)
    cmd += chr(sector_num & 0xFFl)
    cmd += NULL_CHAR
#    print "cmd=",
#    print_str_hex(cmd)

    sg_fd = open(sg_path, 'wb')
    ret = False
    try:
        response = py_sg.write(sg_fd, cmd, buf, 2000 )
        ret = True
    except py_sg.SCSIError as e:
        print "SCSIError: %s" % e
    except OSError as e:
        print "OSError: ", e
    sg_fd.close()
    return ret

if __name__ == "__main__":
    import sys
    print get_dev_block_info(sys.argv[1])

