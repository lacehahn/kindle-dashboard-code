"""Cached battery reads and nightly freshness gate, using the real shell controller."""
from pathlib import Path
import os,subprocess,tempfile
source=Path(__file__).parent/'extensions/dashboard/bin/report-layout.sh'
for name in ['power.sh','power-events.sh']:
 assert 'battLevel' not in (source.parent/name).read_text(),name
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);(root/'bin').mkdir();(root/'bin/reportread').write_text('#!/bin/sh\necho "$REPORT_EPOCH"\n');(root/'bin/reportread').chmod(0o755)
 (root/'bin/lipc-get-prop').write_text('#!/bin/sh\necho read >> "$TEST_ROOT/reads"; echo 87\n');(root/'bin/lipc-get-prop').chmod(0o755)
 code=source.read_text().replace('. "$DASH_DIR/bin/report-download.sh"',':').replace('. "$DASH_DIR/bin/report-weather.sh"',':').replace('/mnt/us/dashboard',str(root/'data'))
 (root/'data').mkdir();(root/'data/report-current').write_text('a'*64)
 harness=code+'''
COMMANDS="$TEST_ROOT/commands"; LOG="$TEST_ROOT/log"; DASH_DIR="$TEST_ROOT"
t() { :; }
PATH="$TEST_ROOT/bin:$PATH"
report_update_local
report_battery; report_battery
[ "$(wc -l < "$TEST_ROOT/reads" | tr -d ' ')" = 1 ] || exit 11
report_update_local; report_battery
[ "$(wc -l < "$TEST_ROOT/reads" | tr -d ' ')" = 2 ] || exit 12
power_network_on() { :; }; power_network_off() { :; }; report_download() { return 0; }; report_weather_fetch() { [ "$WEATHER_OK" = 1 ]; }
date() { case "$1" in +%H%M) echo "$HM";; +%H) echo 01;; +%M|+%S) echo 00;; +%Y%m%d) echo 20261108;; +%s) echo 1794136200;; *) echo test;; esac; }
REPORT_REPOSITORY=example/private
weather_due 1794136200 || exit 13
HM=0059; weather_due 1794136200 && exit 19
HM=0100
refresh_weather
if [ "$FRESH" = 1 ] && [ "$WEATHER_OK" = 1 ]; then
 [ "$(cat "$TEST_ROOT/data/report-day")" = 20261108 ] || exit 14
 weather_due 1794140000 && exit 15
else
 [ "$FRESH" = 1 ] || [ ! -f "$TEST_ROOT/data/report-day" ] || exit 16
 weather_due 1794136201 && exit 17
 weather_due 1794140000 || exit 18
fi
exit 0
'''
 for fresh,weather_ok in [(False,True),(True,True),(True,False)]:
  stamp=1794136200-5*3600 if fresh else 1794136200-7*3600
  (root/'data/weather-day').unlink(missing_ok=True);(root/'data/report-day').unlink(missing_ok=True);(root/'reads').unlink(missing_ok=True)
  p=subprocess.run(['sh'],input=harness,text=True,capture_output=True,env=dict(os.environ,TEST_ROOT=str(root),REPORT_EPOCH=str(stamp),HM='0100',WEATHER_OK=str(int(weather_ok)),FRESH=str(int(fresh))))
  assert p.returncode==0,(stamp,p.returncode,p.stderr)
print('PASS: initial/boundary battery reads only; redraws use cache; 01:00 weather/report fetch gate; partial failures retry; previous evening snapshot accepted')
