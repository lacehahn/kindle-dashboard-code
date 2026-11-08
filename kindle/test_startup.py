"""Regression checks for explicit layout selection and reversible UI ownership."""
from pathlib import Path
import os,subprocess,tempfile,time
SOURCE=Path(__file__).resolve().parent/'extensions/dashboard/bin'
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);dev=root/'mnt/us';scripts=dev/'extensions/dashboard/bin';scripts.mkdir(parents=True)
 for name in ['start.sh','stop.sh','exclusive.sh']:
  text=(SOURCE/name).read_text().replace('/mnt/us',str(dev)).replace('/tmp/dashboard',str(root/'dashboard')).replace('/proc/',str(root/'proc')+'/')
  (scripts/name).write_text(text)
 commands=root/'bin';commands.mkdir()
 def stub(name,body):
  path=commands/name;path.write_text('#!/bin/sh\n'+body+'\n');path.chmod(0o755)
 stub('sleep',':');stub('lipc-set-prop',':')
 stub('setsid',f'echo "$3" > {root}/launch-mode')
 stub('fbink',f'echo unexpected >> {root}/errors;exit 99')
 stub('lipc-get-prop',f'echo unexpected >> {root}/errors;exit 99')
 env=dict(os.environ,PATH=str(commands)+':'+os.environ['PATH'])
 for mode in ['portrait','landscape']:
  (root/'dashboard-session.pid').unlink(missing_ok=True)
  subprocess.run(['sh',str(scripts/'start.sh'),mode],env=env,check=True)
  for _ in range(100):
   p=root/'launch-mode'
   if p.exists() and p.read_text().strip()==mode:break
   time.sleep(.01)
  assert p.read_text().strip()==mode
 assert not (root/'errors').exists()
 # STOP/CONT must affect only owned PIDs and never a process already paused.
 for pid,name,state in [(101,'awesome','S'),(102,'mesquite','T')]:
  folder=root/'proc'/str(pid);folder.mkdir(parents=True)
  (folder/'comm').write_text(name+'\n');(folder/'status').write_text('State:\t'+state+'\n')
 harness='''kill() { echo "$*" >> "$SIGNALS"; }
pidof() { case "$1" in awesome) echo 101;;mesquite) echo 102;;esac; }
. "$SCRIPT"
ui_pause
ui_resume
'''
 subprocess.run(['sh'],input=harness,text=True,env=dict(env,SCRIPT=str(scripts/'exclusive.sh'),SIGNALS=str(root/'signals')),check=True)
 assert (root/'signals').read_text().splitlines()==['-STOP 101','-CONT 101']
print('PASS: explicit menu modes; no state probing; UI pause/resume owns only its own processes')
