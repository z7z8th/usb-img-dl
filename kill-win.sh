#!/bin/sh

pid=`ps -aux | grep usb_dlr_win | grep -v grep | head -n1 | awk '{print $2}'`

[ x$pid != x ] && {
    echo kill $pid;
    kill -TERM $pid;
}
