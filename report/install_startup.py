#!/usr/bin/env python3
"""Enable/disable this user's RunAtLoad LaunchAgent; leaves the daily crontab alone."""
import argparse,os,plistlib,subprocess,sys
from pathlib import Path
LABEL='dev.inkdesk.report.login'
def make_plist(runtime):
 return {'Label':LABEL,'ProgramArguments':['/bin/sh',str(runtime/'report/startup-report.sh')],
         'RunAtLoad':True,'ProcessType':'Background','WorkingDirectory':str(runtime),
         'StandardOutPath':str(runtime/'logs/login-launch.log'),
         'StandardErrorPath':str(runtime/'logs/login-launch.log')}
def main():
 parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
 group.add_argument('--enable',action='store_true');group.add_argument('--disable',action='store_true');args=parser.parse_args()
 if sys.platform!='darwin':raise ValueError('仅支持 macOS')
 runtime=Path.home()/'Library/Application Support/InkDesk'
 plist=Path.home()/'Library/LaunchAgents'/(LABEL+'.plist');target='gui/'+str(os.getuid())+'/'+LABEL
 active=subprocess.run(['/bin/launchctl','print',target],capture_output=True).returncode==0
 if args.disable:
  if active:subprocess.run(['/bin/launchctl','bootout',target],check=True)
  plist.unlink(missing_ok=True)
  print('已关闭登录后执行；每日 20:00 的 crontab 保留。');return
 if not (runtime/'report/daily-report.sh').is_file():raise ValueError('请先运行 install_cron.py')
 # Stage the login wrapper next to the already isolated daily runtime.
 import shutil
 shutil.copyfile(Path(__file__).with_name('startup-report.sh'),runtime/'report/startup-report.sh')
 (runtime/'report/startup-report.sh').chmod(0o700)
 (runtime/'logs').mkdir(exist_ok=True)
 log=runtime/'logs/login-launch.log';log.touch(exist_ok=True);log.chmod(0o600)
 desired=plistlib.dumps(make_plist(runtime))
 if active and plist.is_file() and plist.read_bytes()==desired:
  print('登录后执行已启用；每日 crontab 保留。');return
 if active:subprocess.run(['/bin/launchctl','bootout',target],check=True)
 plist.parent.mkdir(parents=True,exist_ok=True);plist.write_bytes(desired);plist.chmod(0o600)
 subprocess.run(['/bin/launchctl','enable',target],check=True)
 subprocess.run(['/bin/launchctl','bootstrap','gui/'+str(os.getuid()),str(plist)],check=True)
 if subprocess.run(['/bin/launchctl','print',target],capture_output=True).returncode:raise ValueError('LaunchAgent 注册后验证失败')
 print('已启用登录后执行一次；每日 20:00 的 crontab 保留。首次加载会立即试运行。')
if __name__=='__main__':
 try:main()
 except Exception as e:
  print('设置未完成：'+(str(e) if isinstance(e,ValueError) else type(e).__name__),file=sys.stderr);sys.exit(1)
