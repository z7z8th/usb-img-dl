import time
import threading
from const_vars import *
from usb_misc import *
from usb_dl import *
import type_call_dict
from ldr_update_worker import ldr_update_worker
from usb_generic import get_usb_dev_eps
from usb_probe import verify_im_ldr_usb

class dl_worker(threading.Thread):
    def __init__(self, dlr_opts, dev_opts):
        threading.Thread.__init__(self)
        self.dlr_opts = dlr_opts
        self.dev_opts = dev_opts
        self.dev_opts.reboot_delay = 0 #dlr_opts.reboot_delay
        self.ldr_update_worker = ldr_update_worker(dlr_opts, dev_opts)

    def update_info(self, info):
        self.dev_opts.dev_info.set_info(info)

    def update_status(self, status):
        self.dev_opts.dev_info.set_status(status)
        

    def run(self):
        with self.dev_opts.libusb_lock:
            warn("start working")
            self.check_dev()

        self.update_status("download")
        ############### set dl type to flash ###############
        set_dl_img_type(usbdldev, DOWNLOAD_TYPE_FLASH, FLASH_BASE_ADDR)

        if self.dlr_opts.erase_all:
            self.update_info("Erase whole nand Flash!")
            usb_erase_whole_nand_flash(self.dev_opts)

        for img_id, img_buf in self.dlr_opts.img_buf_dict.items():
            dl_desc = type_call_dict.type_call_dict[img_id]['std_name']
            dl_type = type_call_dict.type_call_dict[img_id]['img_type']
            dl_params = type_call_dict.type_call_dict[img_id]['func_params']
            self.update_info("Downloading "+dl_desc)
            if dl_type == 'dyn_id':
                usb_dl_dyn_id(usbdldev, img_buf, *dl_params)
            elif dl_type == 'raw':
                usb_dl_raw(usbdldev, img_buf, *dl_params)
            elif dl_type == 'yaffs2':
                usb_dl_yaffs2(usbdldev, img_buf, *dl_params)
            else:
                raise Exception("Unknown img type")

        self.update_info("All Done")
        self.update_status("success")

        
    def check_dev(self):
        self.update_status("test")
        usbdldev = get_usb_dev_eps(self.dev_opts.dev)
        if usbdldev is None:
            wtf("Unable to find bootloader.")
        ret = verify_im_ldr_usb(usbdldev)
        if not ret:
            wtf("Unable to verify bootloader.")
        elif ret == "ldr-update":
            info("Updating Ram Loader...")
            self.dev_opts = self.ldr_update_worker.work()
        else:
            self.dev_opts.__dict__.update(usbdldev.__dict__)

