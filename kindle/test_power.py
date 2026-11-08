"""Exercise stock-powerd event scheduling, wake delivery and Wi-Fi restoration with stubs."""
from pathlib import Path
import os, subprocess, tempfile, time
ROOT=Path(__file__).resolve().parent
WAIT=ROOT.parent/'.device-config/tickwait-host'
def wait_for(predicate):
 for _ in range(200):
  if predicate():return
  time.sleep(.01)
 raise AssertionError('expected event did not arrive')

def scenario(reject):
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp);dev=root/'mnt/us';scripts=dev/'extensions/dashboard/bin';scripts.mkdir(parents=True)
  for name in ['power.sh','power-events.sh']:
   text=(ROOT/'extensions/dashboard/bin'/name).read_text().replace('/mnt/us',str(dev)).replace('/tmp/dashboard',str(root/'dashboard'))
   (scripts/name).write_text(text)
  commands=root/'bin';commands.mkdir(); calls=root/'calls'
  def stub(name,body):
   path=commands/name;path.write_text('#!/bin/sh\n'+body+'\n');path.chmod(0o755)
  stub('lipc-set-prop',f'''echo "$*" >> '{calls}'
case "$*" in *rtcWakeup*) [ "$REJECT" != 1 ] || exit 1;;esac''')
  stub('lipc-get-prop','case "$*" in *battLevel*) echo 74;;*cmState*) echo CONNECTED;;*enable*) echo 1;;esac')
  stub('lipc-wait-event','printf "readyToSuspend 10\\nwakeupFromSuspend 0\\n"; exec sleep 30')
  env=dict(os.environ,PATH=str(commands)+':'+os.environ['PATH'],REJECT='1' if reject else '0')
  power=root/'dashboard-power';power.mkdir();os.mkfifo(power/'ticks')
  (power/'next-tick').write_text(str(int(time.time())+60))
  (power/'wifi-before').write_text('1\n')
  p=subprocess.Popen(['sh',str(scripts/'power-events.sh')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
  (power/'events.pid').write_text(str(p.pid))
  try:
   if reject:wait_for(lambda:(power/'failed').exists() and calls.exists() and 'com.lab126.powerd wakeUp 1' in calls.read_text())
   else:wait_for(lambda:(power/'armed-count').exists())
   text=calls.read_text()
   assert 'com.lab126.powerd rtcWakeup' in text
   if reject:assert 'com.lab126.powerd wakeUp 1' in text
   start=time.monotonic()
   event=subprocess.check_output([str(WAIT),str(power/'ticks'),'60'],text=True)
   assert time.monotonic()-start<2,'Wake event was delayed by the 60-second timeout'
   assert ('failed' if reject else 'wake') in event
   # Restoring on exit must terminate owned listeners and restore original Wi-Fi.
   script='. "$SCRIPT"\nPOWER_ACTIVE=1\npower_restore\n'
   subprocess.run(['sh'],input=script,text=True,env=dict(env,SCRIPT=str(scripts/'power.sh')),check=True)
   p.wait(timeout=3)
   assert 'com.lab126.wifid enable 1' in calls.read_text()
   assert not power.exists()
   # Network is awake only around weather work; explicit sleep follows Wi-Fi off.
   power.mkdir();(power/'wifi-before').write_text('0\n')
   calls.write_text('')
   network='. "$SCRIPT"\nPOWER_ACTIVE=1\npower_network_on\necho WEATHER >> "$CALLS"\npower_network_off\npower_enter_sleep\npower_restore\n'
   subprocess.run(['sh'],input=network,text=True,env=dict(env,SCRIPT=str(scripts/'power.sh'),CALLS=str(calls),LOG=str(dev/'dashboard.log')),check=True)
   order=calls.read_text()
   assert order.index('com.lab126.wifid enable 1') < order.index('WEATHER')
   assert order.index('WEATHER') < order.index('com.lab126.wifid enable 0') < order.index('com.lab126.powerd preventScreenSaver 0') < order.index('com.lab126.powerd powerButton 1')
   assert order.strip().endswith('com.lab126.wifid enable 0'),'Originally disabled Wi-Fi must stay disabled on exit'
  except Exception:
   if p.poll() is None:p.terminate();p.wait(timeout=3)
   print('EVENT STDERR:',p.stderr.read().decode())
   print('CALLS:',calls.read_text() if calls.exists() else '(none)')
   print('FILES:',list(power.iterdir()) if power.exists() else '(none)')
   raise
  finally:
   if p.poll() is None:p.terminate();p.wait(timeout=3)
   p.stderr.close()
for reject in [False,True]:scenario(reject)
# The no-event path should return after one second, without writing the kernel power state.
with tempfile.TemporaryDirectory() as tmp:
 path=Path(tmp)/'fifo';os.mkfifo(path);start=time.monotonic()
 assert subprocess.check_output([str(WAIT),str(path),'1'])==b''
 assert .8<time.monotonic()-start<2
for name in ['power.sh','power-events.sh']:
 source=(ROOT/'extensions/dashboard/bin'/name).read_text()
 assert '/sys/power/state' not in source.replace('# Use stock powerd\'s suspend state machine. Never write /sys/power/state.','')
print('PASS: RTC ready-state scheduling; immediate RTC wake delivery; rejected alarms recover; original Wi-Fi restored; quiet timeout; no forced kernel suspend')
