import os
import io
import sys
from debug_util import *
from utils import *
from const_vars import *
from usb_generic import read_blocks, write_blocks,write_large_buf, get_dev_block_info
import struct
import ctypes
import time


def set_dl_img_type(sg_fd, dl_img_type, start_addr_hw):
    buf = chr(dl_img_type) + NULL_CHAR * (SECTOR_SIZE - 1)
    dbg( get_cur_func_name() + ": len of buf=%d" % len(buf))
    ret = write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_BOOT_DEVICE, 1)
    if not ret:
        wtf("fail to set download img type")
    buf = int32_to_str(start_addr_hw)
    buf += NULL_CHAR * (SECTOR_SIZE - 4)
    ret = write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_BOOT_ADDR, 1)
    if not ret:
        wtf("fail to set download img addr")


def usb_burn_dyn_id(sg_fd, img_buf, dyn_id):
    dyn_id_init_offset = DYN_ID_INIT_OFFSET
    dyn_id_init_len    = DYN_ID_INIT_LENGTH
    sector_offset = dyn_id_init_offset / SECTOR_SIZE
    platform_id = 0x15

    buf = int32_to_str(dyn_id_init_offset)
    buf += int32_to_str(dyn_id_init_len)
    buf += NULL_CHAR * 2
    buf += chr(0x98)
    buf += chr(platform_id)
    buf += chr(dyn_id+1)
    buf += NULL_CHAR * (SECTOR_SIZE - len(buf))

    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)
    write_blocks(sg_fd, buf, USB_PROGRAMMER_ERASE_NAND_CMD, 1)

    write_large_buf(sg_fd, img_buf, sector_offset)


def usb_burn_raw(sg_fd, img_buf, start_addr_hw, img_len_hw):
    sector_offset = start_addr_hw / SECTOR_SIZE
    buf = int32_to_str(start_addr_hw)
    buf += int32_to_str(img_len_hw)
    buf += NULL_CHAR * (SECTOR_SIZE - len(buf))
    write_blocks(sg_fd, buf, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)
    write_blocks(sg_fd, buf, USB_PROGRAMMER_ERASE_NAND_CMD, 1)
    img_total_size = len(img_buf)
    write_large_buf(sg_fd, img_buf, sector_offset)

def parse_yaffs2_header(header_buf):
    header_size = 0
    yaffs_head_id = str_to_int32_le(header_buf[0:4])
    yaffs_version = str_to_int32_le(header_buf[4:8])
    yaffs_byte_per_chunk = str_to_int32_le(header_buf[8:12])
    yaffs_byte_per_spare = str_to_int32_le(header_buf[12:16])

    info("yaffs_image_header: head_id=%d, version=%d, chunk_size=%d, spare_size=%d" % \
            (yaffs_head_id, yaffs_version, yaffs_byte_per_chunk, yaffs_byte_per_spare))
    header_struct_fmt = 'LLLL'
    yaffs_img_header = struct.pack(header_struct_fmt, yaffs_head_id, \
            yaffs_version, yaffs_byte_per_chunk, yaffs_byte_per_spare)
    if yaffs_head_id == YAFFS_MAGIC_HEAD_ID and yaffs_version == YAFFS_VERSION_4096:
        size_per_page = YAFFS_CHUNKSIZE_4K
        size_per_spare = YAFFS_SPARESIZE_4K
        header_size = struct.calcsize(header_struct_fmt)
    elif  yaffs_head_id == YAFFS_MAGIC_HEAD_ID and yaffs_version == YAFFS_VERSION_2048:
        size_per_page = YAFFS_CHUNKSIZE_2K
        size_per_spare = YAFFS_SPARESIZE_2K
        header_size = struct.calcsize(header_struct_fmt)
    else:
        dbg("yaffs version is none")
        # im9828 v1/v3 uses 2KB size page and 64B size spare
        size_per_page = YAFFS_CHUNKSIZE_2K
        size_per_spare = YAFFS_SPARESIZE_2K

    return (header_size, size_per_page, size_per_spare)


def usb_burn_yaffs2(sg_fd, img_buf, start_addr_hw, img_len_hw):
    ret = False
    dbg(get_cur_func_name()+"(): start_addr_hw=%.8x, img_len_hw=%.8x" % 
            (start_addr_hw, img_len_hw))

    # erase nand partition
    buf = ctypes.create_string_buffer(SECTOR_SIZE)
    buf[0] = '\x01'
    write_blocks(sg_fd, buf.raw, USB_PROGRAMMER_SET_NAND_SPARE_DATA_CTRL, 1)

#    buf[:] = NULL_CHAR * SECTOR_SIZE
    buf[0:4] = int32_to_str(start_addr_hw)
    buf[4:8] = int32_to_str(img_len_hw)
    write_blocks(sg_fd, buf.raw, USB_PROGRAMMER_SET_NAND_PARTITION_INFO, 1)

    info("start to erase yaffs")
    start_addr_erase_hw = start_addr_hw
    img_len_erase_hw = img_len_hw
    while img_len_erase_hw > 0:
        buf[:] = NULL_CHAR * SECTOR_SIZE
        erase_len = min(img_len_erase_hw, NAND_ERASE_MAX_LEN_PER_TIME)
        buf[0:4] = int32_to_str(start_addr_erase_hw)
        buf[4:8] = int32_to_str(erase_len)
        write_blocks(sg_fd, buf.raw, USB_PROGRAMMER_ERASE_NAND_CMD, 1)
        start_addr_erase_hw += erase_len
        img_len_erase_hw    -= erase_len
        print '.',
        sys.stdout.flush()
    #endof erase nand partition
    #exit(0)
    print
    # write yaffs
    info("start to write yaffs")
    sector_offset = start_addr_hw / SECTOR_SIZE
    img_total_size = len(img_buf)
    dbg("img_total_size=", img_total_size)

    size_written, size_per_page, size_per_spare = \
            parse_yaffs2_header(img_buf[:SIZE_YAFFS2_HEADER])
    num_cnt_to_bb_per_time = SIZE_PER_WRITE/ size_per_page
    dbg("size_written=0x%.4x, size_per_page=%.4x, size_per_spare=%.4x" %
            (size_written, size_per_page, size_per_spare))
    dbg( "num_cnt_to_bb_per_time=", num_cnt_to_bb_per_time)
    size_per_group = size_per_page + size_per_spare
    size_page_per_nand_write = size_per_page*num_cnt_to_bb_per_time
    size_spare_per_nand_write = size_per_spare*num_cnt_to_bb_per_time
    size_per_nand_write = size_per_group*num_cnt_to_bb_per_time

    page_buf = ctypes.create_string_buffer(size_page_per_nand_write)
    spare_buf = ctypes.create_string_buffer(size_spare_per_nand_write)
    while size_written < img_total_size:
        page_buf[:] = NULL_CHAR * size_page_per_nand_write
        spare_buf[:] = NULL_CHAR * size_spare_per_nand_write
        size_to_write = min(img_total_size - size_written, size_per_nand_write)
        group_cnt = size_to_write/size_per_group
#        dbg(get_cur_func_name() + \
#                "(): size_written=%.8x, size_to_write=%.8x, group_cnt=%.2x" % \
#                (size_written, size_to_write, group_cnt))

        # create buf
        for i in range(group_cnt):
            img_buf_page_start  = size_written + i*size_per_group
            img_buf_page_end    = img_buf_page_start + size_per_page
            img_buf_spare_start = img_buf_page_end
            img_buf_spare_end   = img_buf_spare_start + size_per_spare
            page_buf_start = i*size_per_page
            spare_buf_start = i*size_per_spare
            page_buf[page_buf_start:page_buf_start+size_per_page] =\
                    img_buf[img_buf_page_start:img_buf_page_end]
            if page_buf[page_buf_start:page_buf_start+size_per_page] !=\
                    img_buf[img_buf_page_start:img_buf_page_end]:
                wtf("why????")
            spare_buf[spare_buf_start:spare_buf_start+size_per_spare] =\
                    img_buf[img_buf_spare_start:img_buf_spare_end]
            if spare_buf[spare_buf_start:spare_buf_start+size_per_spare] !=\
                    img_buf[img_buf_spare_start:img_buf_spare_end]:
                wtf("why????????????")
        # do write to disk
        print ".",
#        dbg("group_cnt=", group_cnt)
        sys.stdout.flush()
#        dbg("write spare_buf")
        write_blocks(sg_fd, spare_buf.raw, USB_PROGRAMMER_WR_NAND_SPARE_DATA,
                size_spare_per_nand_write/SECTOR_SIZE)
        #time.sleep(0.010)
#        dbg("write page_buf")
        write_blocks(sg_fd, page_buf.raw, sector_offset, 
                (group_cnt * size_per_page) / SECTOR_SIZE)
        #time.sleep(0.020)
        size_written += size_to_write
        sector_offset += SECTOR_NUM_PER_WRITE
    print
    dbg("write yaffs to nand finished")
    buf[:] = NULL_CHAR * SECTOR_SIZE
    buf[0] = chr(0x00)
    write_blocks(sg_fd, buf.raw, USB_PROGRAMMER_SET_NAND_SPARE_DATA_CTRL, 1)
        


#def usb_burn(sg_fd, ):
    

if __name__ == "__main__":
    set_dl_img_type("/dev/sg2", 48, 0)
