#!/usr/bin/env python
import sys,os,statvfs

f = os.statvfs("/home")
print "preferred block size", "=>", f[statvfs.F_BSIZE]
print "fundamental block size", "=>", f[statvfs.F_FRSIZE]
print "total blocks", "=>", f[statvfs.F_BLOCKS]
print "total free blocks", "=>", f[statvfs.F_BFREE]
print "available blocks", "=>", f[statvfs.F_BAVAIL]
print "total file nodes", "=>", f[statvfs.F_FILES]
print "total free nodes", "=>", f[statvfs.F_FFREE]
print "available nodes", "=>", f[statvfs.F_FAVAIL]
print "max file name length", "=>", f[statvfs.F_NAMEMAX]
print "disk size", "=>", f.f_bsize * f.f_blocks / 1024 /1024/1024
