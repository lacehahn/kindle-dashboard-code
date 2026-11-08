#!/usr/bin/env python3
"""Stage a standalone macOS runtime and install one idempotent daily crontab entry."""
import argparse,datetime,json,os,re,shlex,shutil,subprocess,sys,time
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
PROJECT=SOURCE.parent
BEGIN='# BEGIN INKDESK_PRIVATE_REPORT'
END='# END INKDESK_PRIVATE_REPORT'
def render_crontab(existing,runner):
 if existing.count(BEGIN)!=existing.count(END) or existing.count(BEGIN)>1:
  raise ValueError('现有 InkDesk crontab 标记异常，未修改 crontab')
 cleaned=re.sub(re.escape(BEGIN)+r'\n.*?'+re.escape(END)+r'(?:\n|$)','',existing,flags=re.S).rstrip('\n')
 command='0 20 * * * /bin/sh '+shlex.quote(str(runner))
 # A percent sign has special meaning even inside shell quotes in crontab.
 command=command.replace('%',r'\%')
 return (cleaned+'\n\n' if cleaned else '')+BEGIN+'\n'+command+'\n'+END+'\n'
def read_crontab():
 p=subprocess.run(['/usr/bin/crontab','-l'],capture_output=True,text=True)
 if p.returncode==0:return p.stdout
 if p.returncode==1 and 'no crontab for' in p.stderr:return ''
 raise ValueError('无法读取 crontab，未进行修改')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--startup',choices=['keep','login','none'],default='keep');args=parser.parse_args()
 if sys.platform!='darwin':raise ValueError('此安装器面向当前 macOS')
 if time.localtime().tm_gmtoff!=9*3600:raise ValueError('Mac 系统时区不是日本时间；请先确认每天 20:00 的时区')
 runtime=Path.home()/'Library/Application Support/InkDesk'
 runtime.mkdir(parents=True,exist_ok=True);runtime.chmod(0o700)
 for folder in ['report','logs','.device-config']:
  (runtime/folder).mkdir(exist_ok=True);(runtime/folder).chmod(0o700)
 for name in ['run.py','layouts.py','daily-report.sh','requirements.txt','config.local.json']:
  src=SOURCE/name
  if not src.is_file():raise ValueError('缺少 '+name)
  shutil.copyfile(src,runtime/'report'/name)
  (runtime/'report'/name).chmod(0o600 if name=='config.local.json' else 0o700)
 shutil.copytree(SOURCE/'brand',runtime/'report/brand',dirs_exist_ok=True)
 shutil.copytree(SOURCE/'site',runtime/'report/site',dirs_exist_ok=True)
 # Only report inputs are copied; no Android project, full device backup or session logs.
 data=runtime/'kindle/dashboard';data.mkdir(parents=True,exist_ok=True)
 for name in ['lunar.dat','terms.dat']:shutil.copyfile(PROJECT/'kindle/dashboard'/name,data/name)
 shutil.copytree(PROJECT/'kindle/dashboard/icons',data/'icons',dirs_exist_ok=True)
 fonts=[Path('/Volumes/Kindle/dashboard/fonts/cjk-bold.ttf'),*sorted((PROJECT/'.device-config/kindle-backups').glob('*/dashboard/fonts/cjk-bold.ttf'))]
 font=next((p for p in fonts if p.is_file()),None)
 if font is None:raise ValueError('缺少日期标记字体，请连接 Kindle 后重试')
 dest=runtime/'.device-config/kindle-backups/runtime/dashboard/fonts/cjk-bold.ttf'
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(font,dest)
 config=json.loads((SOURCE/'config.local.json').read_text())
 if config.get('publish_mode')!='private_repository':raise ValueError('必须启用 private_repository 模式')
 for key,default in [('github_token_file','../.device-config/github-read-token'),('secrets_file','../.device-config/report-secrets.json')]:
  src=(SOURCE/config.get(key,default)).resolve()
  if key=='github_token_file' and (not src.is_file() or not src.read_text().strip()):raise ValueError('请先配置 GitHub 只读令牌')
  filename='github-read-token' if key=='github_token_file' else 'report-secrets.json'
  target=runtime/'.device-config'/filename
  if src.is_file():shutil.copyfile(src,target);target.chmod(0o600)
  elif target.exists():target.unlink()
  config[key]='../.device-config/'+filename
 # Optional usage aggregates are staged too, so cron never follows a Documents path.
 if config.get('deepseek_usage_file'):
  src=(SOURCE/config['deepseek_usage_file']).resolve()
  target=runtime/'.device-config/deepseek-usage.json';shutil.copyfile(src,target);target.chmod(0o600)
  config['deepseek_usage_file']='../.device-config/deepseek-usage.json'
 (runtime/'report/config.local.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
 (runtime/'report/config.local.json').chmod(0o600)
 # Keep the last report for cache fallback on the initial scheduled run.
 if (SOURCE/'output').is_dir() and not (runtime/'report/output').exists():
  shutil.copytree(SOURCE/'output',runtime/'report/output')
 python=runtime/'venv/bin/python3'
 if not python.exists():subprocess.run([sys.executable,'-m','venv',str(runtime/'venv')],check=True)
 if subprocess.run([str(python),'-c','import PIL,zoneinfo'],capture_output=True).returncode:
  subprocess.run([str(python),'-m','pip','install','-r',str(runtime/'report/requirements.txt')],check=True)
 # Match cron's environment: no shell profile, IDE state, or SSH agent environment.
 env={'HOME':str(Path.home()),'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','USER':os.environ.get('USER','lance'),'LOGNAME':os.environ.get('LOGNAME','lance'),'SHELL':'/bin/sh'}
 runner=runtime/'report/daily-report.sh'
 subprocess.run(['/bin/sh',str(runner)],cwd='/',env=env,check=True)
 existing=read_crontab();updated=render_crontab(existing,runner)
 backup=PROJECT/'.device-config/cron-backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S.txt')
 backup.parent.mkdir(parents=True,exist_ok=True);backup.write_text(existing);backup.chmod(0o600)
 if read_crontab()!=existing:raise ValueError('crontab 被其他程序修改，请重新安装')
 if updated!=existing:
  subprocess.run(['/usr/bin/crontab','-'],input=updated,text=True,check=True)
 if read_crontab()!=updated:raise ValueError('crontab 写入后的校验未通过')
 print('已安装并校验：每天日本时间 20:00，由本地 crontab 执行；真实最小环境试运行已成功。')
 if args.startup!='keep':subprocess.run([sys.executable,str(SOURCE/'install_startup.py'),'--enable' if args.startup=='login' else '--disable'],check=True)
 print('Runtime: '+str(runtime))
 print('Log: '+str(runtime/'logs/daily-report.log'))
if __name__=='__main__':
 try:main()
 except Exception as e:
  print('安装未完成：'+(str(e) if isinstance(e,ValueError) else type(e).__name__),file=sys.stderr);sys.exit(1)
