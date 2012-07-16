#!/usr/bin/env python
from __future__ import print_function
import os
import sys
import time
import glob

from const_vars import *
from runtime_global_vars import *
import config
from debug_util import *
from usb_generic import read_blocks, write_blocks, get_dev_block_info


def check_magic_str(sg_fd, cmd_sector_base):
    #read magic hex, should be 0xdeadbeef
    magic_block = read_blocks(sg_fd, \
            cmd_sector_base + USB_PROGRAMMER_VERIFY_BL_VALIDITY_OFFSET, 1)
    if not magic_block:
        return False
    if config.debug:
        print_str_hex(magic_block[:4])
    if magic_block[:4] != MAGIC_WORD:
        return False
    if BL_MAGIC_STRING not in magic_block:
        return False
    return True

def change_to_dl_mode(sg_fd):
    global dl_major_version
    global dl_minor_version
    global dl_small_version
    fill_sector = NULL_CHAR * 9
    fill_sector += chr(dl_major_version / 10)
    fill_sector += chr(dl_major_version % 10)
    fill_sector += NULL_CHAR
    fill_sector += chr(dl_minor_version / 10)
    fill_sector += chr(dl_minor_version % 10)
    fill_sector += NULL_CHAR
    fill_sector += chr(dl_small_version / 10)
    fill_sector += chr(dl_small_version % 10)
    fill_sector += NULL_CHAR * (512 - len(fill_sector))
    ret = write_blocks(sg_fd, fill_sector, \
            USB_PROGRAMMER_DOWNLOAD_WRITE_LOADER_EXISTENCE, 1 )
    return ret

def check_ram_loader_version(sg_fd, cmd_sector_base):
    global blOneStageReady
    global dl_small_version
    version_sector = read_blocks( sg_fd, \
            cmd_sector_base + USB_PROGRAMMER_GET_BL_SW_VERSION_OFFSET, 1)
    if not version_sector:
        return False
    blOneStageReady = False
    if ord(version_sector[8]) == 1:
        info("ROM Type: %s" % version_sector[9:11])
    if ord(version_sector[8]) == 2:
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
            return True
        else:
            dl_ram_version_check = False
            os.close(sg_fd)
            wtf("need ramloader small version >= 6")
            return False
    return False


def get_dev_type(sg_fd, cmd_sector_base):
    dev_type_sector = read_blocks(sg_fd, \
            cmd_sector_base + USB_PROGRAMMER_GET_DEV_TYPE_OFFSET, 1)
    if ord(dev_type_sector[8]) == FLASH_DEV_TYPE_IS_NAND:
        ucDevType = FLASH_DEV_TYPE_IS_NAND
        info("dev type is nand flash")
    elif ord(dev_type_sector[8]) == FLASH_DEV_TYPE_IS_NOR:
        ucDevType = FLASH_DEV_TYPE_IS_NOR
        info("dev type is nor flash")
    else:
        ucDevType = 0x00
        warn("dev type is not recognized")
    return ucDevType



def get_im_sg_fd():
    sg_list = glob.glob('/dev/sg[1-9]*')
    sg_fd = -1
    for sg_path in sg_list:
        if sg_fd >= 0:
            os.close(sg_fd)
        try:
            sg_fd = os.open(sg_path, os.O_SYNC | os.O_RDWR)
            if sg_fd < 0:
                continue
            dbg("\nchecking: ", sg_path)
            lastblock, block_size = get_dev_block_info(sg_fd)
            if block_size and block_size != SECTOR_SIZE:
                warn("unable to handle block_size=%d, must be %d" \
                        % (block_size, SECTOR_SIZE))
                continue
            if not lastblock:
                #warn("fail to read lastblock of ", sg_fd)
                continue

            info("lastblock=%d" % lastblock)
            cmd_sector_base = lastblock - COMMAND_AREA_SIZE
            ret = check_magic_str(sg_fd, cmd_sector_base)
            if ret: 
                info("magic string match")
            else:
                warn("magic string not match, this is ok to ignore")
                continue

            ret = check_ram_loader_version(sg_fd, cmd_sector_base)
            if ret:
                info("ramloader version check succeed")
            else:
                wtf("ramloader version check failed")

            ret = change_to_dl_mode(sg_fd)
            if ret:
                info("change device to download mode succeed")
            else:
                wtf("change device to download mode failed")

            ret = get_dev_type(sg_fd, cmd_sector_base)
            if ret:
                info("get dev type succeed")
            else:
                warn("get dev type failed, maybe this is a bug")
                continue
            return sg_fd
        except EnvironmentError as e:
            pass
            #err(str(e))
    if sg_fd >= 0:
        os.close(sg_fd)
    return None

def wait_and_get_im_sg_fd():
    info("waiting for device to appear")
    while True:
        sg_fd = get_im_sg_fd()
        if sg_fd:
            return sg_fd
        time.sleep(0.5)
        print('.', sep='', end='')
        sys.stdout.flush()



if __name__ == "__main__":
    wait_and_get_im_sg_fd()
