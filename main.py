#!/usr/bin/env python

import io
import os
import glob
import my_sg
from debug_util import *

COMMAND_AREA_SIZE = 0X100
USB_PROGRAMMER_VERIFY_BL_VALIDITY_OFFSET = 0x04
USB_PROGRAMMER_GET_BL_SW_VERSION_OFFSET = 0x06

#Send Download mode to board's RAM loader
USB_PROGRAMMER_DOWNLOAD_WRITE_LOADER_EXISTENCE = 0x50000210

MAGIC_WORD = '\xde\xad\xbe\xef'
BL_MAGIC_STRING = "InfoMax Communication"

svn_revision = 16
dl_major_version = 1
dl_minor_version = 2
dl_small_version = svn_revision

def check_magic_str(disk_path, lastblock):
    cmd_sector_base = lastblock - COMMAND_AREA_SIZE
    #read magic hex, should be 0xdeadbeef
    magic_block = my_sg.read_blocks(disk_path, \
            cmd_sector_base + USB_PROGRAMMER_VERIFY_BL_VALIDITY_OFFSET, 1)
    if not magic_block:
        warn("*** read magic block failed")
        return
    my_sg.print_str_hex(magic_block[:4])
    if magic_block[:4] == MAGIC_WORD:
        info("magic word match")
    else:
        warn("*** magic word not match")
        return False
    if BL_MAGIC_STRING in magic_block:
        info("magic string match")
    else:
        warn("*** magic string didn't match")
        return False
    return True

def change_to_dl_mode(disk_path):
    global dl_major_version
    global dl_minor_version
    global dl_small_version
    fill_sector = my_sg.NULL_CHAR * 9
    fill_sector += chr(dl_major_version / 10)
    fill_sector += chr(dl_major_version % 10)
    fill_sector += my_sg.NULL_CHAR
    fill_sector += chr(dl_minor_version / 10)
    fill_sector += chr(dl_minor_version % 10)
    fill_sector += my_sg.NULL_CHAR
    fill_sector += chr(dl_small_version / 10)
    fill_sector += chr(dl_small_version % 10)
    fill_sector += my_sg.NULL_CHAR * (512 - len(fill_sector))
    ret = my_sg.write_blocks(disk_path, fill_sector, \
            USB_PROGRAMMER_DOWNLOAD_WRITE_LOADER_EXISTENCE, 1 )
    return ret

def check_board_sw_version(disk_path, lastblock):
    cmd_sector_base = lastblock - COMMAND_AREA_SIZE
    version_sector = my_sg.read_blocks( disk_path, \
            cmd_sector_base + USB_PROGRAMMER_GET_BL_SW_VERSION_OFFSET, 1)
    if not version_sector:
        return False
    if ord(version_sector[8]) == 1:
        blOneStageReady = False
        info("ROM Type: %s" % version_sector[9:11])
    if ord(version_sector[8]) == 2:
        blOneStageReady = False
        info("Flash Type: %s" % version_sector[9:11])
    if ord(version_sector[8]) == 3:
        major_version = int(version_sector[9:11])
        minor_version = int(version_sector[12:14])
        small_version = int(version_sector[15:17])
        if major_version != 0 and \
                minor_version != 0 and \
                small_version != 0:
            blOneStageReady = True
            info("RAM Type: %s" % version_sector[9:17])
        if small_version >= 6:
            dl_ram_version_check = True
            ret = change_to_dl_mode(disk_path)
            return ret
    else:
        wtf("need ramloader small version >= 6")
        return False





def get_im_disk_path():
    disk_list = glob.glob('/dev/sg[1-9]')
    print disk_list
    for disk_path in disk_list:
        print "\nchecking: ", disk_path
        lastblock, block_size = my_sg.read_lastblock_num(disk_path)
        if block_size and block_size != my_sg.SECTOR_SIZE:
            warn("unable to handle block_size=%d, must be %d" \
                    % (block_size, my_sg.SECTOR_SIZE))
        if not lastblock:
            warn("*** fail to read: ", disk_path)
            continue

        info("lastblock=%d" % lastblock)
        if check_magic_str(disk_path, lastblock):
            info("Aha! Device Found! Good Luck!")
            ret = check_board_sw_version(disk_path, lastblock)
            if ret:
                return disk_path
        return None
    return None



get_im_disk_path()


