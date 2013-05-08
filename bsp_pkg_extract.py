import os
import io
import sys
from debug_utils import *
from const_vars import *


def copy_img_from_pkg(pkg_fd, img_fd, img_size):
    size_per_copy = 1<<15  # 512kB
    size_copyed = 0
    img_size_org = img_size
    while img_size > 0:
        if img_size < size_per_copy:
            size_per_copy = img_size
        buf = pkg_fd.read(size_per_copy)
        img_fd.write(buf)
        size_copyed += len(buf)
        img_size -= size_per_copy
    info("%d of %d bytes writed" % (size_copyed, img_size_org))
    img_fd.flush()
    os.fsync(img_fd)

def bsp_pkg_extract(pkg_path, dest_dir):
    if not os.path.exists(pkg_path):
        warn(pkg_path + " does not exists")
        return False
    if os.path.exists(dest_dir) and not os.path.isdir(dest_dir):
        wtf(dest_dir + " exists and is not a dir!")
    if not os.path.exists(dest_dir):
        os.mkdir(dest_dir)

    ret = False
    pkg_fd = open(pkg_path, 'rb')
    if pkg_fd:
        info("Open bsp package succeed: %s" % pkg_path)
    else:
        wtf("Open bsp package failed: %s" % pkg_path)
    position = 0
    pkg_fd.seek(position, os.SEEK_SET)
    magic_name = pkg_fd.read(16)
    info("magic_name='%s'" % magic_name)
    while magic_name == PACKAGE_HEADER_MAGIC_PATTERN:
        img_size  = 0
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
            pkg_fd.seek(position, os.SEEK_SET)

            img_size = int(partition_size, 16)
            info("partition_size='%s'=%d" % (partition_size, img_size))
            img_type = int(content,16)
            info("img_type=%X='%s'" % ( img_type, img_type_dict[img_type]))
            # copy the img from bsp pkg to file
            img_file_name = img_type_dict[img_type][0][4:].lower() + ".img"
            img_file_path = os.path.join(dest_dir, img_file_name)
            info("Output img to: " + img_file_path)
            if os.path.exists(img_file_path):
                warn("Overwrite img: " + img_file_path)
            img_fd = open(img_file_path, 'wb')
            copy_img_from_pkg(pkg_fd, img_fd, img_size)
            img_fd.close()

            img_size_align = img_size + SECTOR_SIZE - img_size % SECTOR_SIZE
            position += img_size_align
        elif platform_name == PACKAGE_TAIL_PLATFORM:
            ret = True
            break
        pkg_fd.seek(position, os.SEEK_SET)
        magic_name = pkg_fd.read(16)
        info("\nmagic_name='%s'" % magic_name)

    if magic_name == PACKAGE_TAIL_MAGIC_PATTERN:
        ret = True
    pkg_fd.close()
    return ret


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3 or \
            not os.path.exists(sys.argv[1]) or \
            not os.path.exists(sys.argv[2]):
        wtf("Usage: %s /path/to/bsp-package /dir/to/extract" % sys.argv[0])
    bsp_pkg_extract(sys.argv[1], sys.argv[2])
