#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# Set ZIG to a local Zig executable, or install Zig in PATH.
ZIG=${ZIG:-zig}
"$ZIG" cc -target arm-linux-musleabi -mcpu=cortex_a9 -O2 -s -static "$ROOT/native/render.c" -o "$ROOT/extensions/dashboard/bin/render" -lm
cc -O2 "$ROOT/native/render.c" -o "$ROOT/../.device-config/render-host" -lm


"$ZIG" cc -target arm-linux-musleabi -mcpu=cortex_a9 -O2 -s -static "$ROOT/native/tickwait.c" -o "$ROOT/extensions/dashboard/bin/tickwait"
cc -O2 "$ROOT/native/tickwait.c" -o "$ROOT/../.device-config/tickwait-host"
"$ZIG" cc -DJSMN_PARENT_LINKS -target arm-linux-musleabi -mcpu=cortex_a9 -O2 -s -static "$ROOT/native/reportread.c" -o "$ROOT/extensions/dashboard/bin/reportread"
cc -DJSMN_PARENT_LINKS -O2 "$ROOT/native/reportread.c" -o "$ROOT/../.device-config/reportread-host"
"$ZIG" cc -DJSMN_PARENT_LINKS -target arm-linux-musleabi -mcpu=cortex_a9 -O2 -s -static "$ROOT/native/weatherread.c" -o "$ROOT/extensions/dashboard/bin/weatherread" -lm
cc -DJSMN_PARENT_LINKS -O2 "$ROOT/native/weatherread.c" -o "$ROOT/../.device-config/weatherread-host" -lm
