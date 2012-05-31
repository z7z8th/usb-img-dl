from debug_util import *


def int32_to_str(i32):
    if not isinstance(i32, int):
        wtf("need a int32 parameter")
    buf = chr((i32 >> 24) & 0xFF)
    buf += chr((i32 >> 16) & 0xFF)
    buf += chr((i32 >> 8) & 0xFF)
    buf += chr(i32 & 0xFF)
    return buf

