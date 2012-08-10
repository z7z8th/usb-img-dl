#!/usr/bin/env python
import time
import mmap
import os
from optparse import OptionParser

import config
import runtime_config
from const_vars import *
from debug_util import *
import mtd_part_alloc
from usb_probe_dev import wait_and_get_im_sg_fd
from usb_misc import *
from usb_burn import *

type_call_dict = {}

def update_type_call_dict():
    global type_call_dict
    type_call_dict = { 
        'b': ("barebox",       'dyn_id', ID_BAREBOX),
        'B': ('boot',          'raw',    (mtd_part_alloc.BOOTIMG_OFFSET,  
                                            mtd_part_alloc.BOOTIMG_LENGTH)),
        'r': ('recovery',      'raw',    (mtd_part_alloc.RECOVERY_OFFSET, 
                                            mtd_part_alloc.RECOVERY_LENGTH)),
        's': ('system',        'yaffs2',  (mtd_part_alloc.SYSTEM_OFFSET, 
                                            mtd_part_alloc.SYSTEM_LENGTH)),
        'm': ('modem-or-ecos', 'raw',    (mtd_part_alloc.PS_MODEM_OFFSET,
                                            mtd_part_alloc.PS_MODEM_LENGTH)),
        'c': ('charging-icon', 'dyn_id', ID_ICON),
        'u': ('userdata',      'yaffs2',  (mtd_part_alloc.UDATA_OFFSET,  
                                            mtd_part_alloc.UDATA_LENGTH)),
        'M': ('machine-data',  'yaffs2',  (mtd_part_alloc.MDATA_OFFSET,  
                                            mtd_part_alloc.MDATA_LENGTH)),
        'i': ('IMEI-data',     'dyn_id', ID_IMEI),
        'd': ('barebox-data',  'dyn_id', ID_BAREBOX_ENV),
        'R': ('RAM-SD-loader', 'dyn_id', ID_LDR_APP),  # this type maybe wrong
        }

update_type_call_dict()


USAGE_MSG_HEADER = "usage: %prog <options> <args> [path/to/img...]\n" \
"available partition/img type list are:\n"
for type in 'bBrsmcuMidR':
    USAGE_MSG_HEADER += "%s : %s\n" % (type, type_call_dict[type][0])
USAGE_MSG_HEADER += "\nif you specify more than one of dump/erase/burn,\n" \
        "dump will go first, then erase, then burn.\n"\
        "burn will always be the last action"


def parse_options():
    parser = OptionParser(USAGE_MSG_HEADER)
    parser.add_option("-1", "--bsp12", action="store_true", dest="bsp12_alloc",
            help="the 1st alloc type, for bsp12")
    parser.add_option("-2", "--bsp13", action="store_true", dest="bsp13_alloc",
            help="the 2nd alloc type, for bsp13")
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
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
            help="output verbose information for debug")
    return parser.parse_args()


def main():
    options, args = parse_options()
    img_paths = args
    dbg("options: ", options)
    dbg("args: ", args)

    config.debug = True if options.verbose else False

    if options.bsp12_alloc and options.bsp13_alloc:
        wtf("only one type of alloc can be specified")
    if options.bsp12_alloc:
        mtd_part_alloc.use_bsp12_allocation()
    elif options.bsp13_alloc:
        mtd_part_alloc.use_bsp13_allocation()
    else:
        warn("use default alloc: bsp13")
        mtd_part_alloc.use_bsp13_allocation()
    #print_allocation()

    type_call_keys = set(type_call_dict.keys())
    burn_list  = set(options.burn_list)  if options.burn_list  else set()
    erase_list = set(options.erase_list) if options.erase_list else set()
    dump_list  = set(options.dump_list)  if options.dump_list  else set()
    for s in [burn_list, erase_list, dump_list]:
        if len(s) != len(s & type_call_keys):
            wtf("%s contains invalid partition/img types: %s" 
                    % (str(list(s)), str(list(s - type_call_keys))))

    if options.burn_list and len(options.burn_list) != len(burn_list):
        wtf("you have specified duplicated value for --burn")
    if options.burn_list and len(options.burn_list) != len(args):
        wtf("you ask to burn %d imgs, but %d path/to/imgs specified." \
              " their count should equal" % (len(options.burn_list), len(args)) )


    for p in img_paths:
        if not os.path.isfile(p):
            wtf(p + " isn't a file")

    dbg("burn_list: ", list(burn_list))
    dbg("erase_list: ", list(erase_list))
    dbg("dump_list: ", list(dump_list))

    sg_fd = -1
    if options.sg_path:
        if not os.path.exists(options.sg_path):
            wtf(options.sg_path, "does not exists")
        else:
            sg_path = options.sg_path
            sg_fd = os.open(sg_path, os.O_SYNC | os.O_RDWR)
    else:
        sg_fd = wait_and_get_im_sg_fd()

    time.sleep(0.5)

    if sg_fd < 0:
        wtf("unable to open device.")
    usb2_start(sg_fd)
    for d in dump_list:
        dumped_path = type_call_dict[d][0]+".img-dumped-"+ \
                time.strftime("%Y%m%d_%H%M%S", time.localtime())
        info("dump "+type_call_dict[d][0]+" -> "+dumped_path)

    for e in erase_list:
        erase_desc = type_call_dict[e][0]
        erase_type = type_call_dict[e][1]
        info("erase " + erase_desc)
        if erase_type == 'dyn_id':
            usb_erase_dyn_id(sg_fd, type_call_dict[e][2])
        elif type_call_dict[e][1] == 'raw':
            erase_offset, erase_length = type_call_dict[e][2]
            usb_erase_raw(sg_fd, erase_offset, erase_length)
        elif type_call_dict[e][1] == 'yaffs2':
            erase_offset, erase_length = type_call_dict[e][2]
            usb_erase_yaffs2(sg_fd, erase_offset, erase_length)
        else:
            wtf("unknown img type")
        info("\n;-) erase %s succeed!" % erase_desc)


    if options.burn_list:
        for i,b in enumerate(options.burn_list):
            info("burn "+type_call_dict[b][0]+": "+img_paths[i])
            if not os.path.basename(img_paths[i]).startswith(type_call_dict[b][0]):
                wtf("img file pattern not match, you maybe burning the wrong img")
            with open(img_paths[i], 'rb') as img_fd:
                img_buf = mmap.mmap(img_fd.fileno(), 0, mmap.MAP_PRIVATE, mmap.PROT_READ)
                set_dl_img_type(sg_fd, DOWNLOAD_TYPE_FLASH, FLASH_BASE_ADDR)
                time.sleep(0.5)
                burn_desc = type_call_dict[b][0]
                burn_type = type_call_dict[b][1]
                if burn_type == 'dyn_id':
                    usb_burn_dyn_id(sg_fd, img_buf, type_call_dict[b][2])
                elif burn_type == 'raw':
                    burn_offset, burn_lenght = type_call_dict[b][2]
                    usb_burn_raw(sg_fd, img_buf, burn_offset, burn_lenght)
                elif type_call_dict[b][1] == 'yaffs2':
                    burn_offset, burn_lenght = type_call_dict[b][2]
                    usb_burn_yaffs2(sg_fd, img_buf, burn_offset, burn_lenght)
                else:
                    wtf("unknown img type")
                info("\n;-) burn %s succeed!" % burn_desc)
                img_buf.close()

    usb2_end(sg_fd)
    os.close(sg_fd)


if __name__ == "__main__":
    main()
