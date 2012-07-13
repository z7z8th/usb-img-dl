from const_vars import *
from debug_util import *
from usb_generic import *

def set_dl_img_type(sg_fd, dl_img_type, nand_part_start_addr):
    buf = chr(dl_img_type) + NULL_CHAR * (SECTOR_SIZE - 1)
    dbg( get_cur_func_name() + ": len of buf=%d" % len(buf))
    ret = write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_BOOT_DEVICE, 1)
    if not ret:
        wtf("fail to set download img type")
    buf = int32_to_str(nand_part_start_addr)
    buf += NULL_CHAR * (SECTOR_SIZE - 4)
    ret = write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_BOOT_ADDR, 1)
    if not ret:
        wtf("fail to set download img addr")


def usb_wr_bb_reg(sg_fd, start_addr, length):
    assert_number(sg_fd)
    assert_number(start_addr)
    assert_number(length)
    buf = int32_to_str(start_addr)
    buf += int32_to_str(length)
    buf += NULL_CHAR*(SECTOR_SIZE - len(buf))
    write_blocks(sg_fd, buf, USB_PROGRAMMER_WR_BB_REG, 1)


def usb_dl_start(sg_fd):
    # turn off LCM backlight
    #usb_wr_bb_reg(sg_fd, 0xf8001020, 0x1ff)
    # turn off LED backlight
    usb_wr_bb_reg(sg_fd, 0xf8002184, 0x3)
    usb_wr_bb_reg(sg_fd, 0xf80021A4, 0xff)


def usb_dl_end(sg_fd):
    # turn on LCM backlight
    usb_wr_bb_reg(sg_fd, 0xf8001020, 0x100)
    # turn on LED backlight
    usb_wr_bb_reg(sg_fd, 0xf8002184, 0x4003)
    usb_wr_bb_reg(sg_fd, 0xf80021A4, 0xc0)


def usb_reset_WDT(sg_fd):
    # the magic number will be cleaned up from a non WDT reset
    usb_wr_bb_reg(sg_fd, 0xf8001310, 0x1234ABCD)
    # WDT reset
    usb_wr_bb_reg(sg_fd, 0xf8000500, 0x87654321)


def usb2_start(sg_fd):
    set_dl_img_type(sg_fd, DOWNLOAD_TYPE_RAM, RAM_BOOT_BASE_ADDR)
    usb_dl_start(sg_fd)


def usb2_end(sg_fd):
    set_dl_img_type(sg_fd, DOWNLOAD_TYPE_RAM, RAM_BOOT_BASE_ADDR)
    usb_dl_end(sg_fd)


def usb2_reset(sg_fd):
    set_dl_img_type(sg_fd, DOWNLOAD_TYPE_RAM, RAM_BOOT_BASE_ADDR)
    usb_reset_WDT()



if __name__ == "__main__":
    #set_dl_img_type("/dev/sg2", 48, 0)
    pass
