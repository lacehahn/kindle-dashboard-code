#!/bin/sh
# Use stock powerd's suspend state machine. Never write /sys/power/state.
POWER_DIR=/tmp/dashboard-power
ACTION_DIR=/tmp/dashboard-actions
# Asia/Tokyo's UTC offset is a multiple of 600 seconds, so these boundaries
# are exactly local :00, :10, :20, :30, :40 and :50 as requested.
next_refresh_epoch() { echo $(( ($1 / 600 + 1) * 600 )); }
refresh_delay() { echo $(( $(next_refresh_epoch "$1") - $1 )); }
power_mark_action() {
    mkdir -p "$ACTION_DIR"
    echo "$(($(date +%s)+10))" > "$ACTION_DIR/$1"
}
power_wake() {
    _state=$(lipc-get-prop com.lab126.powerd state 2>/dev/null)
    case "$_state" in
        active|Active) rm -f "$ACTION_DIR/wake" ;;
        *) power_mark_action wake ;;
    esac
    lipc-set-prop com.lab126.powerd wakeUp 1 2>/dev/null
}
power_log() { echo "$(date '+%F %T') power: $*" >> "$LOG"; }
power_restore() {
    if [ -d "$POWER_DIR" ]; then
        for _file in events.pid source.pid; do
            if [ -f "$POWER_DIR/$_file" ]; then kill "$(cat "$POWER_DIR/$_file")" 2>/dev/null; fi
        done
        power_wake
        lipc-set-prop com.lab126.blanket load screensaver 2>/dev/null
        if [ -f "$POWER_DIR/wifi-before" ]; then
            _wifi=$(cat "$POWER_DIR/wifi-before")
            case "$_wifi" in 0|1) lipc-set-prop com.lab126.wifid enable "$_wifi" 2>/dev/null ;; esac
        fi
        rm -rf "$POWER_DIR"
    fi
}
power_fallback() {
    power_log "compatibility fallback: $*"
    # Restore system modules and Wi-Fi before returning to the proven awake loop.
    power_restore
    lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
    POWER_ACTIVE=0
    POWER_REPAINT=1
}
power_init() {
    POWER_ACTIVE=0
    [ "${DASH_LOW_POWER:-1}" = 1 ] || return 0
    if ! command -v lipc-wait-event >/dev/null 2>&1 || [ ! -x "$DASH_DIR/bin/tickwait" ]; then
        power_log 'power event support unavailable; using compatibility mode'
        return 0
    fi
    mkdir -p "$POWER_DIR"
    _wifi=$(lipc-get-prop com.lab126.wifid enable 2>/dev/null)
    case "$_wifi" in 0|1) echo "$_wifi" > "$POWER_DIR/wifi-before" ;;
        *) power_log 'cannot save Wi-Fi state; using compatibility mode'; rmdir "$POWER_DIR"; return 0 ;;
    esac
    mkfifo "$POWER_DIR/ticks" || { power_restore; return 0; }
    date +%s > "$POWER_DIR/started"
    POWER_ACTIVE=1
    if ! lipc-set-prop com.lab126.blanket unload screensaver 2>> "$LOG"; then
        power_fallback 'cannot hide native screensaver'; return 0
    fi
    sh "$DASH_DIR/bin/power-events.sh" >> "$LOG" 2>&1 &
    echo $! > "$POWER_DIR/events.pid"
    # Give the subscription time to connect before requesting any sleep state.
    sleep 1
    if ! kill -0 "$(cat "$POWER_DIR/events.pid")" 2>/dev/null; then
        power_fallback 'power event subscription exited'; return 0
    fi
    power_log "event-driven sleep enabled; period=600s aligned; frontlight untouched"
}
power_network_on() {
    [ "$POWER_ACTIVE" = 1 ] || return 0
    # Only network refreshes request a fully active state; RTC clock-only wakes do not.
    power_wake
    if ! lipc-set-prop com.lab126.wifid enable 1 2>> "$LOG"; then
        power_fallback 'cannot enable Wi-Fi'; return 0
    fi
    _tries=0
    while [ "$_tries" -lt 20 ]; do
        _connected=$(lipc-get-prop com.lab126.wifid cmState 2>/dev/null)
        case "$_connected" in CONNECTED|CONNECTED:*) break ;; esac
        _tries=$((_tries+1)); sleep 1
    done
}
power_network_off() {
    [ "$POWER_ACTIVE" = 1 ] || return 0
    if ! lipc-set-prop com.lab126.wifid enable 0 2>> "$LOG"; then
        power_fallback 'cannot disable Wi-Fi'
    fi
}
power_enter_sleep() {
    [ "$POWER_ACTIVE" = 1 ] || return 0
    power_tick_done
    # Stock powerd controls the hardware. rtcWakeup is set by its ready event.
    lipc-set-prop com.lab126.powerd preventScreenSaver 0 2>> "$LOG" || { power_fallback 'cannot release sleep inhibition'; return; }
    power_mark_action sleep
    if ! lipc-set-prop com.lab126.powerd powerButton 1 2>> "$LOG"; then
        power_fallback 'cannot request stock sleep'
    fi
}
power_wait() {
    _now=$(date +%s)
    _seconds=$((NEXT_REFRESH - _now))
    [ "$_seconds" -gt 0 ] || return 0
    if [ "$POWER_ACTIVE" = 1 ]; then
        # Capture events so scheduled wakeups are consumed before the next redraw.
        if ! "$DASH_DIR/bin/tickwait" "$POWER_DIR/ticks" "$_seconds" > "$POWER_DIR/last-event"; then
            power_fallback 'event wait failed'
        elif [ -f "$POWER_DIR/failed" ] || ! kill -0 "$(cat "$POWER_DIR/events.pid")" 2>/dev/null; then
            power_fallback 'powerd wake scheduling unavailable'
        fi
    else
        sleep "$_seconds"
    fi
}
power_tick_done() {
    NEXT_REFRESH=$(next_refresh_epoch "$(date +%s)")
    if [ "$POWER_ACTIVE" = 1 ]; then echo "$NEXT_REFRESH" > "$POWER_DIR/next-tick"; fi
}
