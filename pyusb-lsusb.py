import usb.core
import libusbx1

dev_lst = usb.core.find(find_all=True, backend=libusbx1.get_backend(), idVendor = 0x1f75)

for d in dev_lst:
    print d.__dict__
    d.get_active_configuration()
    print ">>>> ", d._ctx.backend.get_port_number(d._ctx.dev)
    print ">>>> ", d._ctx.backend.get_port_path(d._ctx.dev)
    print

