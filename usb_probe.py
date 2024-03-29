#!/usr/bin/env python
from __future__ import print_function
import os
import sys
import time
import glob
import binascii

import configs
from const_vars import *
from debug_utils import *
from utils import *
from usb_generic import inquiry_info, read_sectors, write_sectors, \
        capacity_info, find_im_ldr_usb


def check_magic_str(usbdldev, cmd_sector_base):
    #read magic hex, should be 0xdeadbeef
    magic_block = read_sectors(usbdldev, \
            cmd_sector_base + USB_PROGRAMMER_VERIFY_BL_VALIDITY_OFFSET, 1)
    if not magic_block:
        return False
    magic_block = magic_block.tostring()
    if configs.debug:
        dbg("MAGIC_WORD:", binascii.b2a_hex(magic_block[:4]))
    if magic_block[:4] != MAGIC_WORD:
        return False
    if BL_MAGIC_STRING not in magic_block:
        return False
    return True

def change_to_dl_mode(usbdldev):
    to_two_byte_char = lambda x: chr(x / 10) + chr(x % 10)
    fill_sector = NULL_CHAR * 9
    fill_sector += to_two_byte_char(configs.usb_img_dl_major_version)
    fill_sector += NULL_CHAR
    fill_sector += to_two_byte_char(configs.usb_img_dl_minor_version)
    fill_sector += NULL_CHAR
    fill_sector += to_two_byte_char(configs.usb_img_dl_small_version)
    fill_sector += NULL_CHAR * (512 - len(fill_sector))
    ret = write_sectors(usbdldev, fill_sector, \
            USB_PROGRAMMER_DOWNLOAD_WRITE_LOADER_EXISTENCE, 1 )
    return ret

def check_ram_loader_version(usbdldev, cmd_sector_base):
    version_sector = read_sectors( usbdldev, \
            cmd_sector_base + USB_PROGRAMMER_GET_BL_SW_VERSION_OFFSET, 1)
    # configs.blOneStageReady = False
    ret = "ldr-ok"
    if version_sector[8] == 1:
        info("ROM Type: %s" % version_sector[9:11])
        wtf("Should not come here!")
    elif version_sector[8] == 2:
        info("Flash Type: %s" % version_sector[9:11])
        ret = "ldr-update"
        warn("Ram Loader not found. Please Update!")
    elif version_sector[8] == 3:
        ram_loader_major_version = int(version_sector[9:11].tostring())
        ram_loader_minor_version = int(version_sector[12:14].tostring())
        ram_loader_small_version = int(version_sector[15:17].tostring())
        info("RAM Type (Ram Loader Version): %s" % version_sector[9:17].tostring())

        ram_loader_versions = [ram_loader_major_version, 
                    ram_loader_minor_version,
                    ram_loader_small_version]
        if cmp_version(ram_loader_versions, 
                configs.ram_loader_min_versions) < 0:
            ret = "ldr-update"
            warn("Ram Loader is too old, Please update!")
        elif cmp_version(ram_loader_versions, 
                configs.ram_loader_integrated_versions) < 0:
            ret = "ldr-update"
            warn("New version of Ram Loader available, will update!")
        else:
            info("Ram Loader is ok!")
    
    return ret


def get_flash_type(usbdldev, cmd_sector_base):
    dev_type_sector = read_sectors(usbdldev, \
            cmd_sector_base + USB_PROGRAMMER_GET_DEV_TYPE_OFFSET, 1)
    if dev_type_sector[8] == FLASH_DEV_TYPE_IS_NAND:
        ucDevType = FLASH_DEV_TYPE_IS_NAND
        dbg("Dev type is nand flash")
    elif dev_type_sector[8] == FLASH_DEV_TYPE_IS_NOR:
        ucDevType = FLASH_DEV_TYPE_IS_NOR
        dbg("Dev type is nor flash")
    else:
        ucDevType = 0x00
        warn("Dev type is not recognized")
    return ucDevType


def verify_im_ldr_usb(usbdldev):
    dbg("\nChecking: ", usbdldev)

    ( periheral_qualifer, periheral_dev_type, 
            t10_vendor_ident, product_ident ) = \
                    inquiry_info(usbdldev)
    if periheral_qualifer != 0x00 or \
            periheral_dev_type != 0x00 or \
            not t10_vendor_ident.startswith('Infomax') or \
            not product_ident.startswith('Flash Disk'):
                dbg("not Infomax Flash Disk, skip")
                return False
    print()
    info("Sg dev info match")

    numofblock, block_size = capacity_info(usbdldev)
    if block_size and block_size != SECTOR_SIZE:
        warn("Unable to handle block_size=%d, must be %d" \
                % (block_size, SECTOR_SIZE))
        return False
    if not numofblock:
        warn("fail to read numofblock of ", usbdldev)
        return False

    cmd_sector_base = numofblock - COMMAND_AREA_SIZE
    ret = check_magic_str(usbdldev, cmd_sector_base)
    if ret: 
        info("Magic string match")
    else:
        warn("Magic string not match, this is ok to ignore")
        return False

    ret = check_ram_loader_version(usbdldev, cmd_sector_base)
    if ret != "ldr-ok":
        return ret

    ret = change_to_dl_mode(usbdldev)
    if ret:
        info("Change device to download mode succeed")
    else:
        wtf("Change device to download mode failed")

    ret = get_flash_type(usbdldev, cmd_sector_base)
    if ret:
        info("Get flash type succeed")
    else:
        warn("Get flash type failed, maybe this is a bug")
        return False
    return True




if __name__ == "__main__":
    configs.debug = True
    usbdldev = find_im_ldr_usb()
    verify_im_ldr_usb(usbdldev)
