#!/bin/sh
# One run per user login, with bounded retry while networking becomes available.
set -eu
REPORT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
for delay in 15 30 60; do
    sleep "$delay"
    if /bin/sh "$REPORT_DIR/daily-report.sh"; then exit 0; fi
done
exit 1
