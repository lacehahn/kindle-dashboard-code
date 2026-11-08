#!/bin/sh
# Standalone cron entrypoint. The installer copies this beside run.py.
set -eu
umask 077
export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin
export TZ=Asia/Tokyo
export LANG=en_US.UTF-8
export PYTHONUTF8=1
export PYTHONUNBUFFERED=1
REPORT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RUNTIME_DIR=$(CDPATH= cd -- "$REPORT_DIR/.." && pwd)
LOG_DIR="$RUNTIME_DIR/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/daily-report.log"
if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -ge 2097152 ]; then
    mv -f "$LOG" "$LOG.1"
fi
exec >> "$LOG" 2>&1
trap 'result=$?; printf "%s finished status=%s\n" "$(date "+%Y-%m-%d %H:%M:%S %Z")" "$result"; exit "$result"' 0
printf '\n%s starting private report\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
cd "$RUNTIME_DIR"
"$RUNTIME_DIR/venv/bin/python3" "$REPORT_DIR/run.py" --publish
