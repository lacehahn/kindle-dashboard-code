#!/bin/sh
# Detached session owns the UI pause, worker, power-button events, and cleanup as one lifetime.
export PATH=/usr/sbin:/sbin:/usr/bin:/bin:$PATH
DIR=/mnt/us/extensions/dashboard
LOG=/mnt/us/dashboard.log
. "$DIR/bin/exclusive.sh"
. "$DIR/bin/power.sh"
MODE=${1:-portrait}
case "$MODE" in portrait|landscape|report|report-portrait) ;; *) exit 2 ;; esac
echo $$ > /tmp/dashboard-session.pid
WORKER=
WATCH=
TIMER=
cleanup() {
    trap '' TERM INT USR1
    [ -n "$TIMER" ] && kill "$TIMER" 2>/dev/null
    [ -n "$WORKER" ] && kill "$WORKER" 2>/dev/null
    [ -n "$WATCH" ] && kill "$WATCH" 2>/dev/null
    sleep 1
    [ -n "$WORKER" ] && kill -KILL "$WORKER" 2>/dev/null
    power_restore
    lipc-set-prop com.lab126.powerd wakeUp 1 2>/dev/null
    ui_resume
    lipc-set-prop com.lab126.powerd preventScreenSaver 0 2>/dev/null
    lipc-set-prop com.lab126.appmgrd start app://com.lab126.booklet.home 2>/dev/null
    rm -rf /tmp/dashboard-actions
    rm -f /tmp/dashboard-session.pid /tmp/dashboard.pid /tmp/dashboard-exit /tmp/dashboard-button.ready
    echo "$(date '+%F %T') exclusive session stopped" >> "$LOG"
}
trap cleanup 0
trap 'exit 0' TERM INT USR1
# Close KUAL and allow its final home transition BEFORE pausing the UI.
sleep 3
rm -f /tmp/dashboard-button.ready /tmp/dashboard-exit
sh "$DIR/bin/button-exit.sh" >> "$LOG" 2>&1 &
WATCH=$!
tries=0
while [ ! -f /tmp/dashboard-button.ready ] && [ "$tries" -lt 3 ]; do sleep 1; tries=$((tries+1)); done
if [ ! -f /tmp/dashboard-button.ready ]; then
    echo "$(date '+%F %T') cannot subscribe power-button exit; leaving system UI active" >> "$LOG"
    exit 1
fi
ui_pause
echo "$(date '+%F %T') exclusive UI acquired mode=$MODE" >> "$LOG"
DASH_LAYOUT=$MODE sh "$DIR/bin/clock.sh" >> "$LOG" 2>&1 &
WORKER=$!
while kill -0 "$WORKER" 2>/dev/null && kill -0 "$WATCH" 2>/dev/null; do
    [ -f /tmp/dashboard-exit ] && break
    [ -f /mnt/us/STOP_DASHBOARD ] && { rm -f /mnt/us/STOP_DASHBOARD; break; }
    # USB mass storage removes /mnt/us from the local mount namespace.
    # Resume the UI so USB operation and KUAL remain accessible.
    awk '$2=="/mnt/us"{ok=1} END{exit !ok}' /proc/mounts || break
    sleep 30 &
    TIMER=$!
    wait "$TIMER"
    TIMER=
done
