"""Native JSON validation and atomic weather replacement without device access."""
from pathlib import Path
import copy,json,os,subprocess,tempfile,shutil
root=Path(__file__).resolve().parent;reader=root.parent/'.device-config/weatherread-host'
fixture={'current':{'time':'2026-11-09T01:00','temperature_2m':13.5,'relative_humidity_2m':63,'wind_speed_10m':2.1,'weather_code':2},'daily':{'time':['2026-11-09','2026-11-10','2026-11-11','2026-11-12'],'temperature_2m_max':[18,19,20,21],'temperature_2m_min':[9,10,11,12],'weather_code':[2,3,61,0]}}
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'bin').mkdir();shutil.copyfile(reader,p/'bin/weatherread');(p/'bin/weatherread').chmod(0o755)
 curl=p/'bin/curl';curl.write_text('#!/bin/sh\nwhile [ "$#" -gt 0 ]; do if [ "$1" = -o ]; then cp "$INPUT" "$2"; exit; fi; shift; done\nexit 1\n');curl.chmod(0o755)
 payload=p/'input.json';cache=p/'weather';library=root/'extensions/dashboard/bin/report-weather.sh'
 harness='. "$LIBRARY"\nWEATHER_CACHE="$CACHE"; LOG="$TEST_ROOT/log"; LAT=35; LON=139; TZ_NAME=Asia/Tokyo\nreport_weather_fetch\n'
 env=dict(os.environ,PATH=str(p/'bin')+':'+os.environ['PATH'],DASH_DIR=str(p),INPUT=str(payload),LIBRARY=str(library),CACHE=str(cache),TEST_ROOT=str(p))
 payload.write_text(json.dumps(fixture));result=subprocess.run(['sh'],input=harness,text=True,env=env,capture_output=True);assert result.returncode==0,result.stderr
 original=cache.read_bytes();assert original.decode().splitlines()==['current|2026-11-09T01:00|13.5|63|2.1|2|18|9','forecast|2026-11-10|3|19|10','forecast|2026-11-11|61|20|11','forecast|2026-11-12|0|21|12']
 incomplete=copy.deepcopy(fixture);incomplete['daily']['time'].pop()
 invalid=copy.deepcopy(fixture);invalid['current']['relative_humidity_2m']=None
 reversed_dates=copy.deepcopy(fixture);reversed_dates['daily']['time'].reverse()
 for bad in [incomplete,invalid,reversed_dates,{'error':True}]:
  payload.write_text(json.dumps(bad));result=subprocess.run(['sh'],input=harness,text=True,env=env,capture_output=True)
  assert result.returncode!=0;assert cache.read_bytes()==original
print('PASS: fresh current weather + 3 forecast dates; malformed/partial/null/unordered responses preserve cache')
