#!/usr/bin/env python

import time
import traceback

import configs
from const_vars import *
from debug_utils import *
from utils import *

import libusbx1
import usb.core
import usb.util
from usb.core import USBError

class UsbDlDev:
    def __init__(self, ep_out, ep_in, dev):
        self.ep_out = ep_out
        self.ep_in = ep_in
        self.dev = dev


DEFAULT_TIMEOUT = 4*1000
MAX_TIMEOUT     = 10*1000
RETRY_MAX = 30
RETRY_MAX_CLEAR_HALT = 4

test_stall_done = 0

def usb_setup_get_max_lun(dev):
    return
    dbg("----->> get max lun")
    max_lun = dev.ctrl_transfer(0xA1, 0xFE, 0, 0, 1, DEFAULT_TIMEOUT)
    assert(1 == len(max_lun))
    dbg("-----<< get max lun done: ", max_lun)

def get_port_path(dev):
    return dev._ctx.backend.get_port_path(dev._ctx.dev)

def usb_set_debug(level):
    return libusbx1.get_backend().set_debug(level)

def usb_clear_ep_stall(dev, ep_num):
    #return
    dbg("----->> clear ep stall")
    dev.ctrl_transfer(0x02, 0x01, 0, ep_num, '', DEFAULT_TIMEOUT)
    dbg("-----<< clear ep stall done: 0x%x" % ep_num)

def usb_clear_halt(dev, ep_num):
    ri = 0
    while ri < RETRY_MAX_CLEAR_HALT:
        ret = None
        try:
            dbg("----->> clear halt: 0x%x" % ep_num)
            ret = dev._ctx.backend.clear_halt(dev._ctx.handle, ep_num)
            assert(ret == 0)
            return ret
        except Exception as e:
            traceback.print_exc()
            ri += 1
            warn("*** clear halt fail; will retry: %d/%d. " % (ri, RETRY_MAX_CLEAR_HALT), e)
            time.sleep(1)
            #ret = dev._ctx.backend.clear_halt(dev._ctx.handle, 0)
            #warn("*** cleared ep0 halt")
            assert(ret == 0)
            time.sleep(1)
            continue
        
    raise Exception("Exceed RETRY_MAX(%d) limit. Fatal Error!"  % RETRY_MAX_CLEAR_HALT)


def usb_clear_dev_halt(usbdldev):
    # print "ep_out addr: 0x%x" % usbdldev.ep_out.bEndpointAddress
    # print "ep_in addr: 0x%x" % usbdldev.ep_in.bEndpointAddress
    try:
        # FIXME: need to clear ep0 halt?
        #usb_clear_halt(usbdldev.dev, 0)
        usb_clear_halt(usbdldev.dev, usbdldev.ep_out.bEndpointAddress)
        usb_clear_halt(usbdldev.dev, usbdldev.ep_in.bEndpointAddress)
        return usbdldev
    except:
        warn("clear dev halt fail, reset device")
        # FIXME: reset works fine?
        usbdldev.dev.reset()
        return get_usb_dev_eps(usbdldev.dev)


def usb_test_clear_halt(dev, ep_num):
    for i in range(10):
        dbg("===>> ", i)
        usb_clear_halt(dev, ep_num)
        
def test_clear_stall(dev, ep_num = 0x86):
    for i in range(10):
        dbg("===>> ", i)
        usb_clear_ep_stall(dev, ep_num)


CBW_SIGNATURE = 'USBC'
CBW_TAG       = NULL_CHAR * 4

CBW_FLAG_IN   = '\x80'
CBW_FLAG_OUT  = '\x00'
CBW_LUN       = '\x01'
CBW_CB_LEN    = '\x0A'
CBW_SIZE      = 31

CSW_SIGNATURE = 'USBS'
CSW_SIZE      = 13  # lite to 13

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
def inquiry_info(usbdldev, timeout = DEFAULT_TIMEOUT):
    info("======== inquiry_info")
    cdb = chr(INQUIRY) + NULL_CHAR*3 + chr(INQUIRY_DATA_LEN) + NULL_CHAR
    ret_buf=None

    ri = 0
    while ri < RETRY_MAX:
        ret = None
        try:
            if ri > 0:
                dbg("*** sleep before cbw")
                time.sleep(1)
            ret = write_cbw(usbdldev.ep_out, CBW_FLAG_IN, INQUIRY_DATA_LEN, cdb, timeout)
            dbg("CBW written!")

            if ri > 0:
                dbg("*** sleep before data")
                time.sleep(2)
            inquiry_buf = usbdldev.ep_in.read(INQUIRY_DATA_LEN, timeout)
            dbg("inquiry_buf=", inquiry_buf)
            dbg("inquiry info read!")
            ret_buf = print_inquiry_data(inquiry_buf)

            if ri > 0:
                dbg("*** sleep before csw")
                time.sleep(2)
            csw_data = usbdldev.ep_in.read(CSW_SIZE, timeout)
            dbg("CSW read:", csw_data)
            assert(csw_data[:4].tostring() == CSW_SIGNATURE)
            assert(csw_data[12] == 0)
            #dbg("CSW Status=", csw_data[12])
            assert(len(inquiry_buf) >= min(36, INQUIRY_DATA_LEN) )
        except Exception as e:
            traceback.print_exc()
            ri += 1
            warn("inquiry_info fail; will retry: %d/%d. " % (ri, RETRY_MAX), e)
            time.sleep(1)
            usbdldev = usb_clear_dev_halt(usbdldev)
            continue
        return ret_buf

    raise Exception("Exceed RETRY_MAX(%d) limit. Fatal Error!"  % RETRY_MAX)


READ_CAPACITY = 0x25
def capacity_info(usbdldev, timeout = DEFAULT_TIMEOUT):
    info("======== capacity_info")
    cdb = chr(READ_CAPACITY) + NULL_CHAR * 9  #READ_CAPACITY

    ri = 0
    while ri < RETRY_MAX:
        ret = None
        try:
            if ri > 0:
                dbg("*** sleep before cbw")
                time.sleep(1)
            ret = write_cbw(usbdldev.ep_out, CBW_FLAG_IN, 8, cdb, timeout)

            if ri > 0:
                dbg("*** sleep before data")
                time.sleep(2)
            read_buf = usbdldev.ep_in.read(8, timeout)
            dbg("block info: ", read_buf)
            lastblock = str_be_to_int32_le(read_buf[:4].tostring())
            blocksize = str_be_to_int32_le(read_buf[4:8].tostring())
            disk_cap = (lastblock+1) * blocksize
            dbg("lastblock=", lastblock)
            dbg("blocksize=", blocksize)
            dbg("capacity=%ul, %f GB" % (disk_cap, disk_cap/1024.0/1024.0/1024.0))

            if ri > 0:
                dbg("*** sleep before csw")
                time.sleep(2)
            csw_data = usbdldev.ep_in.read(CSW_SIZE, timeout)
            dbg("csw: ", csw_data)
            assert(csw_data[:4].tostring() == CSW_SIGNATURE)
            assert(csw_data[12] == 0)
            #dbg("CSW Status=", csw_data[12])
        except Exception as e:
            traceback.print_exc()
            ri += 1
            warn("capacity_info fail; will retry: %d/%d. " % (ri, RETRY_MAX), e)
            time.sleep(1)
            usbdldev = usb_clear_dev_halt(usbdldev)
            continue
        return lastblock, blocksize

    raise Exception("Exceed RETRY_MAX(%d) limit. Fatal Error!"  % RETRY_MAX)


def write_cbw(ep_out, direction, data_len, cdb, timeout=DEFAULT_TIMEOUT):
    cbw_data_len = int32_le_to_str_le(data_len)

    cbw = CBW_SIGNATURE + CBW_TAG + cbw_data_len + direction + CBW_LUN
    cbw += CBW_CB_LEN + cdb
    cbw += NULL_CHAR * (CBW_SIZE - len(cbw))

    ret = ep_out.write(cbw, timeout)
    assert(ret == len(cbw))
    # dbg("write_cbw: ret=", ret)
    return ret

READ_10 = 0x28
def read_sectors(usbdldev, sector_offset, sector_num, timeout=DEFAULT_TIMEOUT):
    traceback.print_exc()
    timeout = min(MAX_TIMEOUT, timeout * sector_num)
    rd_size = sector_num * SECTOR_SIZE
    cdb = chr(READ_10) + NULL_CHAR
    cdb += int32_le_to_str_be(sector_offset)
    cdb += NULL_CHAR
    cdb += chr((sector_num>>8) & 0xFF)
    cdb += chr(sector_num & 0xFF)
    cdb += NULL_CHAR

    sector_data = None

    ri = 0
    while ri < RETRY_MAX:
        ret = None
        try:
            if ri > 0:
                dbg("*** sleep before cbw")
                time.sleep(1)
            ret = write_cbw(usbdldev.ep_out, CBW_FLAG_IN, 
                        rd_size, cdb, timeout)
            if ri > 0:
                dbg("*** sleep before data")
                time.sleep(2)
            sector_data = usbdldev.ep_in.read(rd_size, timeout)
            dbg("sector_data: (%d):" % rd_size, sector_data)
            assert(len(sector_data) == rd_size)

            if ri > 0:
                dbg("*** sleep befor csw")
                time.sleep(2)
            csw_data = usbdldev.ep_in.read(CSW_SIZE, timeout)
            dbg("csw_data: ", csw_data)
            assert(csw_data[:4].tostring() == CSW_SIGNATURE)
            assert(csw_data[12] == 0)
            # dbg("CSW Status=", csw_data[12])
        except Exception as e:
            traceback.print_exc()
            ri += 1
            warn("read_sectors fail; will retry: %d/%d. " % (ri, RETRY_MAX), e)
            time.sleep(1)
            usbdldev = usb_clear_dev_halt(usbdldev)
            continue
        return sector_data

    raise Exception("Exceed RETRY_MAX(%d) limit. Fatal Error!"  % RETRY_MAX)

WRITE_10 = 0x2a
def write_sectors(usbdldev, buf, sector_offset, sector_num, timeout=DEFAULT_TIMEOUT):
    timeout = min(MAX_TIMEOUT, timeout * sector_num)
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

    ri = 0
    while ri < RETRY_MAX:
        ret = None
        try:
            if ri > 0:
                dbg("*** sleep before cbw")
                time.sleep(1)
            ret = write_cbw(usbdldev.ep_out, CBW_FLAG_OUT, 
                    wr_size, cdb, timeout)
            
            if ri > 0:
                dbg("*** sleep before data")
                time.sleep(1)
            ret = usbdldev.ep_out.write(buf, timeout)
            # dbg("ep wr size:", ret, "/", wr_size)
            assert(ret == wr_size)

            if ri > 0:
                dbg("*** sleep before csw")
                time.sleep(2)
            csw_data = usbdldev.ep_in.read(CSW_SIZE, timeout)
            dbg("csw_data: ", csw_data)
            assert(csw_data[:4].tostring() == CSW_SIGNATURE)
            assert(csw_data[12] == 0)
            #dbg("CSW Status=", csw_data[12])
            #ret = (csw_data[12] == 0)

            # sleep for yaffs2 tragedy, I think it's not need
            # the tragedy should be caused by multi process access
            #time.sleep(0.005)
        except Exception as e:
            traceback.print_exc()
            ri += 1
            warn("write_sectors fail; will retry: %d/%d. " % (ri, RETRY_MAX), e)
            # usb_clear_ep_stall(usbdldev.dev)
            time.sleep(1)
            usbdldev = usb_clear_dev_halt(usbdldev)
            continue
        return ret

    raise Exception("Exceed RETRY_MAX(%d) limit. Fatal Error!"  % RETRY_MAX)


def write_large_buf(usbdldev, large_buf, sector_offset,
        size_per_write = SIZE_PER_WRITE):
    img_total_size = len(large_buf)
    dbg(get_cur_func_name(), "(): img_total_size=", img_total_size)
    dbg(get_cur_func_name(), "(): total sector num=",
            (float(img_total_size)/SECTOR_SIZE))
    size_written = 0
    while size_written < img_total_size:
        buf_end_offset = min(img_total_size, size_written + size_per_write)
        sector_num_write = (buf_end_offset - size_written + \
                SECTOR_SIZE - 1)/SECTOR_SIZE
        buf = large_buf[size_written : buf_end_offset]
        buf_len = buf_end_offset - size_written
        if buf_len < size_per_write:
            buf += NULL_CHAR * (sector_num_write*SECTOR_SIZE - buf_len)
        write_sectors(usbdldev, buf, sector_offset, sector_num_write)
        size_written += size_per_write
        sector_offset += sector_num_write
    dbg("End of " + get_cur_func_name())


def get_usb_dev_eps(dev):
    info("~~~~~~~~ get_usb_dev_eps: dev=", dev.__dict__)

    # was it found?
    if dev is None:
        raise ValueError('Device not found')

    # usb.util.claim_interface(dev, 0)
    #usb_setup_get_max_lun(dev)

    # set the active configuration. With no arguments, the first
    # configuration will be the active one

    # ram loader can not accept set-config twice, 1 by driver, 1 by pyusb
    #dev.set_configuration()

    # get an endpoint instance
    #cfg = dev._ctx.backend.get_configuration(dev._ctx.dev.devid)
    cfg = dev.get_active_configuration()
    dbg("get_usb_dev_eps: cfg=", cfg)
    interface_number = 0 # cfg[(0,0)].bInterfaceNumber
    # alternate_setting = usb.control.get_interface(dev, interface_number)
    intf = usb.util.find_descriptor(
        cfg, bInterfaceNumber = interface_number,
    #    bAlternateSetting = alternate_setting
    )

    ep_out = usb.util.find_descriptor(
        intf,
        # match the first OUT endpoint
        custom_match = \
        lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_OUT
    )
    assert ep_out is not None
    ep_in = usb.util.find_descriptor(
        intf,
        # match the first OUT endpoint
        custom_match = \
        lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_IN
    )

    assert ep_in is not None
    usbdldev = UsbDlDev(ep_out, ep_in, dev)
    return usbdldev


def find_im_ldr_usb():
    # dev = usb.core.find(idVendor=0x18D1, idProduct=0x0FFF)
    # dev_lst = usb.core.find(find_all=True, idVendor=0x0851, idProduct=0x0002)
    dev_lst = usb.core.find(find_all=True, backend=libusbx1.get_backend(),
                             idVendor=0x18d1, idProduct=0x0fff)
    for dev in dev_lst:
        usbdldev = get_usb_dev_eps(dev)
        print "ep addr: 0x%x, 0x%x " % (usbdldev.ep_out.bEndpointAddress, usbdldev.ep_in.bEndpointAddress)
        warn("port path: ", dev.bus, "".join([ "%d " % ord(d) for d in get_port_path(dev) ]))
        # time.sleep(2)
        ##### test clear stall ######
        #usb_clear_ep_stall(usbdldev.dev)
        #traceback.print_exc()
        #test_clear_stall(usbdldev.dev)
        #return

    
        inquiry_info(usbdldev)
        # time.sleep(2)
        print(capacity_info(usbdldev))
        #usb_clear_ep_stall(dev)
        usb_clear_halt(usbdldev.dev, 0x86)
        
        print "###### test clear halt ######"
        #usb_test_clear_halt(usbdldev.dev, 0x86)
        #usb_test_clear_halt(usbdldev.dev, 0x05)
        usb_clear_dev_halt(usbdldev)

        return usbdldev


if __name__ == "__main__":
    configs.debug = True
    import sys

    usb_set_debug(3)
    find_im_ldr_usb()


