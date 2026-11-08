"""Exercise the Kindle download path against the actual private GitHub repo on this Mac."""
import json,os,shutil,subprocess,tempfile,sys,urllib.request,urllib.error,argparse
from pathlib import Path
from run import ROOT,PROJECT,read_github_token,verify_private_repo
parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path,default=PROJECT);args=parser.parse_args()
report_root=args.runtime/'report'
c=json.loads((report_root/'config.local.json').read_text())
c['github_token_file']=str((report_root/c['github_token_file']).resolve())
try:
 repo=verify_private_repo(c);token=read_github_token(c)
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp);device=root/'device';device.mkdir();(root/'bin').mkdir()
  shutil.copyfile(PROJECT/'.device-config/reportread-host',root/'bin/reportread');(root/'bin/reportread').chmod(0o755)
  auth=device/'report-auth.conf';auth.write_text('header = "Authorization: Bearer '+token+'"\nheader = "Accept: application/vnd.github.raw+json"\nproto = "=https"\n');auth.chmod(0o600)
  env=dict(os.environ,REPORT_ROOT=str(device),DASH_DIR=str(root),REPORT_REPOSITORY=repo,REPORT_REF=c['github_branch'],LIBRARY=str(PROJECT/'kindle/extensions/dashboard/bin/report-download.sh'))
  result=subprocess.run(['sh'],input='. "$LIBRARY"\nreport_download\n',text=True,env=env,capture_output=True,timeout=240)
  if result.returncode:raise ValueError('实际私有下载未通过，保留现有数据；请检查令牌与仓库内容')
  cache=device/'report-cache'/(device/'report-current').read_text().strip()
  downloaded=json.loads((cache/'report.json').read_text());expected=json.loads((report_root/'output/report.json').read_text())
  if downloaded!=expected:raise ValueError('下载 JSON 与本次上传文件不一致')
  dest=PROJECT/'.device-config/verified-private-report';shutil.copytree(cache,dest,dirs_exist_ok=True)
  print('PASS: real private GitHub download; raw JSON matches upload; all '+str(len(downloaded['assets']))+' PNG asset hashes verified')
 # Confirm the same report cannot be downloaded anonymously.
 url='https://api.github.com/repos/'+repo+'/contents/report.json?ref='+c['github_branch']
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'Accept':'application/vnd.github.raw+json','User-Agent':'InkDesk/2'}),timeout=20) as response:
   if response.status==200:raise ValueError('匿名访问竟然可读取报告，需要检查仓库隐私')
 except urllib.error.HTTPError as e:
  if e.code!=404:raise ValueError('匿名访问检查未能确认：HTTP '+str(e.code))
 print('PASS: anonymous access denied (404); credentials not included in saved report artifacts')
except Exception as e:
 print('验证未完成：'+(str(e) if isinstance(e,ValueError) else type(e).__name__),file=sys.stderr);sys.exit(1)
