import copy
import threading
import usb.core
import libusbx1

MAX_DEV_SUPPORTED = 16

class dl_manager(threading.Thread):
    def __init__(self, dlr_opts, dev_opts):
        threading.Thread.__init__(self)
        self.dlr_opts = dlr_opts
        self.dev_opts = dev_opts
        self.libusb_lock = threading.Lock()
        self.running_set_lock = threading.Lock()
        self.running_set = set()

    def run(self):
        LDR_ROM_idVendor  = 0x18d1
        LDR_ROM_idProduct = 0x0fff

        worker_list = {}

        while True:
            with self.libusb_lock:
                dev_list = usb.core.find(find_all = True, 
                                backend = libusbx1.get_backend(),
                                idVendor = LDR_ROM_idVendor,
                                idProduct = LDR_ROM_idProduct)
                if len(dev_list) == 0:
                    err("No Device Found!")
                if len(dev_list) > MAX_DEV_SUPPORTED:
                    dev_list = dev_list[:MAX_DEV_SUPPORTED]
                for dev in dev_list:
                    # FIXME: host may have more than 16 buses
                    port_id = chr(dev.bus) + get_port_path(dev)
                    port_id_str = "".join("%X." % ord(i) for i in port_id)
                    with self.running_set_lock:
                        if port_id in self.running_set:
                            continue
                        self.running_set.add(port_id)
                        info("running_set after added: ", self.running_set)
                        
                    pinfo(dev.__dict__)
                    dev_opts = copy.deepcopy(self.dev_opts)
                    dev_opts.dev = dev
                    dev_opts.dev_info = self.dlr_opts.dev_info_list[x]
                    worker = dl_worker(self.dlr_opts, dev_opts, self.done_callback)

                    worker_list[port_id] = worker
                    worker.start()
            time.sleep(4)



    def done_callback(self, port_id):
        #mark thread as dead
        pass
