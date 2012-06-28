#!/usr/bin/env python

from const_vars import *
from debug_util import *
from check_bsp_pkg import *
from usb_probe_dev import wait_and_get_im_sg_path
from optparse import OptionParser
from usb_burn import *
import time
import mmap
import os

type_call_dict = { 
        'b': ("barebox", 'dyn_id'),
        'B': ('boot', 'raw'),
        'r': ('recovery', 'raw'),
        's': ('system', 'yaffs'),
        'm': ('modem-or-ecos', 'raw'),
        'c': ('charging-icon', 'dyn_id'),
        'u': ('user-data', 'yaffs'),
        'M': ('machine-data', 'yaffs'),
        'i': ('IMEI-data', 'dyn_id'),
        'd': ('barebox-data', 'dyn_id'),
        'R': ('RAM-SD-loader', ''),
        }


# Dyn ID 
ID_NULL                         = 99
#enum DYN_ID_Type
ID_BAREBOX                      = 0x0
ID_BAREBOX_ENV                  = 0x1
ID_LDR_APP                      = 0x2
ID_IMEI                         = 0x3
ID_ICON                         = 0x4

type_dyn_id_dict = {
        'b' : ID_BAREBOX,
        'd' : ID_BAREBOX_ENV,
        'R' : ID_LDR_APP,
        'i' : ID_IMEI,
        'c' : ID_ICON,
        }

type_raw_off_len_dict = {
        'm' : (PS_MODEM_OFFSET, PS_MODEM_LENGTH),
        'B' : (BOOTIMG_OFFSET,  BOOTIMG_LENGTH),
        'r' : (RECOVERY_OFFSET, RECOVERY_LENGTH),
        }
type_yaffs_off_len_dict = {
        'M' : (MDATA_OFFSET,  MDATA_LENGTH),
        's' : (SYSTEM_OFFSET, SYSTEM_LENGTH),
        'u' : (UDATA_OFFSET,  UDATA_LENGTH),
        }


#call_func_dict = {

USAGE_MSG_HEADER = "usage: %prog <options> <args> [path/to/img...]\n" \
"available partition/img type list are:\n"

for type in 'bBrsmcuMidR':
    USAGE_MSG_HEADER += "%s : %s\n" % (type, type_call_dict[type][0])

USAGE_MSG_HEADER += "\nif you specify more than one of dump/erase/burn,\n" \
        "dump will go first, then erase, then burn.\n"\
        "burn will always be the last action"

print USAGE_MSG_HEADER


def main():
    parser = OptionParser(USAGE_MSG_HEADER)
    parser.add_option("-b", "--burn", type="string", dest="burn_list", \
            metavar="IMG_PATTERN",
            help="burn img to board: %metavar is a combination of partition/img" \
                 "i.e.: '-b Bsu' means to burn Boot,System,UserData to board")
    parser.add_option("-e", "--erase", type="string", dest="erase_list", \
            metavar="PART_PATTERN", 
            help="erase nand partitions: %metavar is a combination of partition/img" \
                 "i.e.: '-e Bsu' means to erase Boot,System,UserData of board")
    parser.add_option("-d", "--dump", type="string", dest="dump_list", \
            metavar="PART_PATTERN",
            help="dump nand partitions: %metavar is a combination of partition/img" \
                 "i.e.: '-d Bsu' means to dump Boot,System,UserData to file" \
                 "the partition will dump to file with pattern: " \
                 "<PART_TYPE>.img-dumped-<TIME>")
    parser.add_option("-A", "--erase-all", action="store_true", dest="erase_all",
            help="erase the whole nand flash")
    parser.add_option("-i", "--disk-path", type="string", dest="sg_path", 
            help="the path to the flash disk. when use this option, "\
                    "the device should already in download mode")
    parser.add_option("-y", "--yes", action="store_true", dest="yes_to_all",
            help="say yes to all additional confirmation")
    options, args = parser.parse_args()
    img_paths = args
    dbg(options)
    dbg(args)
    type_call_keys = set(type_call_dict.keys())
    burn_list = set(options.burn_list) if options.burn_list  else set()
    erase_list = set(options.erase_list) if options.erase_list else set()
    dump_list = set(options.dump_list) if options.dump_list else set()
    for s in [burn_list, erase_list, dump_list]:
        if len(s) != len(s & type_call_keys):
            wtf("%s contains invalid partition/img types: %s" 
                    % (str(list(s)), str(list(s - type_call_keys))))

    if len(options.burn_list) != len(burn_list):
        wtf("you have specified duplicated value for --burn")
    if options.burn_list and len(options.burn_list) != len(args):
        wtf("you ask to burn %d imgs, but %d path/to/imgs specified." \
              " their count should equal" % (len(options.burn_list), len(args)) )


    for p in img_paths:
        if not os.path.isfile(p):
            wtf(p + " isn't a file")

    dbg(burn_list)
    dbg(erase_list)
    dbg(dump_list)

    if options.sg_path:
        if not os.path.exists(options.sg_path):
            wtf(options.sg_path, "does not exists")
        else:
            sg_path = options.sg_path
    else:
        sg_path = wait_and_get_im_sg_path()

    time.sleep(0.5)

    sg_fd = os.open(sg_path, os.O_SYNC | os.O_RDWR)
    assert(sg_fd > 0)
    for d in dump_list:
        dumped_path = type_call_dict[d][0]+".img-dumped-"+ \
                time.strftime("%Y%m%d_%H%M%S", time.localtime())
        info("dump "+type_call_dict[d][0]+" -> "+dumped_path)

    for e in erase_list:
        info("erase "+type_call_dict[e][0])

    for i,b in enumerate(options.burn_list):
        info("burn "+type_call_dict[b][0]+": "+img_paths[i])
        with open(img_paths[i], 'rb') as img_fd:
            img_buf = mmap.mmap(img_fd.fileno(), 0, mmap.MAP_PRIVATE, mmap.PROT_READ)
            set_dl_img_type(sg_fd, DOWNLOAD_TYPE_FLASH, FLASH_BASE_ADDR)
            time.sleep(0.5)
            if type_call_dict[b][1] == 'dyn_id':
                usb_burn_dyn_id(sg_fd, img_buf, type_dyn_id_dict[b])
            elif type_call_dict[b][1] == 'raw':
                usb_burn_raw(sg_fd, img_buf, 
                        type_raw_off_len_dict[b][0], 
                        type_raw_off_len_dict[b][1])
            elif type_call_dict[b][1] == 'yaffs':
                usb_burn_yaffs2(sg_fd, img_buf,
                        type_yaffs_off_len_dict[b][0],
                        type_yaffs_off_len_dict[b][1])
            else:
                wtf("unknown img type")
            info("\n;-) burn %s succeed!" % type_call_dict[b][1])
            img_buf.close()
    os.close(sg_fd)


if __name__ == "__main__":
    main()
