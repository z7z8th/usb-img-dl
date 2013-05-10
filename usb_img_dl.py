#!/usr/bin/env python
import time
import mmap
import os
import sys
import re
from optparse import OptionParser
import threading
import usb.core
import libusbx1
#import signal
import time
import traceback
from progress.spinner import Spinner

import configs
from const_vars import *
from debug_utils import *
import mtd_part_alloc
from bsp_pkg_check import bsp_pkg_check
from usb_generic import get_usb_dev_eps, get_port_path
from usb_probe import verify_im_ldr_usb
from usb_misc import *
from usb_burn import *


########## Gloable Vars ##########
type_call_dict = {}
ldr_processing_set = set()
ldr_processing_set_lock = threading.Lock()
get_usb_dev_eps_lock = threading.Lock()
dl_thread_result_list = []
dl_thread_result_list_lock = threading.Lock()



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
    parser.add_option("-n", "--all-new", action="store_true", dest="all_new",
            help="All ramloader is new")
    parser.add_option("-p", "--burn-pkg", type="string", dest="pkg_path",
            help="Burn a whole package")
    parser.add_option("-t", "--profile", action="store_true", dest="do_profile",
            help="Run profiler for performance tunning")
    return parser.parse_args()




def usb_dl_thread_func(dev, port_id, options, img_buf_dict):
    global get_usb_dev_eps_lock
    info("\n>>>>>>>>>>>>>>> new dl thread\n")
    ################ get ep out/in of usb device ################
    eps = None
    time.sleep(0.5)
    with get_usb_dev_eps_lock:
        eps = get_usb_dev_eps(dev)
        if eps is None:
            wtf("Unable to find bootloader.")
        ret = verify_im_ldr_usb(eps)
        if not ret:
            wtf("Unable to verify bootloader.")

    # usb2_start(eps)

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

    # usb2_end(eps)
    
    info("\nAll operations Completed!\n")



def usb_dl_thread_func_wrapper(dev, port_id, options, img_buf_dict):
    global ldr_processing_set
    global ldr_processing_set_lock
    is_failed = False
    start_time = time.time()
    do_profile = options.do_profile
    port_id_str = "".join("%X." % ord(i) for i in port_id)

    pinfo("New Thread: ", port_id_str)
    if do_profile:
        import cProfile, pstats, io
        pr = cProfile.Profile()
        pr.enable()

    try:
        if do_profile:
            pr.runcall(usb_dl_thread_func, dev, port_id, options, img_buf_dict)

        usb_dl_thread_func(dev, port_id, options, img_buf_dict)
    except Exception as e:
        is_failed = True
        traceback.print_exc()
        # raise e
    finally:
        if do_profile:
            pr.disable()
            pr.print_stats()

        time_used = time.time() - start_time
        with dl_thread_result_list_lock:
            dl_thread_result_list.append((port_id_str, is_failed, time_used))
        warn("\nport_id: %10s %12s. Time used: %3.2d seconds" % \
                ( port_id_str, 
                    "***Failed" if is_failed else "Success",
                    time_used))


def usb_img_dl_main():
    global ldr_processing_set
    global ldr_processing_set_lock
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

    ######### burn package #######
    if options.pkg_path and options.burn_list:
        wtf("Only one of --burn-pkg and --burn could be given!")

    pkg_img_pos_list = []
    pkg_buf = None

    if options.pkg_path:
        if not os.path.exists(options.pkg_path):
            wtf("Package not found in: ", options.pkg_path)
        chk_rslt, pkg_img_pos_dict = bsp_pkg_check(options.pkg_path)
        if not chk_rslt:
            wtf("Failed to verify bsp package: ", options.pkg_path)
        info(pkg_img_pos_dict)
        # open pkg buffer
        pkg_fd = open(options.pkg_path, 'rb')
        pkg_buf = mmap.mmap(pkg_fd.fileno(), 0, access = mmap.ACCESS_READ)
        # gen burn list
        options.burn_list = ''
        for i, pkg_img_pos in pkg_img_pos_dict.items():
            options.burn_list += img_type_dict[i][1]
            pkg_img_pos_list.append(pkg_img_pos)

        info("BSP PKG INFO: ", options.burn_list, pkg_img_pos_list)

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
    if options.burn_list and not options.pkg_path and len(options.burn_list) != len(args):
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

            if options.pkg_path:
                info("Load ", type_call_dict[b]['std_name'], "from package.")
                img_start, img_size = pkg_img_pos_list[i]
                img_end = img_start + img_size
                img_buf = pkg_buf[img_start : img_end]
            else:
                info("Load ", type_call_dict[b]['std_name'], ": ", img_paths[i])
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
    LDR_ROM_idVendor  = 0x18d1
    LDR_ROM_idProduct = 0x0fff

    dl_thread_list = []


    with get_usb_dev_eps_lock:
        dev_list = usb.core.find(find_all = True, 
                        backend = libusbx1.get_backend(),
                        idVendor = LDR_ROM_idVendor,
                        idProduct = LDR_ROM_idProduct)
        if len(dev_list) == 0:
            err("No Device Found!")
        for dev in dev_list:
            # FIXME: host may have more than 16 buses
            port_id = chr(dev.bus) + get_port_path(dev)
            with ldr_processing_set_lock:
                if port_id in ldr_processing_set:
                    dbg("*** already in ldr_processing_set")
                    continue

            dbg("~*" * 20)
            info(dev.__dict__)
            with ldr_processing_set_lock:
                ldr_processing_set.add(port_id)
                info("ldr_processing_set after added: ", ldr_processing_set)

            dl_thread = threading.Thread(target = usb_dl_thread_func_wrapper, 
                                    name = port_id,
                                    args = (dev, port_id, options, img_buf_dict))
            dl_thread_list.append(dl_thread)
            dl_thread.start()
        else:
            #warn("No bootloader device found!")
            pass

    sprogress = Spinner()
    while True:
        with dl_thread_result_list_lock:
            if len(dl_thread_result_list) < len(dl_thread_list):
                sprogress.next()
            else:
                break
        time.sleep(1)
    sprogress.finish()

    for t in dl_thread_list:
        t.join()

    assert(len(dl_thread_list) == len(dl_thread_result_list))

    max_time_used = 0
    failed_list = []
    for r in dl_thread_result_list:
        max_time_used = max(max_time_used, r[2])
        if r[1]:
            failed_list.append(r[0])
    pinfo()
    pinfo("Maximum time used: %3.2d seconds" % max_time_used)
    pinfo("%d Failed, %d Succeed (%d Total)" % \
            (len(failed_list), 
            len(dl_thread_result_list) - len(failed_list),
            len(dl_thread_result_list))
         )
    if len(failed_list) > 0:
        pinfo("Failed List: ", [id for id in failed_list])



if __name__ == "__main__":
    usb_img_dl_main()


