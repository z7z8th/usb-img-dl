#!/usr/bin/env python

from common import *
from check_bsp_pkg import *
from usb_probe_dev import get_im_disk_path


disk_path = get_im_disk_path()
ret = check_bsp_pkg(sys.argv[1])
