import time

import usb.core
import libusbx1
from const_vars import *
from usb_misc import *
from usb_dl import *

class ldr_update_worker(object):
    def __init__(self, dlr_opts, dev_opts):
        self.dlr_opts = dlr_opts
        self.dev_opts = dev_opts

    def work(self):
        set_dl_img_type(eps, DOWNLOAD_TYPE_RAM, RAM_BOOT_BASE_ADDR)
        usb_dl_ram_loader(eps, img_buf_dict[IMG_LDR_APP])
        time.sleep(1)

        LDR_RAM_idVendor  = 0x18D1
        LDR_RAM_idProduct = 0x0FFF
        raw_dev_match_dict = {
            'idVendor'  : LDR_RAM_idVendor,
            'idProduct' : LDR_RAM_idProduct,
            'bus'       : dev.bus,
            'port_path' : get_port_path(dev)
        }
        dev = None
        WAIT_ATTACH_RETRY = 30
        for i in range(WAIT_ATTACH_RETRY):
            time.sleep(0.5)
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
        with self.dlr_opts.get_dev_eps_lock:
            usbdldev = get_usb_dev_eps(dev[0])
            ret = verify_im_ldr_usb(usbdldev)
            if not ret or ret == "ldr-update":
                raise Exception("Update Ramloader failed!")
            self.dev_opts.usbdldev = usbdldev
            return self.dev_opts
        
        
