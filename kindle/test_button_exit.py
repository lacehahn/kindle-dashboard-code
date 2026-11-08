"""Power-key exit ignores programmed transitions and RTC wake events; uses no touch API."""
from pathlib import Path
import os,subprocess,tempfile,time
source=Path(__file__).resolve().parent/'extensions/dashboard/bin/button-exit.sh'
for events,programmed,expected in [
 ('outOfScreenSaver 0\n',None,True),
 ('goingToScreenSaver 0\n',None,True),
 ('goingToScreenSaver 0\nwakeupFromSuspend 0\n','sleep',False),
 ('outOfScreenSaver 0\n','wake',False),
 ('outOfScreenSaver 0\noutOfScreenSaver 0\n','wake',True),
 ('charging 1\n',None,True),
]:
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp);script=root/'button.sh'
  script.write_text(source.read_text().replace('/tmp/dashboard',str(root/'dashboard')))
  actions=root/'dashboard-actions';actions.mkdir()
  if programmed:(actions/programmed).write_text(str(int(time.time())+10))
  (root/'dashboard-session.pid').write_text('424242')
  commands=root/'bin';commands.mkdir();stub=commands/'lipc-wait-event'
  stub.write_text('#!/bin/sh\ncat "$EVENTS"\n');stub.chmod(0o755)
  eventfile=root/'events';eventfile.write_text(events)
  signals=root/'signals'
  harness='kill() { echo "$*" >> "$SIGNALS"; }\n. "$SCRIPT"\n'
  env=dict(os.environ,PATH=str(commands)+':'+os.environ['PATH'],SCRIPT=str(script),EVENTS=str(eventfile),SIGNALS=str(signals))
  subprocess.run(['sh'],input=harness,text=True,env=env,check=True,timeout=3,stdout=subprocess.DEVNULL)
  got=signals.exists() and '-USR1 424242' in signals.read_text()
  assert got==expected,(events,programmed,got)
  assert not (root/'dashboard-button.ready').exists()
assert '/dev/input' not in source.read_text()
print('PASS: physical sleep/wake exit; programmed sleep/wake ignored; RTC wake keeps dashboard; cable exit; no touch access')
