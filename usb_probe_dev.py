#!/usr/bin/env python

from const_vars import *
from debug_util import *
import sys
import glob
from usb_generic import read_blocks, write_blocks, get_dev_block_info
import time

COMMAND_AREA_SIZE = 0X100
USB_PROGRAMMER_VERIFY_BL_VALIDITY_OFFSET = 0x04
USB_PROGRAMMER_GET_BL_SW_VERSION_OFFSET = 0x06
USB_PROGRAMMER_GET_DEV_TYPE_OFFSET = 0x07

#Send Download mode to board's RAM loader
USB_PROGRAMMER_DOWNLOAD_WRITE_LOADER_EXISTENCE = 0x50000210

FLASH_DEV_TYPE_IS_NOR = 0x01
FLASH_DEV_TYPE_IS_NAND = 0x02

MAGIC_WORD = '\xde\xad\xbe\xef'
BL_MAGIC_STRING = "InfoMax Communication"

svn_revision = 16
dl_major_version = 1
dl_minor_version = 2
dl_small_version = svn_revision
blOneStageReady = False
dl_small_version = False

def check_magic_str(sg_fd, cmd_sector_base):
    #read magic hex, should be 0xdeadbeef
    magic_block = read_blocks(sg_fd, \
            cmd_sector_base + USB_PROGRAMMER_VERIFY_BL_VALIDITY_OFFSET, 1)
    if not magic_block:
        warn("*** read magic block failed")
        return
    print_str_hex(magic_block[:4])
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
        err("read ram loader version sector failed")
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
            return True
        else:
            dl_ram_version_check = False
            sg_fd.close()
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
    return ucDevType



def get_im_sg_path():
    sg_list = glob.glob('/dev/sg[1-9]*')
    #print sg_list
    for sg_path in sg_list:
        try:
            with open(sg_path, 'r+b') as sg_fd:
                dbg("\nchecking: ", sg_path)
                lastblock, block_size = get_dev_block_info(sg_fd)
                if block_size and block_size != SECTOR_SIZE:
                    warn("unable to handle block_size=%d, must be %d" \
                            % (block_size, SECTOR_SIZE))
                if not lastblock:
                    warn("*** fail to read: " + sg_fd)
                    return None    # to delete
                    continue

                info("lastblock=%d" % lastblock)
                cmd_sector_base = lastblock - COMMAND_AREA_SIZE
                ret = check_magic_str(sg_fd, cmd_sector_base)
                if ret: info("magic string match")
                else:
                    warn("magic string not match")
                    continue
                ret = check_ram_loader_version(sg_fd, cmd_sector_base)
                if ret: info("ramloader version check succeed")
                else:
                    warn("ramloader version check failed")
                    continue
                ret = change_to_dl_mode(sg_fd)
                if ret: info("change device to download mode succeed")
                else:
                    warn("change device to download mode failed")
                    continue
                ret = get_dev_type(sg_fd, cmd_sector_base)
                if ret: info("get dev type succeed")
                else:
                    warn("get dev type failed")
                    continue
                return sg_path
        except IOError as e:
            pass
            #err(str(e))
        return None         # to delete
    return None

def wait_and_get_im_sg_path():
    info("waiting for device to appear")
    while True:
        sg_path = get_im_sg_path()
        if sg_path:
            return sg_path
        time.sleep(0.5)
        print ".",
        sys.stdout.flush()
        


if __name__ == "__main__":
    wait_and_get_im_sg_path()
