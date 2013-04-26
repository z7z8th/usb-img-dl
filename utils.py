from debug_utils import *


def int32_le_to_str_be(i32):
    if not ( isinstance(i32, int) or isinstance(i32, long)):
        raise TypeError("Need a int32 parameter")
    buf = chr((i32 >> 24) & 0xFF)
    buf += chr((i32 >> 16) & 0xFF)
    buf += chr((i32 >> 8) & 0xFF)
    buf += chr(i32 & 0xFF)
    return buf

def int32_le_to_str_le(i32):
    if not ( isinstance(i32, int) or isinstance(i32, long)):
        raise TypeError("Need a int32 parameter")
    buf = chr(i32 & 0xFF)
    buf += chr((i32 >> 8) & 0xFF)
    buf += chr((i32 >> 16) & 0xFF)
    buf += chr((i32 >> 24) & 0xFF)
    return buf

def str_le_to_int32_le(str_4bytes):
    if not isinstance(str_4bytes, str) or not len(str_4bytes) == 4:
        wtf("Need a str of 4 bytes length")
    i32 = ord(str_4bytes[3])<<24 | ord(str_4bytes[2])<<16 | \
            ord(str_4bytes[1]) << 8 | ord(str_4bytes[0])
    return i32


def str_be_to_int32_le(str_4bytes):
    if not isinstance(str_4bytes, str) or not len(str_4bytes) == 4:
        wtf("Need a str of 4 bytes length")
    i32 = ord(str_4bytes[0])<<24 | ord(str_4bytes[1])<<16 | \
            ord(str_4bytes[2]) << 8 | ord(str_4bytes[3])
    return i32

def cmp_version(v1, v2):
    assert(len(v1) == 3 and len(v2) == 3)
    for x1, x2 in zip(v1, v2):
        # print x1, x2
        if x1 < x2:
            return -1
        elif x1 > x2:
            return 1
        else:
            continue
    return 0


if __name__ == "__main__":
    assert(cmp_version([1,2,3], [1,2,3]) == 0)
    assert(cmp_version([1,2,4], [1,2,3]) == 1)
    assert(cmp_version([1,2,3], [1,2,4]) == -1)
    assert(cmp_version([1,3,3], [1,2,4]) == 1)
    assert(cmp_version([1,1,6], [1,2,4]) == -1)
    assert(cmp_version([2,1,6], [1,2,4]) == 1)
    assert(cmp_version([2,4,6], [1,2,4]) == 1)
    info("Test for cmp_version passed")
