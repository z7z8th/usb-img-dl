#############################################
## define configurable vars here
#############################################

#from const_vars import *
from utils import *

debug = False

DATA_DIR = "data"

deprecated_svn_revision = 16

usb_img_dl_major_version = 1
usb_img_dl_minor_version = 2
usb_img_dl_small_version = deprecated_svn_revision

ram_loader_min_versions = [1, 0, 6]
ram_loader_integrated_versions = [2, 0, 0]
#INTERGRATED_RAM_LOADER_NAME = "ldr_app-%d.%d.%d.bin" % tuple(ram_loader_integrated_versions)
INTERGRATED_RAM_LOADER_NAME = "ldr_app-usb2.0-retry-rel3.bin"

ram_loader_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), DATA_DIR,
        INTERGRATED_RAM_LOADER_NAME)


assert(cmp_version(ram_loader_integrated_versions, ram_loader_min_versions) >= 0)

USB_ID_ROM = (0x0851, 0x0002)
USB_ID_FASTBOOT = (0x18d1, 0x0fff)

BSP12_NAME = "BSP12"
BSP13_NAME = "BSP13"
