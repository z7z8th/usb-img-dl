from config import *
from debug_util import *

def update_allocation():
    PS_MODEM_OFFSET = IM9828_MISC_OFFSET + IM9828_MISC_LENGTH
    MDATA_OFFSET    = PS_MODEM_OFFSET + PS_MODEM_LENGTH
    BOOTIMG_OFFSET  = MDATA_OFFSET + MDATA_LENGTH
    RECOVERY_OFFSET = BOOTIMG_OFFSET + BOOTIMG_LENGTH
    SYSTEM_OFFSET   = RECOVERY_OFFSET + RECOVERY_LENGTH
    UDATA_OFFSET    = SYSTEM_OFFSET + SYSTEM_LENGTH
    CACHE_OFFSET    = UDATA_OFFSET + UDATA_LENGTH
    CACHE_LENGTH    = IM9828_NAND_LENGTH - CACHE_OFFSET


def print_allocation():
    for k in ALLOCATION_LIST:
        info("%s\t\t\t0x%.8X" % (k[0], k[1]))


if __name__ == "__main__":
    update_allocation()
    print_allocation()
