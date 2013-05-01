#!/usr/bin/env python

import time
from progress.bar import Bar

import configs
from const_vars import *
from debug_utils import *
from utils import *

import usb.core
import usb.util
from usb.core import USBError

def usb_setup_get_max_lun(dev):
    dbg("----->> get max lun")
    max_lun = dev.ctrl_transfer(0xA1, 0xFE, 0, 0, 1, 1500)
    assert(1 == len(max_lun))
    dbg("-----<< get max lun done: ", max_lun)


CBW_SIGNATURE = 'USBC'
CBW_TAG       = NULL_CHAR * 4

CBW_FLAG_IN   = '\x80'
CBW_FLAG_OUT  = '\x00'
CBW_LUN       = '\x01'
CBW_CB_LEN    = '\x0A'
CBW_SIZE      = 31

CSW_SIGNATURE = 'USBS'
CSW_SIZE      = 13

def print_inquiry_data(inquiry_buf):
    assert(len(inquiry_buf) >= min(36, INQUIRY_DATA_LEN) )
    periheral_qualifer = (inquiry_buf[0] & 0xE0) >> 5
    periheral_dev_type = inquiry_buf[0] & 0x1F
    rmb = (inquiry_buf[1] & 0x80) >> 7
    version = inquiry_buf[2]
    t10_vendor_ident = inquiry_buf[8:16].tostring()
    product_ident = inquiry_buf[16:32].tostring()
    product_rev_lvl = inquiry_buf[32:36].tostring()
    #vendor_specific = inquiry_buf[36:56]
    
    dbg("len(inquiry_buf)=", len(inquiry_buf))
    dbg("periheral_qualifer=0x%02x" % periheral_qualifer)
    dbg("periheral_dev_type=0x%02x" % periheral_dev_type)
    dbg("removable=0x%02x" % rmb)
    dbg("version=0x%02x" % version)
    dbg("t10_vendor_ident=", t10_vendor_ident)
    dbg("product_ident=", product_ident)
    dbg("product_rev_lvl=", product_rev_lvl)
    #dbg("vendor_specific=", vendor_specific)
    return (periheral_qualifer, periheral_dev_type, t10_vendor_ident, product_ident)

INQUIRY = 0x12
INQUIRY_DATA_LEN = 36
def inquiry_info(eps):
    info("======== inquiry_info")
    cdb = chr(INQUIRY) + NULL_CHAR*3 + chr(INQUIRY_DATA_LEN) + NULL_CHAR
    ret_buf=None

    ret = write_cbw(eps[0], CBW_FLAG_IN, INQUIRY_DATA_LEN, cdb)
    dbg("CBW written!")

    inquiry_buf = eps[1].read(INQUIRY_DATA_LEN)
    dbg("inquiry_buf=", inquiry_buf)
    dbg("inquiry info read!")
    ret_buf = print_inquiry_data(inquiry_buf)

    csw_data = eps[1].read(CSW_SIZE)
    dbg("CSW read:", csw_data)
    assert(csw_data[:4].tostring() == CSW_SIGNATURE)
    dbg("CSW Status=", csw_data[12])
    assert(len(inquiry_buf) >= min(36, INQUIRY_DATA_LEN) )
    return ret_buf


READ_CAPACITY = 0x25
def capacity_info(eps):
    info("======== capacity_info")
    cdb = chr(READ_CAPACITY) + NULL_CHAR * 9  #READ_CAPACITY

    ret = write_cbw(eps[0], CBW_FLAG_IN, 8, cdb)

    read_buf = eps[1].read(8)
    dbg("block info: ", read_buf)
    lastblock = str_be_to_int32_le(read_buf[:4].tostring())
    blocksize = str_be_to_int32_le(read_buf[4:8].tostring())
    disk_cap = (lastblock+1) * blocksize
    dbg("lastblock=", lastblock)
    dbg("blocksize=", blocksize)
    dbg("capacity=%ul, %f GB" % (disk_cap, disk_cap/1024.0/1024.0/1024.0))

    csw_data = eps[1].read(CSW_SIZE)
    dbg("csw: ", csw_data)
    assert(csw_data[:4].tostring() == CSW_SIGNATURE)
    dbg("CSW Status=", csw_data[12])

    return lastblock, blocksize


def write_cbw(ep_out, direction, data_len, cdb, timeout=1500):
    cbw_data_len = int32_le_to_str_le(data_len)

    cbw = CBW_SIGNATURE + CBW_TAG + cbw_data_len + direction + CBW_LUN
    cbw += CBW_CB_LEN + cdb
    cbw += NULL_CHAR * (CBW_SIZE - len(cbw))

    ret = ep_out.write(cbw, timeout)
    assert(ret == len(cbw))
    # dbg("write_cbw: ret=", ret)
    return ret

READ_10 = 0x28
def read_sectors(eps, sector_offset, sector_num, timeout=800):
    rd_size = sector_num * SECTOR_SIZE
    cdb = chr(READ_10) + NULL_CHAR
    cdb += int32_le_to_str_be(sector_offset)
    cdb += NULL_CHAR
    cdb += chr((sector_num>>8) & 0xFF)
    cdb += chr(sector_num & 0xFF)
    cdb += NULL_CHAR

    sector_data = None

    ret = write_cbw(eps[0], CBW_FLAG_IN, 
                rd_size, cdb)

    sector_data = eps[1].read(rd_size, timeout)
    assert(len(sector_data) == rd_size)

    csw_data = eps[1].read(CSW_SIZE, timeout)
    assert(csw_data[:4].tostring() == CSW_SIGNATURE)
    # dbg("CSW Status=", csw_data[12])

    return sector_data

WRITE_10 = 0x2a
def write_sectors(eps, buf, sector_offset, sector_num, timeout=1500):
    # dbg("wr sec: sector_offset=%x, sector_num=%x, timeout=%d" % \
    #         (sector_offset, sector_num, timeout))
    wr_size = sector_num * SECTOR_SIZE
    assert(len(buf) == wr_size)
    cdb = chr(WRITE_10) + NULL_CHAR
    cdb += int32_le_to_str_be(sector_offset)
    cdb += NULL_CHAR
    cdb += chr((sector_num>>8) & 0xFF)
    cdb += chr(sector_num & 0xFF)
    cdb += NULL_CHAR

    ret = None
    ret = write_cbw(eps[0], CBW_FLAG_OUT, 
            wr_size, cdb)

    ret = eps[0].write(buf, timeout)
    # dbg("ep wr size:", ret, "/", wr_size)
    assert(ret == wr_size)

    csw_data = eps[1].read(CSW_SIZE, timeout)
    assert(csw_data[:4].tostring() == CSW_SIGNATURE)
    # dbg("CSW Status=", csw_data[12])
    ret = (csw_data[12] == 0)
    #except OSError as e:
    #    warn(get_cur_func_name()+"(): OSError: ", e)

    # sleep for yaffs2 tragedy, I think it's not need
    # the tragedy should be caused by multi process access
    #time.sleep(0.005)
    return ret


def write_large_buf(eps, large_buf, sector_offset,
        size_per_write = SIZE_PER_WRITE):
    img_total_size = len(large_buf)
    dbg(get_cur_func_name(), "(): img_total_size=", img_total_size)
    dbg(get_cur_func_name(), "(): total sector num=",
            (float(img_total_size)/SECTOR_SIZE))
    progressBar = Bar('Burning',
            max = max(1, len(large_buf)/size_per_write),
            suffix='%(percent)d%%')
    size_written = 0
    while size_written < img_total_size:
        buf_end_offset = min(img_total_size, size_written + size_per_write)
        sector_num_write = (buf_end_offset - size_written + \
                SECTOR_SIZE - 1)/SECTOR_SIZE
        buf = large_buf[size_written : buf_end_offset]
        buf_len = buf_end_offset - size_written
        if buf_len < size_per_write:
            buf += NULL_CHAR * (sector_num_write*SECTOR_SIZE - buf_len)
        write_sectors(eps, buf, sector_offset, sector_num_write)
        size_written += size_per_write
        sector_offset += sector_num_write
        if not configs.debug:
            progressBar.next()
    progressBar.finish()
    dbg("End of " + get_cur_func_name())


def get_port_path(dev):
    return dev._ctx.backend.get_port_path(dev._ctx.dev)


def get_usb_dev_eps(dev):
    info("~~~~~~~~ get_usb_dev_eps: dev=", dev.__dict__)

    # was it found?
    if dev is None:
        raise ValueError('Device not found')

    # set the active configuration. With no arguments, the first
    # configuration will be the active one

    # ram loader can not accept set-config twice, 1 by driver, 1 by pyusb
    # dev.set_configuration()

    # get an endpoint instance
    cfg = dev.get_active_configuration()
    dbg("get_usb_dev_eps: cfg=", cfg)
    interface_number = 0 # cfg[(0,0)].bInterfaceNumber
    # alternate_setting = usb.control.get_interface(dev, interface_number)
    intf = usb.util.find_descriptor(
        cfg, bInterfaceNumber = interface_number,
    #    bAlternateSetting = alternate_setting
    )

    eps_out = usb.util.find_descriptor(
        intf,
        # match the first OUT endpoint
        custom_match = \
        lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_OUT
    )
    assert eps_out is not None
    eps_in = usb.util.find_descriptor(
        intf,
        # match the first OUT endpoint
        custom_match = \
        lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_IN
    )

    assert eps_in is not None
    return [eps_out, eps_in]


def find_im_ldr_usb():
    # dev = usb.core.find(idVendor=0x18D1, idProduct=0x0FFF)
    dev_lst = usb.core.find(find_all=True, idVendor=0x0851, idProduct=0x0002)
    for dev in dev_lst:
        usb_setup_get_max_lun(dev)
        eps = get_usb_dev_eps(dev)
        print "ep addr: 0x%x, 0x%x " % (eps[0].bEndpointAddress, eps[1].bEndpointAddress)
        inquiry_info(eps)
        print(capacity_info(eps))


if __name__ == "__main__":
    configs.debug = True
    import sys

    find_im_ldr_usb()


