import copy
import time
import threading
import usb.core
import libusbx1

from debug_utils import *
from usb_generic import get_port_path
from dl_worker import dl_worker

MAX_DEV_SUPPORTED = 16

class dl_manager(threading.Thread):
    def __init__(self, dlr_opts, dev_opts):
        threading.Thread.__init__(self)
        self.dlr_opts = dlr_opts
        self.win = dlr_opts.win
        self.dev_opts = dev_opts
        self.libusb_lock = threading.Lock()
        self.running_set_lock = threading.Lock()
        self.running_set = set()
        self.port_id_dev_info_dict = {}
        self.worker_dict = {}

    def run(self):
        pinfo("(II) dl_manager started")
        LDR_ROM_idVendor  = 0x18d1 #0x0851 #0x18d1
        LDR_ROM_idProduct = 0x0002 #0x0002 #0x0fff

        
        while True:
            with self.libusb_lock:
                dev_list = usb.core.find(find_all = True, 
                                backend = libusbx1.get_backend(),
                                idVendor = LDR_ROM_idVendor,
                                idProduct = LDR_ROM_idProduct)
                print "(DD) after find"
                if len(dev_list) == 0:
                    err("No Device Found!")
                if len(dev_list) > MAX_DEV_SUPPORTED:
                    dev_list = dev_list[:MAX_DEV_SUPPORTED]
                cur_set = set()

                for dev in dev_list:
                    print dev.__dict__
                    # FIXME: host may have more than 16 buses
                    port_id = chr(dev.bus) + get_port_path(dev)
                    port_id_str = "".join("%X." % ord(i) for i in port_id)
                    cur_set.add(port_id)
                    with self.running_set_lock:
                        if port_id in self.running_set:
                            continue
                        self.running_set.add(port_id)
                        info("running_set after added: ", self.running_set)
                        
                    pinfo(dev.__dict__)
                    
                    dev_opts = copy.deepcopy(self.dev_opts)
                    dev_opts.libusb_lock = self.libusb_lock
                    dev_opts.dev = dev
                    dev_opts.dev_info = self.get_idle_dev_info()
                    if dev_opts.dev_info == None:
                        with self.running_set_lock:
                            self.running_set.remove(port_id)
                        continue
                    dev_opts.dev_info.port_id = port_id
                    self.port_id_dev_info_dict[port_id] = dev_opts.dev_info
                    worker = dl_worker(self.dlr_opts, dev_opts)

                    self.worker_dict[port_id] = worker
                    # self.port_id_dev_dict[port_id] = dev
                    worker.start()

                self.update_running_set(cur_set)
            time.sleep(4)

    def update_dev_info_status(self, port_id_list, status=None,
                               fraction=None, info=None):
        for i in port_id_list:
            if status is not None:
                self.port_id_dev_info_dict[i].set_status(status)
            if fraction is not None:
                self.port_id_dev_info_dict[i].set_fraction(fraction)
            if info is not None:
                self.port_id_dev_info_dict[i].set_info(info)

    def update_running_set(self, cur_set):
        with self.running_set_lock:
            disconn_set = self.running_set - cur_set
            self.join_disconn_worker(disconn_set)
            self.running_set -= disconn_set
            self.update_dev_info_status(disconn_set, "disconnect", 0, "Disconnected")
            for i in disconn_set:
                self.port_id_dev_info_dict[i].port_id = None

    def join_disconn_worker(self, port_id_set):
        for i in port_id_set:
            if self.worker_dict[i].is_alive():
                self.win.alert("Device disconnected, but Thread still alive!")
                self.worker_dict[i].join(5)
            else:
                self.worker_dict[i].join()
            
            
    def get_idle_dev_info(self):
        for i in self.win.dev_info_list[:]:
            if i.port_id == None:
                return i
        else:
            msg = "No Device Infomation Bar available!"
            self.win.alert(msg)
            return None

    def done_callback(self, port_id):
        #mark thread as dead
        pass
