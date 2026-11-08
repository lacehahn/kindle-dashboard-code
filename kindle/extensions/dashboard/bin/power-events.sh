#!/bin/sh
export PATH=/usr/sbin:/sbin:/usr/bin:/bin:$PATH
DASH_DIR=/mnt/us/extensions/dashboard
LOG=/mnt/us/dashboard.log
. "$DASH_DIR/bin/power.sh"
SOURCE=
cleanup_events() { [ -n "$SOURCE" ] && kill "$SOURCE" 2>/dev/null; }
trap cleanup_events 0
trap 'exit 0' TERM INT
mkfifo "$POWER_DIR/events" || exit 1
# Keep a FIFO reader alive between clock waits. This avoids blocking the power callback.
exec 8<> "$POWER_DIR/ticks"
lipc-wait-event -m com.lab126.powerd readyToSuspend,wakeupFromSuspend,goingToScreenSaver,charging > "$POWER_DIR/events" &
SOURCE=$!; echo "$SOURCE" > "$POWER_DIR/source.pid"
count=0
wakes=0
while IFS= read -r event; do
    case "$event" in
        *readyToSuspend*)
            # Handle first, without any redraw/network work in this short state window.
            now=$(date +%s); due=$(cat "$POWER_DIR/next-tick" 2>/dev/null)
            case "$due" in ''|*[!0-9]*) due=$(next_refresh_epoch "$now") ;; esac
            seconds=$((due-now)); [ "$seconds" -ge 1 ] || seconds=1
            if lipc-set-prop -i com.lab126.powerd rtcWakeup "$seconds" 2>> "$LOG"; then
                count=$((count+1)); echo "$count" > "$POWER_DIR/armed-count"
                if [ "$count" -le 3 ] || [ $((count%6)) -eq 0 ]; then
                    power_log "RTC armed seconds=$seconds cycles=$count"
                fi
            else
                : > "$POWER_DIR/failed"
                lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
                power_mark_action wake
                lipc-set-prop com.lab126.powerd wakeUp 1 2>/dev/null
                power_log 'RTC request rejected; returning to compatibility mode'
                printf 'failed\n' >&8
            fi
            ;;
        *wakeupFromSuspend*)
            wakes=$((wakes+1))
            printf 'wake\n' >&8
            if [ "$wakes" -le 3 ] || [ $((wakes%6)) -eq 0 ]; then
                power_log "resume received count=$wakes"
            fi ;;

        *goingToScreenSaver*)
            lipc-set-prop com.lab126.blanket unload screensaver 2>> "$LOG"
            printf 'redraw\n' >&8 ;;
        *charging*)
            # Restore normal USB operation immediately when a cable is inserted.
            if [ -f /tmp/dashboard-session.pid ]; then kill -USR1 "$(cat /tmp/dashboard-session.pid)" 2>/dev/null; fi ;;
    esac
done < "$POWER_DIR/events"
: > "$POWER_DIR/failed"
printf 'failed\n' >&8
