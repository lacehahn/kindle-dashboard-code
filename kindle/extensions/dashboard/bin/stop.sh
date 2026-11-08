#!/bin/sh
export PATH=/usr/sbin:/sbin:/usr/bin:/bin:$PATH
# 停止时钟看板

PIDFILE=/tmp/dashboard.pid
LOG=/mnt/us/dashboard.log
FBINK=/mnt/us/libkh/bin/fbink
[ -x "$FBINK" ] || FBINK=$(command -v fbink)

if [ -f /tmp/dashboard-session.pid ]; then
    session=$(cat /tmp/dashboard-session.pid)
    kill "$session" 2>/dev/null
    sleep 4
fi
if [ -f "$PIDFILE" ]; then
    pid=$(cat "$PIDFILE")
    kill "$pid" 2>/dev/null
    sleep 1
    kill -KILL "$pid" 2>/dev/null
    rm -f "$PIDFILE"
fi
# Recovery also works if the worker or its supervisor exited unexpectedly.
. /mnt/us/extensions/dashboard/bin/exclusive.sh
. /mnt/us/extensions/dashboard/bin/power.sh
power_restore
ui_resume
lipc-set-prop com.lab126.powerd preventScreenSaver 0 2>/dev/null
lipc-set-prop com.lab126.appmgrd start app://com.lab126.booklet.home 2>/dev/null
rm -f /tmp/dashboard-session.pid /tmp/dashboard-exit
echo "$(date '+%F %T') stopped" >> "$LOG"
