import os
from debug_util import *
from const_vars import *


def check_bsp_pkg(pkg_path):
    if not os.path.exists(pkg_path):
        warn(pkg_path + " does not exists")
        return False
    img_pos_in_pkg = dict()
    ret = False
    pkg_fd = open(pkg_path, 'rb')
    if pkg_fd:
        info("open bsp package succeed: %s" % pkg_path)
    else:
        wtf("open bsp package failed: %s" % pkg_path)
    position = 0
    pkg_fd.seek(position, os.SEEK_SET)
    magic_name = pkg_fd.read(16)
    info("magic_name='%s'" % magic_name)
    while magic_name == PACKAGE_HEADER_MAGIC_PATTERN:
        image_size  = 0
        img_type = 0
        position += 16
        pkg_fd.seek(position, os.SEEK_SET)
        platform_name = pkg_fd.read(6)
        position += 16
        if platform_name == PACKAGE_HEADER_PLATFORM:
            info("platform_name=" + platform_name)
            position += 32 + 1 + 4 + 1
            pkg_fd.seek(position, os.SEEK_SET)
            content = pkg_fd.read(1)

            position += 1 + 1
            pkg_fd.seek(position, os.SEEK_SET)
            partition_size = pkg_fd.read(8)

            position += 8
            pkg_fd.seek(position, os.SEEK_SET)
            file_str = pkg_fd.read(128)

            position += 128 + 48
            image_size = int(partition_size, 16)
            info("partition_size='%s'=%d" % (partition_size, image_size))
            img_type = int(content,16)
            info("img_type=%X='%s'" % ( img_type, img_type_dict[img_type]))
            tmp = image_size + SECTOR_SIZE - image_size % SECTOR_SIZE
            if img_type == IMG_SYSTEM or \
                    img_type == IMG_M_DATA or \
                    img_type == IMG_USER_DATA:
                img_pos_in_pkg[img_type] = (position, image_size)
            else:
                img_pos_in_pkg[img_type] = (position, tmp)
            position += tmp
        elif platform_name == PACKAGE_TAIL_PLATFORM:
            ret = True
            break
        pkg_fd.seek(position, os.SEEK_SET)
        magic_name = pkg_fd.read(16)
        info("\nmagic_name='%s'" % magic_name)

    if magic_name == PACKAGE_TAIL_MAGIC_PATTERN:
        ret = True
    pkg_fd.close()
    return ret, img_pos_in_pkg


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2 or \
            not os.path.exists(sys.argv[1]):
        wtf("usage: %s BSP_Package_path" % sys.argv[0])
    ret, img_pos_in_pkg = check_bsp_pkg(sys.argv[1])
    print ret, img_pos_in_pkg
