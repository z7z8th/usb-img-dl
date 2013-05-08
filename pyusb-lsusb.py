#!env python

import usb.core
import libusbx1

dev_lst = usb.core.find(find_all=True, 
        backend=libusbx1.get_backend())#, 
#        idVendor = 0x0851)

for d in dev_lst:
    # print d.__dict__
#    d.get_active_configuration()
    print "bus: ", d.bus
    print "port path:",
    print "".join("%02x " % ord(i) for i in \
                d._ctx.backend.get_port_path(d._ctx.dev)
            )
    print "-" * 40

