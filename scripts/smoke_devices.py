#!/usr/bin/env python3
"""End-to-end checks on paired, started test devices. Restores Wi-Fi after mobile tests."""
import argparse,json,time,uuid,subprocess,xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from device_tools import ADB,PACKAGE,shell,stats
p=argparse.ArgumentParser();p.add_argument('--sender',required=True);p.add_argument('--receiver',required=True);p.add_argument('--mobile',action='store_true');a=p.parse_args()
report=[]
def state(serial):
    root=ET.fromstring(shell(serial,f'run-as {PACKAGE} cat shared_prefs/state.xml'))
    return {e.get('name'): e.get('value') if e.get('value') is not None else e.text for e in root}
def post(title,body,tag):
    import shlex
    shell(a.sender,'cmd notification post -t '+shlex.quote(title)+' '+shlex.quote(tag)+' '+shlex.quote(body))
def wait_title(title,timeout=40):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        if any(row[0]==title for row in stats(a.receiver)['tests']):return round(time.monotonic()-start,2)
        time.sleep(2)
    raise AssertionError('Receiver did not persist '+title)
def check(name,fn):
    result=fn();report.append({'check':name,'result':'PASS','detail':result});print(name,'PASS',result,flush=True)
try:
    # Enabling a listener is asynchronous; wait for the bound service before generating the first notification.
    ready=time.monotonic()
    while '.NotificationBridge' not in shell(a.sender,f'dumpsys activity services {PACKAGE}').decode():
        if time.monotonic()-ready>15:raise AssertionError('Source notification listener is not bound; reopen notification access')
        time.sleep(1)
    time.sleep(0.5)
    run=uuid.uuid4().hex[:8]
    title='InkNotifier-E2E-'+run;body='System notification over encrypted ntfy transport';tag='ink-e2e-'+run
    check('real_notification',lambda:(post(title,body,tag),{'observed_seconds':wait_title(title)})[1])
    first=next(r for r in stats(a.receiver)['tests'] if r[0]==title)
    def duplicate():
        post(title,body,tag);time.sleep(4)
        after=stats(a.receiver)
        rows=[r for r in after['tests'] if r[0]==title];assert len(rows)==1 and rows[0][1]==first[1]
        return 'identical update suppressed'
    check('duplicate_notification',duplicate)
    updated=title+'-updated'
    def update():
        post(updated,body+' (updated)',tag);wait_title(updated)
        row=next(r for r in stats(a.receiver)['tests'] if r[0]==updated)
        assert row[2]==first[2] and row[1]==first[1]+1
        return 'same inbox item, newer version'
    check('notification_update',update)
    def source_ack():
        start=time.monotonic()
        while time.monotonic()-start<30:
            if stats(a.sender)['outbox']==0:return 'sender queue cleared after receiver ACK'
            time.sleep(2)
        raise AssertionError('No receiver ACK')
    check('receiver_ack',source_ack)
    def offline():
        shell(a.receiver,f'am force-stop {PACKAGE}; echo stopped')
        late='InkNotifier-Offline-'+run;post(late,'Stored while receiver process is stopped','ink-offline-'+run);time.sleep(3)
        assert stats(a.sender)['outbox']>=1
        assert all(r[0]!=late for r in stats(a.receiver)['tests'])
        shell(a.receiver,f'am start -n {PACKAGE}/.MainActivity')
        wait_title(late);source_ack()
        before=sorted(stats(a.receiver)['tests']);shell(a.receiver,f'am force-stop {PACKAGE}; am start -n {PACKAGE}/.MainActivity');time.sleep(6)
        assert sorted(stats(a.receiver)['tests'])==before,'Cache replay duplicated synthetic test messages'
        return 'restart caught up; subsequent cache replay did not duplicate messages'
    check('offline_and_replay',offline)
    if a.mobile:
        previous={s:shell(s,'settings get global wifi_on').decode().strip() for s in [a.sender,a.receiver]}
        try:
            for s in previous:shell(s,'svc wifi disable; echo wifi-disabled')
            time.sleep(5)
            assert all(shell(s,'settings get global wifi_on').strip()==b'0' for s in previous)
            mobile='InkNotifier-Mobile-'+run
            def mobile_check():
                post(mobile,'Both Wi-Fi radios disabled','ink-mobile-'+run);seconds=wait_title(mobile);source_ack()
                return {'wifi_disabled_on_both':True,'observed_seconds':seconds}
            check('mobile_network',mobile_check)
            def locked():
                for s in previous:shell(s,'input keyevent 223; echo screen-off')
                time.sleep(5)
                import re
                power_states={}
                for s in previous:
                    power=shell(s,'dumpsys power | grep mWakefulness=').decode()
                    match=re.search(r'mWakefulness=(\w+)',power); power_states[s]=match.group(1) if match else 'Unknown'
                assert power_states[a.sender] in ('Asleep','Dozing','Dreaming'),'Source did not enter screen-off state'
                locked_title='InkNotifier-Locked-'+run
                post(locked_title,'Delivered with both screens off','ink-locked-'+run);seconds=wait_title(locked_title);source_ack()
                return {'source_screen_off':True,'power_state_at_send':power_states,'wifi_disabled_on_both':True,'observed_seconds':seconds}
            check('source_locked_mobile_network',locked)
        finally:
            for s,value in previous.items():
                if value in ('1','2'):shell(s,'svc wifi enable; echo wifi-restored')
    check('final_queue',source_ack)
except Exception as e:
    report.append({'check':'execution','result':'FAIL','detail':str(e)});raise
finally:
    path=Path(__file__).resolve().parents[1]/'artifacts'/'device-test-results.json';path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({'date':'2026-10-12','checks':report},ensure_ascii=False,indent=2));print('Report:',path,flush=True)
