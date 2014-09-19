#############################################
## define configurable vars here
#############################################

#from const_vars import *
from utils import *
import sys

def find_data_file(filename):
    if getattr(sys, 'frozen', False):
        # The application is frozen
        datadir = os.path.dirname(sys.executable)
    else:
        # The application is not frozen
        # Change this bit to match where you store your data files:
        datadir = os.path.dirname(__file__)

    return os.path.join(datadir, filename)


debug = False

DATA_DIR = "data"

deprecated_svn_revision = 16

usb_img_dl_major_version = 1
usb_img_dl_minor_version = 2
usb_img_dl_small_version = deprecated_svn_revision

ram_loader_min_versions = [1, 0, 6]
ram_loader_integrated_versions = [1, 0, 12]
INTERGRATED_RAM_LOADER_NAME = "ram_loader-%d.%d.%d.img" % tuple(ram_loader_integrated_versions)
ram_loader_need_update = False

ram_loader_path_rel = os.path.join(DATA_DIR, INTERGRATED_RAM_LOADER_NAME)
ram_loader_path = find_data_file(ram_loader_path_rel)


assert(cmp_version(ram_loader_integrated_versions, ram_loader_min_versions) >= 0)
