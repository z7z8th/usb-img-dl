import usb.core
import libusbx1

dev_lst = usb.core.find(find_all=True, backend=libusbx1.get_backend())

for d in dev_lst:
    print d.__dict__
    print ">>>> ", libusbx1._lib.libusb_get_port_number(d)
    print

