#############################################
## define configurable vars here
#############################################

#from const_vars import *
from utils import *

debug = False

deprecated_svn_revision = 16

usb_img_dl_major_version = 1
usb_img_dl_minor_version = 2
usb_img_dl_small_version = deprecated_svn_revision

ram_loader_min_versions = [1, 0, 6]
ram_loader_integrated_versions = [1, 0, 12]
INTERGRATED_RAM_LOADER_NAME = "ram_loader-%d.%d.%d" % tuple(ram_loader_integrated_versions)
ram_loader_need_update = False

assert(cmp_version(ram_loader_integrated_versions, ram_loader_min_versions) >= 0)
