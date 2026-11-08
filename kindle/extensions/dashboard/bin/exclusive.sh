#!/bin/sh
# Only reversible SIGSTOP/SIGCONT; no framework shutdown or boot changes.
UI_PIDS=/tmp/dashboard-ui.pids
ui_resume() {
    if [ -f "$UI_PIDS" ]; then
        while read -r _pid _name; do
            _comm=$(cat "/proc/$_pid/comm" 2>/dev/null)
            [ "$_comm" = "$_name" ] && kill -CONT "$_pid" 2>/dev/null
        done < "$UI_PIDS"
        rm -f "$UI_PIDS"
    fi
    lipc-set-prop com.lab126.pillow disableEnablePillow enable 2>/dev/null
}
ui_pause() {
    : > "$UI_PIDS"
    lipc-set-prop com.lab126.pillow disableEnablePillow disable 2>/dev/null
    for _name in awesome mesquite; do
        for _pid in $(pidof "$_name" 2>/dev/null); do
            # Do not take ownership of a process another application already paused.
            _state=$(awk '/^State:/{print $2}' "/proc/$_pid/status" 2>/dev/null)
            [ "$_state" = T ] && continue
            echo "$_pid $_name" >> "$UI_PIDS"
            kill -STOP "$_pid" 2>/dev/null
        done
    done
}
