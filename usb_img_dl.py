#!/usr/bin/env python
import time
import mmap
import os
import sys
import re
from optparse import OptionParser
import thread
import usb.core
import libusbx1
#import signal
import time

import configs
import configs
from const_vars import *
from debug_utils import *
import mtd_part_alloc
from usb_generic import get_usb_dev_eps, get_port_path
from usb_probe import verify_im_ldr_usb
from usb_misc import *
from usb_burn import *



type_call_dict = {}

def update_type_call_dict():
    global type_call_dict
    type_call_dict = {
        'b': {'std_name':"barebox",   'name_pattern':r'barebox',
                'img_type':'dyn_id', 'func_params':ID_BAREBOX},

        'B': {'std_name':'boot',          'name_pattern':r'boot',
                'img_type':'raw',    'func_params':(mtd_part_alloc.BOOTIMG_OFFSET,
                                            mtd_part_alloc.BOOTIMG_LENGTH)},

        'r': {'std_name':'recovery',      'name_pattern':r'recovery',
                'img_type':'raw',    'func_params':(mtd_part_alloc.RECOVERY_OFFSET,
                                            mtd_part_alloc.RECOVERY_LENGTH)},

        's': {'std_name':'system',        'name_pattern':r'system',
                'img_type':'yaffs2',  'func_params':(mtd_part_alloc.SYSTEM_OFFSET,
                                            mtd_part_alloc.SYSTEM_LENGTH)},

        'm': {'std_name':'modem-ecos-ps', 'name_pattern':r'modem|ecos',
                'img_type':'raw',    'func_params':(mtd_part_alloc.PS_MODEM_OFFSET,
                                            mtd_part_alloc.PS_MODEM_LENGTH)},

        'c': {'std_name':'charging-icon', 'name_pattern':r'lcm|icon',
                'img_type':'dyn_id', 'func_params':ID_ICON},

        'u': {'std_name':'userdata',      'name_pattern':r'udata|userdata',
                'img_type':'yaffs2',  'func_params':(mtd_part_alloc.UDATA_OFFSET,
                                            mtd_part_alloc.UDATA_LENGTH)},

        'C': {'std_name':'cache',         'name_pattern':r'cache',
                'img_type':'raw',  'func_params':(mtd_part_alloc.CACHE_OFFSET,
                                            mtd_part_alloc.CACHE_LENGTH)},

        'M': {'std_name':'machine-data',  'name_pattern':r'mdata|macine-data',
                'img_type':'yaffs2',  'func_params':(mtd_part_alloc.MDATA_OFFSET,
                                            mtd_part_alloc.MDATA_LENGTH)},

        'i': {'std_name':'IMEI-data',     'name_pattern':r'imei',
                'img_type':'dyn_id', 'func_params':ID_IMEI},

        'd': {'std_name':'barebox-data',  'name_pattern':r'barebox-data',
                'img_type':'dyn_id', 'func_params':ID_BAREBOX_ENV},

        'R': {'std_name':'ram-loader', 'name_pattern':r'ram_ldr|ldr_app|ram_loader',
                'img_type':'dyn_id', 'func_params':ID_LDR_APP},
        }

####### update call dict for msg header, need to be call again later for mtd alloc ######
update_type_call_dict()

USAGE_MSG_HEADER = "Usage: %prog <options> <args> [path/to/img...]\n" \
"Available partition/img type list are:\n"
for type in 'bBrsmcuMidR':
    USAGE_MSG_HEADER += "%s : %s\n" % (type, type_call_dict[type]['std_name'])
USAGE_MSG_HEADER += "\nIf you specify more than one of dump/erase/burn,\n" \
        "dump will go first, then erase, then burn.\n"\
        "Burn will always be the last action"


def parse_options():
    parser = OptionParser(USAGE_MSG_HEADER)
    parser.add_option("-1", "--bsp12", action="store_true", dest="bsp12_alloc",
            help="The 1st alloc type, for bsp12")
    parser.add_option("-2", "--bsp13", action="store_true", dest="bsp13_alloc",
            help="The 2nd alloc type, for bsp13")
    parser.add_option("-b", "--burn", type="string", dest="burn_list", \
            metavar="IMG_PATTERN",
            help="Burn img to board: %metavar is a combination of partition/img" \
                 "i.e.: '-b Bsu' means to burn Boot,System,UserData to board")
    parser.add_option("-e", "--erase", type="string", dest="erase_list", \
            metavar="PART_PATTERN",
            help="Erase nand partitions: %metavar is a combination of partition/img" \
                 "i.e.: '-e Bsu' means to erase Boot,System,UserData of board")
    parser.add_option("-d", "--dump", type="string", dest="dump_list", \
            metavar="PART_PATTERN",
            help="<Not implemented yet!> Dump nand partitions: %metavar is a combination of partition/img" \
                 "i.e.: '-d Bsu' means to dump Boot,System,UserData to file" \
                 "the partition will dump to file with pattern: " \
                 "<PART_TYPE>.img-dumped-<TIME>")
    parser.add_option("-A", "--erase-all", action="store_true", dest="erase_all",
            help="Erase the whole nand flash")
    parser.add_option("-i", "--disk-path", type="string", dest="sg_path",
            help="The path to the flash disk, i.e. /dev/sg4 . When use this option, "\
                    "the device must already in download mode")
    parser.add_option("-y", "--yes", action="store_true", dest="yes_to_all",
            help="Say yes to all additional confirmation. <Currently not used!>")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
            help="Output verbose information for debug")
    return parser.parse_args()




def usb_dl_thread_func(dev, options, img_buf_dict):
    info("\n>>>>>>>>>>>>>>> new dl thread\n")
    ################ get ep out/in of usb device ################
    eps = None
    eps = get_usb_dev_eps(dev)
    if eps is None:
        wtf("Unable to find bootloader.")
    ret = verify_im_ldr_usb(eps)
    if not ret:
        wtf("Unable to verify bootloader.")

    LDR_RAM_idVendor  = 0x18D1
    LDR_RAM_idProduct = 0x0FFF
    raw_dev_match_dict = {
            'idVendor'  : LDR_RAM_idVendor, 
            'idProduct' : LDR_RAM_idProduct,
            'bus'       : dev.bus,
            'port_path' : get_port_path(dev)
        }

    ################# burn ram loader ################
    if ret == "ldr-update" or \
            (options.burn_list and 'R' in options.burn_list):
        info("Updating Ram Loader...")
        if 'R' in options.burn_list:
            ldr_desc = type_call_dict['R']['std_name']
            set_dl_img_type(eps, DOWNLOAD_TYPE_RAM, RAM_BOOT_BASE_ADDR)
            usb_burn_ram_loader(eps, img_buf_dict[ldr_desc])
        else:
            usb_burn_ram_loader_file_to_ram(eps, configs.ram_loader_path)
        # configs.ram_loader_need_update = False
        dev = None
        while None == dev or len(dev) < 1:
            time.sleep(0.2)
            dev = usb.core.find( find_all = True, 
                    backend = libusbx1.get_backend(),
                    custom_match = lambda d:   \
                        ( d.idVendor == raw_dev_match_dict['idVendor'] and \
                            d.idProduct == raw_dev_match_dict['idProduct'] and \
                            d.bus == raw_dev_match_dict['bus'] and \
                            get_port_path(d) == raw_dev_match_dict['port_path'] )
                    )

        dbg("@^" * 30)
        assert(len(dev) == 1)
        dev = dev[0]
        dbg(dev.__dict__)
        eps = None
        eps = get_usb_dev_eps(dev)
        if eps is None:
            wtf("Unable to find bootloader.")
        ret = verify_im_ldr_usb(eps)
        if not ret:
            wtf("Unable to verify bootloader.")

#FIXME: need sleep?
#    time.sleep(0.5)


    usb2_start(eps)

    ############### set dl type to flash ###############
    set_dl_img_type(eps, DOWNLOAD_TYPE_FLASH, FLASH_BASE_ADDR)

    ################# dump ################
    for d in options.dump_list:
        dumped_path = type_call_dict[d]['std_name']+".img-dumped-"+ \
                time.strftime("%Y%m%d_%H%M%S", time.localtime())
        info('='*80)
        info("dump "+type_call_dict[d]['std_name']+" -> "+dumped_path)

    ################ erase ################
    assert(not (options.erase_all and len(options.erase_list)>0))
    if options.erase_all:
        info("Erase whole nand Flash!")
        usb_erase_whole_nand_flash(eps)
    else:
        for e in options.erase_list:
            erase_desc = type_call_dict[e]['std_name']
            erase_type = type_call_dict[e]['img_type']
            info('='*80)
            info("Erase " + erase_desc)
            if erase_type == 'dyn_id':
                usb_erase_dyn_id(eps, type_call_dict[e]['func_params'])
            elif type_call_dict[e]['img_type'] == 'raw':
                erase_offset, erase_length = type_call_dict[e]['func_params']
                usb_erase_generic(eps, erase_offset, erase_length, is_yaffs2=False)
            elif type_call_dict[e]['img_type'] == 'yaffs2':
                erase_offset, erase_length = type_call_dict[e]['func_params']
                usb_erase_generic(eps, erase_offset, erase_length, is_yaffs2=True)
            else:
                wtf("Unknown img type")
            info("\n;-) Erase %s succeed!" % erase_desc)

    ################ burn ################
    if options.burn_list:
        for i,b in enumerate(options.burn_list):
            # set_dl_img_type(eps, DOWNLOAD_TYPE_FLASH, FLASH_BASE_ADDR)
            time.sleep(0.5)

            burn_desc = type_call_dict[b]['std_name']
            burn_type = type_call_dict[b]['img_type']
            if burn_type == 'dyn_id':
                usb_burn_dyn_id(eps, img_buf_dict[burn_desc], 
                        type_call_dict[b]['func_params'])
            elif burn_type == 'raw':
                burn_offset, burn_lenght = type_call_dict[b]['func_params']
                usb_burn_raw(eps, img_buf_dict[burn_desc], 
                        burn_offset, burn_lenght)
            elif burn_type == 'yaffs2':
                burn_offset, burn_lenght = type_call_dict[b]['func_params']
                usb_burn_yaffs2(eps, img_buf_dict[burn_desc], 
                        burn_offset, burn_lenght)
            else:
                wtf("Unknown img type")

            info("\n;-) Burn %s succeed!\n" % burn_desc)

    usb2_end(eps)
    
    warn("\nAll operations Completed!\n")


########## Gloable Vars ##########
ldr_processing_set = set()
ldr_processing_set_lock = thread.allocate_lock()
# ldr_processing_set_lock.acquire()


def usb_dl_thread_func_wrapper(dev, options, img_buf_dict):
    port_id = None
    port_id = chr(dev.bus) + get_port_path(dev)
    try:
        usb_dl_thread_func(dev, options, img_buf_dict)
    finally:
        warn("Thread finished!")

    warn("*** Remove from running set!")
    with ldr_processing_set_lock:
        ldr_processing_set.remove(port_id)




def usb_img_dl_main():
    options, args = parse_options()
    img_paths = args
    dbg("Options: ", options)
    dbg("Args: ", args)

    configs.debug = True if options.verbose else False

    dbg("sys.argv:", sys.argv)
    dbg("ram_loader path:", configs.ram_loader_path)

    ################ update mtd partition allocation ################
    if options.bsp12_alloc and options.bsp13_alloc:
        wtf("Only one type of alloc can be specified")
    if options.bsp12_alloc:
        info("Use BSP12 Allocation")
        mtd_part_alloc.use_bsp12_allocation()
    elif options.bsp13_alloc:
        info("Use BSP13 Allocation")
        mtd_part_alloc.use_bsp13_allocation()
    else:
        wtf("Allocation must be specified: -1 for BSP12, -2 for BSP13")
    #mtd_part_alloc.print_allocation()

    ####### update call dict ######
    update_type_call_dict()

    ################ check dump/erase/burn types ################
    options.burn_list = [] if options.burn_list is None else options.burn_list
    options.erase_list = [] if options.erase_list is None else options.erase_list
    options.dump_list = [] if options.dump_list is None else options.dump_list

    type_call_keys = set(type_call_dict.keys())
    burn_list  = set(options.burn_list)
    erase_list = set(options.erase_list)
    dump_list  = set(options.dump_list)
    for s in [burn_list, erase_list, dump_list]:
        if len(s) != len(s & type_call_keys):
            wtf("%s contains invalid partition/img types: %s"
                    % (str(list(s)), str(list(s - type_call_keys))))

    if options.burn_list and len(options.burn_list) != len(burn_list):
        wtf("You have specified duplicated value for --burn")
    if options.burn_list and len(options.burn_list) != len(args):
        wtf("You ask to burn %d imgs, but %d path/to/imgs specified." \
              " Their count should equal" % (len(options.burn_list), len(args)) )

    ################ check img file path ################
    for p in img_paths:
        if not os.path.isfile(p):
            wtf(p + " isn't a file")

    dbg("burn_list: ", list(burn_list))
    dbg("erase_list: ", list(erase_list))
    dbg("dump_list: ", list(dump_list))

    img_buf_dict = dict()

    if options.burn_list:
        for i,b in enumerate(options.burn_list):
            info('='*80)
            info("Load "+type_call_dict[b]['std_name']+": "+img_paths[i])

            if not re.search(type_call_dict[b]['name_pattern'],
                    os.path.basename(img_paths[i]).lower()):
                wtf("Image file name pattern not match,",
                        " you maybe burning the wrong img.",
                        " file name pattern should be:",
                        type_call_dict[b]['name_pattern'])

            img_fd = open(img_paths[i], 'rb')
            # Unix version mmap
            #img_buf = mmap.mmap(img_fd.fileno(), 0, mmap.MAP_PRIVATE, mmap.PROT_READ)
            # unix/windows mmap
            img_buf = mmap.mmap(img_fd.fileno(), 0, access = mmap.ACCESS_READ)
            img_buf_dict[ type_call_dict[b]['std_name'] ] = img_buf

    ################ probe device ################
    # ms loader
    # dev_list = usb.core.find(find_all = True, idVendor=0x18D1, idProduct=0x0FFF)
    # raw usb loader
    LDR_ROM_idVendor  = 0x0851
    LDR_ROM_idProduct = 0x0002


    while True:
        dev_list = usb.core.find(find_all = True, 
                        backend = libusbx1.get_backend(),
                        idVendor = LDR_ROM_idVendor,
                        idProduct = LDR_ROM_idProduct)
        for dev in dev_list:
            port_id = chr(dev.bus) + get_port_path(dev)
            with ldr_processing_set_lock:
                if port_id in ldr_processing_set:
                    dbg("*** already in ldr_processing_set")
                    continue

            dbg("~*" * 20)
            info(dev.__dict__)
            with ldr_processing_set_lock:
                ldr_processing_set.add(port_id)
                info("ldr_processing_set: ", ldr_processing_set)
            thread.start_new_thread(usb_dl_thread_func_wrapper, 
                                    (dev, options, img_buf_dict))
        else:
            #warn("No bootloader device found!")
            pass
        time.sleep(0.5)
    while True:
        #signal.pause()
        time.sleep(1<<30)


if __name__ == "__main__":
    usb_img_dl_main()
