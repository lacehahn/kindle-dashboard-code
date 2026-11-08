#!/usr/bin/env python3
"""Local report generation. Only explicit aggregates enter the private report."""
import argparse,calendar,datetime as dt,json,os,re,shutil,subprocess,sys,urllib.request,urllib.parse,fcntl,hashlib
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent; PROJECT=ROOT.parent; OUT=ROOT/'output'
def fetch(url,key=None):
 headers={'User-Agent':'InkDesk/2'}
 if key:headers['Authorization']='Bearer '+key
 with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=20) as r:return json.load(r)
def codex(config):
 latest=None
 folder=Path(config['codex_sessions']).expanduser()
 for p in sorted(folder.rglob('*.jsonl'),key=lambda p:p.stat().st_mtime,reverse=True)[:30]:
  with p.open('rb') as f:
   if p.stat().st_size>4_000_000:f.seek(-4_000_000,2);f.readline()
   for line in f:
    try:j=json.loads(line)
    except (ValueError,UnicodeDecodeError):continue
    payload=j.get('payload',{})
    rates=payload.get('rate_limits') if j.get('type')=='event_msg' and payload.get('type')=='token_count' else None
    if rates and rates.get('primary') and rates.get('secondary'):
     stamp=j.get('timestamp','')
     if not latest or stamp>latest['as_of']:
      latest={'as_of':stamp,'source':'local_session_snapshot','status':'snapshot'}
      for name,field in [('five_hour','primary'),('week','secondary')]:
       r=rates[field];v=float(r['used_percent'])
       if not 0<=v<=100:raise ValueError('invalid quota percentage')
       latest[name]={'used_percent':v,'resets_at':r.get('resets_at')}
 return latest or {'status':'unconfigured'}
def weather(c):
 q=urllib.parse.urlencode(dict(latitude=c['latitude'],longitude=c['longitude'],timezone=c['timezone'],forecast_days=4,current='temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m',daily='temperature_2m_max,temperature_2m_min,weather_code',wind_speed_unit='ms'))
 j=fetch('https://api.open-meteo.com/v1/forecast?'+q); cur=j['current'];daily=j['daily']
 return {'status':'ok','as_of':cur['time'],'temperature':cur['temperature_2m'],'humidity':cur['relative_humidity_2m'],'wind':cur['wind_speed_10m'],'code':cur['weather_code'],'high':daily['temperature_2m_max'][0],'low':daily['temperature_2m_min'][0],'forecast':[{'date':daily['time'][i],'code':daily['weather_code'][i],'high':daily['temperature_2m_max'][i],'low':daily['temperature_2m_min'][i]} for i in range(1,4)]}
def deepseek(c):
 result={'status':'unconfigured','balance':None,'currency':None,'balances':[],'is_available':None,'spent':None,'tokens':None}
 secretpath=(ROOT/c['secrets_file']).resolve()
 secrets=json.loads(secretpath.read_text()) if secretpath.is_file() else {}
 key=os.environ.get('DEEPSEEK_API_KEY') or secrets.get('DEEPSEEK_API_KEY')
 if key:
  j=fetch('https://api.deepseek.com/user/balance',key)
  balances=[]
  for info in j['balance_infos']:
   amount=float(info['total_balance']);currency=info['currency']
   if not -float('inf')<amount<float('inf') or not isinstance(currency,str) or not currency.isalpha():raise ValueError('invalid balance')
   balances.append({'currency':currency,'balance':amount})
  if not balances:raise ValueError('empty balance response')
  result.update(status='ok',balances=balances,is_available=j.get('is_available'),balance=balances[0]['balance'],currency=balances[0]['currency'])
 return result
def token(code):
 if code==0:return 'clear','晴'
 if code in [1,2]:return 'partly','多云'
 if code==3:return 'cloud','阴'
 if code in [45,48]:return 'fog','雾'
 if code in [71,73,75,77,85,86]:return 'snow','雪'
 return 'rain','雨'
def lunar(day):
 key=day.strftime('%Y%m%d'); rows=(PROJECT/'kindle/dashboard/lunar.dat').read_text().splitlines()
 row=next((s.split('|') for s in rows if s.startswith(key+'|')),None)
 terms=[s.split('|') for s in (PROJECT/'kindle/dashboard/terms.dat').read_text().splitlines()]
 before=[r for r in terms if r[0]<=key];after=[r for r in terms if r[0]>key]
 nxt=after[0] if after else None
 return {'date':row[1] if row else '未配置','year':row[2] if row else '未配置','term':before[-1][1] if before else '未配置','next_term':nxt[1] if nxt else None,'days_to_next':(dt.datetime.strptime(nxt[0],'%Y%m%d').date()-day).days if nxt else None}
def layout(r):
 sys.path.insert(0,str(ROOT))
 from layouts import build_layouts
 landscape,portrait=build_layouts(r,OUT,PROJECT)
 r['portrait_commands']=portrait
 return landscape

def read_github_token(c):
 path=(ROOT/c.get('github_token_file','../.device-config/github-read-token')).resolve()
 token=path.read_text().strip() if path.is_file() else ''
 if not re.fullmatch(r'[A-Za-z0-9_]+',token):raise ValueError('请在本机 .device-config/github-read-token 中填写 GitHub 只读令牌')
 return token

def verify_private_repo(c):
 repo=c.get('github_repository','')
 if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):raise ValueError('请配置 github_repository：用户名/仓库名')
 token=read_github_token(c)
 info=fetch('https://api.github.com/repos/'+repo,token)
 if info.get('private') is not True:raise ValueError('目标仓库不是私有仓库，拒绝上传')
 if info.get('has_pages') is not False:raise ValueError('请先关闭目标仓库的 GitHub Pages，再上传私有报告')
 if info.get('full_name','').lower()!=repo.lower():raise ValueError('仓库身份不匹配')
 return repo

def publish(c):
 if not c.get('github_repository'):raise ValueError('请配置 github_repository：用户名/仓库名')
 if c.get('publish_mode','local_only')!='private_repository':raise ValueError('隐私模式：只允许上传到已验证的私有仓库，不允许 Pages 发布')
 repo=verify_private_repo(c)
 branch=c.get('github_branch','reports')
 if not re.fullmatch(r'[A-Za-z0-9_-]+',branch):raise ValueError('invalid report branch')
 work=PROJECT/'.device-config/private-report-checkout';work.mkdir(parents=True,exist_ok=True)
 def git(*args,check=True):return subprocess.run(['git',*args],cwd=work,check=check,capture_output=True,text=True,timeout=90,env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=15'))
 if not (work/'.git').exists():
  git('init');git('remote','add','origin','git@github.com:'+repo+'.git')
 if git('remote','get-url','origin').stdout.strip()!='git@github.com:'+repo+'.git':raise ValueError('私有工作区与配置仓库不符')
 remote=git('ls-remote','--heads','origin',branch)
 if remote.stdout.strip():git('fetch','origin',branch);git('checkout','-B',branch,'FETCH_HEAD')
 else:git('symbolic-ref','HEAD','refs/heads/'+branch)
 report=json.loads((OUT/'report.json').read_text())
 bundle='bundles/'+report['asset_bundle']
 shutil.copytree(OUT/'assets',work/bundle,dirs_exist_ok=True)
 shutil.copyfile(OUT/'report.json',work/'report.json')
 git('add','--','report.json',bundle)
 if git('diff','--cached','--quiet',check=False).returncode:
  git('-c','user.name=InkDesk','-c','user.email=inkdesk@localhost','commit','-m','Update private daily report')
 # Check again immediately before pushing; never deliberately push to public repos.
 verify_private_repo(c)
 git('push','origin',branch)
 print('已上传私有报告到 '+repo+' / '+branch+'，未启用 Pages。')

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--publish',action='store_true');parser.add_argument('--config',default=str(ROOT/'config.local.json'));args=parser.parse_args()
 c=json.loads(Path(args.config).read_text());OUT.mkdir(exist_ok=True)
 now=dt.datetime.now(ZoneInfo(c['timezone']));old=json.loads((OUT/'report.json').read_text()) if (OUT/'report.json').exists() else {}
 r={'schema_version':1,'generated_at':now.isoformat(),'generated_epoch':int(now.timestamp()),'date':now.date().isoformat(),'timezone':c['timezone'],'city':c['city'],'canvas':{'width':1448,'height':1072},'lunar':lunar(now.date()),'errors':[]}
 for name,reader in [('weather',weather),('codex',codex),('deepseek',deepseek)]:
  try:r[name]=reader(c)
  except Exception:
   r['errors'].append(name+' 数据源不可用')
   if name in old:r[name]=dict(old[name],status='stale')
   else:r[name]={'status':'unconfigured','balance':None,'currency':None,'spent':None,'tokens':None,'week_spent':None}
 r['commands']=layout(r)
 r['assets']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((OUT/'assets').glob('*.png'))}
 r['asset_bundle']=hashlib.sha256(json.dumps(r['assets'],sort_keys=True).encode()).hexdigest()
 temp=OUT/'report.json.tmp';temp.write_text(json.dumps(r,ensure_ascii=False,allow_nan=False,indent=2));temp.replace(OUT/'report.json')
 for p in (ROOT/'site').iterdir():shutil.copyfile(p,OUT/p.name)
 (OUT/'.nojekyll').touch()
 print('已生成 report/output/report.json；未配置或失败的数据不会伪造。')
 if args.publish:publish(c)
if __name__=='__main__':
 try:
  lockdir=PROJECT/'.device-config';lockdir.mkdir(exist_ok=True)
  with (lockdir/'report-run.lock').open('w') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   main()
 except BlockingIOError:
  print('已有报告任务运行，本次跳过。')
  sys.exit(0)
 except Exception as e:
  print('执行未完成：'+(str(e) if isinstance(e,ValueError) else type(e).__name__),file=sys.stderr);sys.exit(1)
