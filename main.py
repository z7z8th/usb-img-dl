#!/usr/bin/env python

import io
import os
import sys
import glob
import my_sg
from debug_util import *

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

def check_magic_str(disk_path, cmd_sector_base):
    #read magic hex, should be 0xdeadbeef
    magic_block = my_sg.read_blocks(disk_path, \
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

def check_board_sw_version(disk_path, cmd_sector_base):
    global blOneStageReady
    global dl_small_version
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
            return True
        else:
            dl_ram_version_check = False
            wtf("need ramloader small version >= 6")
            return False
    return False


def get_dev_type(disk_path, cmd_sector_base):
    dev_type_sector = my_sg.read_blocks(disk_path, \
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
        cmd_sector_base = lastblock - COMMAND_AREA_SIZE
        if check_magic_str(disk_path, cmd_sector_base):
            info("aha! Device Found! Good Luck!")
            if check_board_sw_version(disk_path, cmd_sector_base):
                info("ramloader version check succeed!")
                if change_to_dl_mode(disk_path):
                    info("change device to download mode succeed!")
                    if get_dev_type(disk_path, cmd_sector_base):
                        return disk_path
        return None
    return None

PACKAGE_HEADER_MAGIC_PATTERN = "(^_^)y :-)(^~~^)"
PACKAGE_HEADER_PLATFORM      = "iM9828"
PACKAGE_TAIL_MAGIC_PATTERN   = "(^~~^)(-: y(^_^)"
PACKAGE_TAIL_PLATFORM        = "im98xx"

IMG_BAREBOX        = 0x1
IMG_LDR_APP        = 0x2
IMG_MODEM          = 0x3
IMG_BOOTIMG        = 0x4
IMG_RECOVERY       = 0x5
IMG_SYSTEM         = 0x6
IMG_M_DATA         = 0x7
IMG_USER_DATA      = 0x8
IMG_IMEI           = 0x9
IMG_BAREBOX_ENV    = 0xA
IMG_ICON           = 0xB
IMG_MAX            = 0xC

img_type_dict = {
#0x0 : "IMG_UNKNOWN",
0x1 : "IMG_BAREBOX",
0x2 : "IMG_LDR_APP",
0x3 : "IMG_MODEM",
0x4 : "IMG_BOOTIMG",
0x5 : "IMG_RECOVERY",
0x6 : "IMG_SYSTEM",
0x7 : "IMG_M_DATA",
0x8 : "IMG_USER_DATA",
0x9 : "IMG_IMEI",
0xA : "IMG_BAREBOX_ENV",
0xB : "IMG_ICON",
0xC : "IMG_MAX"
}
img_pos_in_bsp = dict()

def verify_bsp_pkg(pkg_path):
    if not os.path.exists(pkg_path):
        warn(pkg_path + " does not exists")
        return False
    ret = False
    pkg_fd = open(pkg_path, 'r')
    if pkg_fd:
        info("open bsp package succeed: %s" % pkg_path)
    else:
        wtf("open bsp package failed: %s" % pkg_path)
    position = 0
    pkg_fd.seek(position, os.SEEK_SET)
    magic_name = pkg_fd.read(16)
    info("magic_name='%s'" % magic_name)
    while magic_name == PACKAGE_HEADER_MAGIC_PATTERN:
        image_size  = 0
        img_type = 0
        position += 16
        pkg_fd.seek(position, os.SEEK_SET)
        platform_name = pkg_fd.read(6)
        position += 16
        if platform_name == PACKAGE_HEADER_PLATFORM:
            info("platform_name=" + platform_name)
            position += 32 + 1 + 4 + 1
            pkg_fd.seek(position, os.SEEK_SET)
            content = pkg_fd.read(1)

            position += 1 + 1
            pkg_fd.seek(position, os.SEEK_SET)
            partition_size = pkg_fd.read(8)

            position += 8
            pkg_fd.seek(position, os.SEEK_SET)
            file_str = pkg_fd.read(128)

            position += 128 + 48
            image_size = int(partition_size, 16)
            info("partition_size='%s'=%d" % (partition_size, image_size))
            img_type = int(content,16)
            info("img_type=%X='%s'" % ( img_type, img_type_dict[img_type]))
            tmp = image_size + my_sg.SECTOR_SIZE - image_size % my_sg.SECTOR_SIZE
            if img_type == IMG_SYSTEM or \
                    img_type == IMG_M_DATA or \
                    img_type == IMG_USER_DATA:
                img_pos_in_bsp[img_type] = (position, image_size)
            else:
                img_pos_in_bsp[img_type] = (position, tmp)
            position += tmp
        elif platform_name == PACKAGE_TAIL_PLATFORM:
            ret = True
            break
        pkg_fd.seek(position, os.SEEK_SET)
        magic_name = pkg_fd.read(16)
        info("\nmagic_name='%s'" % magic_name)

    if magic_name == PACKAGE_TAIL_MAGIC_PATTERN:
        ret = True
    return ret

#get_im_disk_path()

ret = verify_bsp_pkg(sys.argv[1])
print "verify_bsp_pkg: ",ret

print img_pos_in_bsp
