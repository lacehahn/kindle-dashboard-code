#!/bin/sh
set -eu
if [ -n "${INK_ADB:-}" ]; then exec "$INK_ADB" "$@"; fi
if [ -x /Users/lance/.cache/inknotifier/adb35/platform-tools/adb ]; then
  exec /Users/lance/.cache/inknotifier/adb35/platform-tools/adb "$@"
fi
exec adb "$@"
