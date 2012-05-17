#!/usr/bin/env python

import py_sg
import os, io
#import Py_buffer

cmd = '\x25\x00\x00\x00\x00\x00\x00\x00\x00\x00'
buf = [0,0,0,0, 0,0,0,0]
sg_fd = open('/dev/sg2', 'r')
response = py_sg.read(sg_fd, cmd, 8)
rd_cap_buff = [ ord(hex_val) for hex_val in response ]
print "response: ", len(response), " : ", rd_cap_buff
lastblock = (rd_cap_buff[0]<<24)|(rd_cap_buff[1]<<16)| \
        (rd_cap_buff[2]<<8)|(rd_cap_buff[3])
blocksize =  (rd_cap_buff[4]<<24)|(rd_cap_buff[5]<<16)| \
        (rd_cap_buff[6]<<8)|(rd_cap_buff[7])
disk_cap = (lastblock+1) * blocksize

print "lastblock=", lastblock
print "blocksize=", blocksize
print "capacity=%lu" % disk_cap
print "capacity=%lu GB" % ( disk_cap/1024/1024/1024 )

