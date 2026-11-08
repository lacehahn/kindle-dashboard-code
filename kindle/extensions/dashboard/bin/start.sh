#!/bin/sh
export PATH=/usr/sbin:/sbin:/usr/bin:/bin:$PATH
# 启动时钟看板

DIR=/mnt/us/extensions/dashboard
PIDFILE=/tmp/dashboard.pid
LOG=/mnt/us/dashboard.log
FBINK=/mnt/us/libkh/bin/fbink
[ -x "$FBINK" ] || FBINK=$(command -v fbink)

if [ ! -x "$FBINK" ]; then
    eips 2 2 "ERROR: fbink not found"
    echo "$(date '+%F %T') start failed: fbink not found" >> "$LOG"
    exit 1
fi

# Restore a previous session before switching layouts.
if [ -f /tmp/dashboard-session.pid ] || [ -f "$PIDFILE" ]; then
    sh "$DIR/bin/stop.sh"
fi
MODE=${1:-portrait}
case "$MODE" in portrait|landscape|report|report-portrait) ;; *) exit 1 ;; esac
# Both layouts draw to the proven portrait framebuffer. Landscape is a rotated
# raster, so no physical landscape dimensions or FBInk state dump are required.
if ! lipc-set-prop com.lab126.winmgr orientationLock U 2>> "$LOG"; then
    echo "$(date '+%F %T') could not set portrait canvas" >> "$LOG"
    exit 1
fi
sleep 1

# Session detachment prevents KUAL's exit from owning the dashboard lifecycle.
if command -v setsid >/dev/null 2>&1; then
    setsid sh "$DIR/bin/session.sh" "$MODE" >> "$LOG" 2>&1 < /dev/null &
else
    nohup sh "$DIR/bin/session.sh" "$MODE" >> "$LOG" 2>&1 < /dev/null &
fi
echo $! > /tmp/dashboard-session.pid
echo "$(date '+%F %T') start.sh mode=$MODE session=$!" >> "$LOG"
