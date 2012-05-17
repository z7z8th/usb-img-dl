#!/usr/bin/env python

import io
import os
import glob
import my_sg

COMMAND_AREA_SIZE=0X100
USB_PROGRAMMER_VERIFY_BL_VALIDITY_OFFSET=0x04
MAGIC_WORD = '\xde\xad\xbe\xef'
BL_MAGIC_STRING = "InfoMax Communication"


def check_magic_str(disk_path, lastblock):
    cmd_sector_base = lastblock - COMMAND_AREA_SIZE
    #read magic hex, should be 0xdeadbeef
    magic_block = my_sg.read_block(disk_path, \
            cmd_sector_base + USB_PROGRAMMER_VERIFY_BL_VALIDITY_OFFSET, 1)
    if not magic_block:
        print "*** read magic block failed"
        return
    my_sg.print_str_hex(magic_block[:4])
    if magic_block[:4] == MAGIC_WORD:
        print "magic word match"
    else:
        print "*** magic word not match"
        return False
    if BL_MAGIC_STRING in magic_block:
        print "magic string match"
    else:
        print "*** magic string didn't match"
        return False
    return True




    

def check_disks():
    disk_list = glob.glob('/dev/sg[1-9]')
    print disk_list
    for disk in disk_list:
        print
        print "checking: ", disk
        lastblock, block_size = my_sg.read_lastblock_num(disk)
        if block_size and block_size != my_sg.SECTOR_SIZE:
            print "unable to handle block_size=%d, must be %d" \
                    %(block_size, my_sg.SECTOR_SIZE)
        if not lastblock:
            print "*** fail to read: ", disk
            continue

        print "lastblock=", lastblock
        if check_magic_str(disk, lastblock):
            print "Aha! Device Found! Good Luck!"
            break




check_disks()
