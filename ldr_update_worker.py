import time

import usb.core
import libusbx1
from const_vars import *
from usb_misc import *
from usb_dl import *
from usb_generic import get_usb_dev_eps
from usb_probe import verify_im_ldr_usb
import configs

class ldr_update_worker(object):
    def __init__(self, dlr_opts, dev_opts):
        self.dlr_opts = dlr_opts
        self.dev_opts = dev_opts

        
    def update_info(self, info):
        self.dev_opts.dev_info.set_info(info)

    def update_status(self, status):
        self.dev_opts.dev_info.set_status(status)

    def work(self):
        set_dl_img_type(self.dev_opts, DOWNLOAD_TYPE_RAM, RAM_BOOT_BASE_ADDR)
        usb_dl_ram_loader_file_to_ram(self.dev_opts, configs.ram_loader_path)
        time.sleep(1)

        old_dev = self.dev_opts.dev
        LDR_RAM_idVendor  = 0x18D1
        LDR_RAM_idProduct = 0x0FFF
        raw_dev_match_dict = {
            'idVendor'  : LDR_RAM_idVendor,
            'idProduct' : LDR_RAM_idProduct,
            'bus'       : old_dev.bus,
            'port_path' : get_port_path(old_dev)
        }
        dev = None
        WAIT_ATTACH_RETRY = 30
        for i in range(WAIT_ATTACH_RETRY):
            time.sleep(1)
            info("Wait updated device to attach: %d/%d" % (i, WAIT_ATTACH_RETRY))
            dev = usb.core.find( find_all = True,
                                 backend = libusbx1.get_backend(),
                                 custom_match = lambda d:   \
                                 ( d.idVendor == raw_dev_match_dict['idVendor'] and\
                                   d.idProduct == raw_dev_match_dict['idProduct'] \
                                   and \
                                   d.bus == raw_dev_match_dict['bus'] and \
                                   get_port_path(d) == \
                                   raw_dev_match_dict['port_path'] ) )
            if dev and len(dev) == 1:
                break
        else:
            raise Exception("Wait update device to attach failed!")

        assert(len(dev) == 1)

        usbdldev = get_usb_dev_eps(dev[0])
        ret = verify_im_ldr_usb(usbdldev)
        if not ret or ret == "ldr-update":
            raise Exception("Update Ramloader failed!")
        self.dev_opts.__dict__.update(usbdldev.__dict__)
        return self.dev_opts
        
        
