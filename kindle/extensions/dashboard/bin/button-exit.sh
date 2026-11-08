#!/bin/sh
# Block on stock power events; never open or grab any touch/input device.
export PATH=/usr/sbin:/sbin:/usr/bin:/bin:$PATH
ACTION_DIR=/tmp/dashboard-actions
FIFO=/tmp/dashboard-button-events
READY=/tmp/dashboard-button.ready
SOURCE=
cleanup_button() {
    [ -n "$SOURCE" ] && kill "$SOURCE" 2>/dev/null
    rm -f "$FIFO" "$READY"
}
trap cleanup_button 0
trap 'exit 0' TERM INT
command -v lipc-wait-event >/dev/null 2>&1 || exit 1
rm -f "$FIFO"
mkfifo "$FIFO" || exit 1
lipc-wait-event -m com.lab126.powerd outOfScreenSaver,goingToScreenSaver,charging > "$FIFO" &
SOURCE=$!
echo ready > "$READY"
while IFS= read -r event; do
    action=
    case "$event" in
        *outOfScreenSaver*) action=wake ;;
        *goingToScreenSaver*) action=sleep ;;
        *charging*) action=exit ;;
    esac
    [ -n "$action" ] || continue
    # Ignore the transitions requested by our own network/sleep code. RTC
    # resume emits wakeupFromSuspend, which is deliberately not subscribed.
    if [ "$action" != exit ] && [ -f "$ACTION_DIR/$action" ]; then
        until=$(cat "$ACTION_DIR/$action")
        rm -f "$ACTION_DIR/$action"
        case "$until" in ''|*[!0-9]*) until=0 ;; esac
        [ "$(date +%s)" -le "$until" ] && continue
    fi
    if [ -f /tmp/dashboard-session.pid ]; then
        echo "$(date '+%F %T') power button/cable exit event=$event"
        kill -USR1 "$(cat /tmp/dashboard-session.pid)" 2>/dev/null
    fi
    break
done < "$FIFO"
