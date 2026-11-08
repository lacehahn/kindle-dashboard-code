#!/usr/bin/env python3
"""Pair two USB-connected test devices without placing secrets in command arguments/logs."""
import argparse, base64, json, secrets, subprocess
from device_tools import ADB
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--sender',required=True)
p.add_argument('--receiver',required=True)
p.add_argument('--server',default='https://ntfy.sh')
p.add_argument('--rotate',action='store_true',help='Explicitly replace the existing pair')
a=p.parse_args()
package='dev.inknotifier'
root=Path(__file__).resolve().parents[1]
private=root/'.device-config'; private.mkdir(mode=0o700,exist_ok=True)
seed=private/'pair.json'
if seed.exists() and not a.rotate:
    pair=json.loads(seed.read_text())
else:
    pair={'server':a.server,'pair':secrets.token_hex(24),'key':base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')}
    seed.write_text(json.dumps(pair));seed.chmod(0o600)
for device,role in [(a.sender,'sender'),(a.receiver,'receiver')]:
    config=json.dumps({**pair,'role':role}).encode()
    def adb(*args,**kw):
        return subprocess.run([ADB,'-s',device,*args],check=True,**kw)
    adb('shell','am','force-stop',package,stdout=subprocess.DEVNULL)
    adb('shell','run-as',package,'mkdir','-p','files',stdout=subprocess.DEVNULL)
    adb('shell','run-as',package,'sh','-c',"'cat > files/pairing.json'",input=config,stdout=subprocess.DEVNULL)
    adb('shell','pm','grant',package,'android.permission.POST_NOTIFICATIONS',stdout=subprocess.DEVNULL)
    adb('shell','dumpsys','deviceidle','whitelist','+'+package,stdout=subprocess.DEVNULL)
    if role=='sender':
        adb('shell','cmd','notification','allow_listener',package+'/.NotificationBridge',stdout=subprocess.DEVNULL)
    adb('shell','am','start','-n',package+'/.MainActivity',stdout=subprocess.DEVNULL)
    print(f'{role}: pairing imported; notification permission configured; app opened')
print('Pair key stored privately in .device-config/pair.json (Git ignored). Tap start on each device.')
