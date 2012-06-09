from debug_util import *


def int32_to_str(i32):
    if not isinstance(i32, int):
        wtf("need a int32 parameter")
    buf = chr((i32 >> 24) & 0xFF)
    buf += chr((i32 >> 16) & 0xFF)
    buf += chr((i32 >> 8) & 0xFF)
    buf += chr(i32 & 0xFF)
    return buf

def str_to_int32(str_4bytes):
    if not isinstance(str_4bytes, str) or not len(str_4bytes) == 4:
        wtf("need a str of 4 bytes length")
    i32 = str_4bytes[3]<<24 | str_4bytes[2]<<16 | \
            str_4bytes[1] << 8 | str_4bytes[0]
    return i32

