#!/usr/bin/env python3
"""Read app UI or tap a visible text control using its current UIAutomator bounds."""
import argparse, re, subprocess, time, xml.etree.ElementTree as ET
from device_tools import ADB
p=argparse.ArgumentParser();p.add_argument('serial');p.add_argument('--tap');a=p.parse_args()
def adb(*args):
    for attempt in range(4):
        try: return subprocess.run([ADB,'-s',a.serial,*args],check=True,capture_output=True,timeout=20).stdout
        except subprocess.CalledProcessError:
            if attempt == 3: raise
            time.sleep(0.5)
xml=adb('shell','-n','uiautomator dump /data/local/tmp/ink-ui.xml >/dev/null && cat /data/local/tmp/ink-ui.xml')
root=ET.fromstring(xml)
for node in root.iter('node'):
    if node.get('package')!='dev.inknotifier':continue
    text=node.get('text','')
    if a.tap and text==a.tap:
        if node.get('clickable')!='true':raise SystemExit('Matching text is not clickable')
        x1,y1,x2,y2=map(int,re.findall(r'\d+',node.get('bounds')))
        adb('shell','-n',f'input tap {(x1+x2)//2} {(y1+y2)//2}')
        print('Tapped:',a.tap);break
    if not a.tap and text and not text.startswith('INK1:'): print(text)
else:
    if a.tap:raise SystemExit('Control not visible: '+a.tap)
