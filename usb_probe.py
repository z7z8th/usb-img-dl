#!/usr/bin/env python
from __future__ import print_function
import os
import sys
import time
import glob
import binascii

import configs
import configs
from const_vars import *
from debug_utils import *
from utils import *
from usb_generic import inquiry_sg_dev_info, read_blocks, write_blocks, get_dev_block_info

ram_loader_major_version = 0
ram_loader_minor_version = 0
ram_loader_small_version = 0

def check_magic_str(sg_fd, cmd_sector_base):
    #read magic hex, should be 0xdeadbeef
    magic_block = read_blocks(sg_fd, \
            cmd_sector_base + USB_PROGRAMMER_VERIFY_BL_VALIDITY_OFFSET, 1)
    if not magic_block:
        return False
    if configs.debug:
        dbg("MAGIC_WORD:", binascii.b2a_hex(magic_block[:4]))
    if magic_block[:4] != MAGIC_WORD:
        return False
    if BL_MAGIC_STRING not in magic_block:
        return False
    return True

def change_to_dl_mode(sg_fd):
    to_two_byte_char = lambda x: chr(x / 10) + chr(x % 10)
    fill_sector = NULL_CHAR * 9
    fill_sector += to_two_byte_char(configs.usb_img_dl_major_version)
    fill_sector += NULL_CHAR
    fill_sector += to_two_byte_char(configs.usb_img_dl_minor_version)
    fill_sector += NULL_CHAR
    fill_sector += to_two_byte_char(configs.usb_img_dl_small_version)
    fill_sector += NULL_CHAR * (512 - len(fill_sector))
    ret = write_blocks(sg_fd, fill_sector, \
            USB_PROGRAMMER_DOWNLOAD_WRITE_LOADER_EXISTENCE, 1 )
    return ret

def check_ram_loader_version(sg_fd, cmd_sector_base):
    global ram_loader_major_version
    global ram_loader_minor_version
    global ram_loader_small_version
    version_sector = read_blocks( sg_fd, \
            cmd_sector_base + USB_PROGRAMMER_GET_BL_SW_VERSION_OFFSET, 1)
    configs.blOneStageReady = False
    if ord(version_sector[8]) == 1:
        dbg("ROM Type: %s" % version_sector[9:11])
    if ord(version_sector[8]) == 2:
        dbg("Flash Type: %s" % version_sector[9:11])
    if ord(version_sector[8]) == 3:
        ram_loader_major_version = int(version_sector[9:11])
        ram_loader_minor_version = int(version_sector[12:14])
        ram_loader_small_version = int(version_sector[15:17])
        info("RAM Type (Ram Loader Version): %s" % version_sector[9:17])

        ram_loader_versions = [ram_loader_major_version, 
                    ram_loader_minor_version,
                    ram_loader_small_version]
        if cmp_version(ram_loader_versions, 
                configs.ram_loader_min_versions) < 0:
            configs.ram_loader_need_update = True
            warn("Ram Loader is too old, will update!")
        elif cmp_version(ram_loader_versions, 
                configs.ram_loader_integrated_versions) < 0:
            configs.ram_loader_need_update = False
            warn("New version of Ram Loader available, will update!")
        else:
            info("Ram Loader is ok!")


def get_flash_type(sg_fd, cmd_sector_base):
    dev_type_sector = read_blocks(sg_fd, \
            cmd_sector_base + USB_PROGRAMMER_GET_DEV_TYPE_OFFSET, 1)
    if ord(dev_type_sector[8]) == FLASH_DEV_TYPE_IS_NAND:
        ucDevType = FLASH_DEV_TYPE_IS_NAND
        dbg("dev type is nand flash")
    elif ord(dev_type_sector[8]) == FLASH_DEV_TYPE_IS_NOR:
        ucDevType = FLASH_DEV_TYPE_IS_NOR
        dbg("dev type is nor flash")
    else:
        ucDevType = 0x00
        warn("dev type is not recognized")
    return ucDevType



def get_im_sg_fd():
    sg_list = glob.glob('/dev/sg[0-9]*')
    dbg(sg_list)
    sg_fd = -1
    for sg_path in sg_list:
        dbg(sg_path)
        if sg_fd >= 0:
            os.close(sg_fd)
        sg_fd = -1
        try:
            sg_fd = os.open(sg_path, os.O_SYNC | os.O_RDWR)
            if sg_fd < 0:
                dbg("open sg dev failed. sg_fd=", sg_fd)
                continue
            dbg("\nchecking: ", sg_path)

            ( periheral_qualifer, periheral_dev_type, 
                    t10_vendor_ident, product_ident ) = \
                            inquiry_sg_dev_info(sg_fd)
            if periheral_qualifer != 0x00 or \
                    periheral_dev_type != 0x00 or \
                    not t10_vendor_ident.startswith('Infomax') or \
                    not product_ident.startswith('Flash Disk'):
                        dbg("not Infomax Flash Disk, skip")
                        continue
            info("sg dev info match")

            lastblock, block_size = get_dev_block_info(sg_fd)
            if block_size and block_size != SECTOR_SIZE:
                warn("unable to handle block_size=%d, must be %d" \
                        % (block_size, SECTOR_SIZE))
                continue
            if not lastblock:
                #warn("fail to read lastblock of ", sg_fd)
                continue

            cmd_sector_base = lastblock - COMMAND_AREA_SIZE
            ret = check_magic_str(sg_fd, cmd_sector_base)
            if ret: 
                info("magic string match")
            else:
                warn("magic string not match, this is ok to ignore")
                continue

            check_ram_loader_version(sg_fd, cmd_sector_base)

            ret = change_to_dl_mode(sg_fd)
            if ret:
                info("change device to download mode succeed")
            else:
                wtf("change device to download mode failed")

            ret = get_flash_type(sg_fd, cmd_sector_base)
            if ret:
                info("get flash type succeed")
            else:
                warn("get flash type failed, maybe this is a bug")
                continue
            return sg_fd
        except EnvironmentError as e:
            dbg("sg_fd=", sg_fd)
            dbg(e)
            pass
    if sg_fd >= 0:
        os.close(sg_fd)
    return None

def wait_and_get_im_sg_fd():
    info("waiting for device to appear")
    while True:
        sg_fd = get_im_sg_fd()
        if sg_fd:
            print()
            sys.stdout.flush()
            return sg_fd
        time.sleep(0.5)
        print('.', sep='', end='')
        sys.stdout.flush()



if __name__ == "__main__":
    configs.debug = True
    wait_and_get_im_sg_fd()
