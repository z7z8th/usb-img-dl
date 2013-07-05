import time
import threading
from const_vars import *
from usb_misc import *
from usb_dl import *


class dl_worker(object):
    def __init__(self, dlr_opts, dev_opts):
        self.dlr_opts = dlr_opts
        self.dev_opts = dev_opts
        self.ldr_update_worker = ldr_update_worker(dlr_opts, dev_opts)

    def work(self):
        warn("start working")
        self.check_dev()
        

        
    def check_dev(self):
        usbdldev = get_usb_dev_eps(dev)
        if usbdldev is None:
            wtf("Unable to find bootloader.")
        ret = verify_im_ldr_usb(usbdldev)
        if not ret:
            wtf("Unable to verify bootloader.")
        if ret == "ldr-update":
            info("Updating Ram Loader...")
            self.dev_opts = self.ldr_update_worker.work()
            
