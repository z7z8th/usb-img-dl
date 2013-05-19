from const_vars import *
from debug_utils import *
from usb_generic import *

def set_dl_img_type(usbdldev, dl_img_type, mtd_part_start_addr):
    dbg("Start of "+get_cur_func_name())
    buf = chr(dl_img_type) + NULL_CHAR * (SECTOR_SIZE - 1)
    ret = write_sectors(usbdldev, buf, USB_PROGRAMMER_SET_BOOT_DEVICE, 1)
    if not ret:
        wtf("Fail to set download img type")
    buf = int32_le_to_str_be(mtd_part_start_addr)
    buf += NULL_CHAR * (SECTOR_SIZE - len(buf))
    ret = write_sectors(usbdldev, buf, USB_PROGRAMMER_SET_BOOT_ADDR, 1)
    if not ret:
        wtf("Fail to set download img addr")
    dbg("End of "+get_cur_func_name())


def usb_wr_bb_reg(usbdldev, addr, value):
    dbg("Start of "+get_cur_func_name())
    assert_number(usbdldev)
    assert_number(addr)
    assert_number(value)
    buf = int32_le_to_str_be(addr)
    buf += int32_le_to_str_be(value)
    buf += NULL_CHAR * (SECTOR_SIZE - len(buf))
    #dbg(get_cur_func_name()+"(): len=", len(buf), "buf=", repr(buf))
    ret = write_sectors(usbdldev, buf, USB_PROGRAMMER_WR_BB_REG, 1)
    if not ret:
        time.sleep(0.100)
    dbg("End of "+get_cur_func_name())


def usb_dl_start(usbdldev):
    dbg("Start of "+get_cur_func_name())
    # turn off LCM backlight
    #usb_wr_bb_reg(usbdldev, 0xf8001020, 0x1ff)
    # turn off LED backlight
    usb_wr_bb_reg(usbdldev, 0xf8002184, 0x3)
    usb_wr_bb_reg(usbdldev, 0xf80021A4, 0xff)
    dbg("End of "+get_cur_func_name())


def usb_dl_end(usbdldev):
    # turn on LCM backlight
    usb_wr_bb_reg(usbdldev, 0xf8001020, 0x100)
    # turn on LED backlight
    usb_wr_bb_reg(usbdldev, 0xf8002184, 0x4003)
    usb_wr_bb_reg(usbdldev, 0xf80021A4, 0xc0)


def usb_reset_WDT(usbdldev):
    # the magic number will be cleaned up from a non WDT reset
    usb_wr_bb_reg(usbdldev, 0xf8001310, 0x1234ABCD)
    # WDT reset
    usb_wr_bb_reg(usbdldev, 0xf8000500, 0x87654321)


def usb2_start(usbdldev):
    return
    set_dl_img_type(usbdldev, DOWNLOAD_TYPE_RAM, RAM_BOOT_BASE_ADDR)
    usb_dl_start(usbdldev)


def usb2_end(usbdldev):
    return
    set_dl_img_type(usbdldev, DOWNLOAD_TYPE_RAM, RAM_BOOT_BASE_ADDR)
    usb_dl_end(usbdldev)


def usb2_reset(usbdldev):
    set_dl_img_type(usbdldev, DOWNLOAD_TYPE_RAM, RAM_BOOT_BASE_ADDR)
    usb_reset_WDT()



if __name__ == "__main__":
    #set_dl_img_type("/dev/sg2", 48, 0)
    pass
