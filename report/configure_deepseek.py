#!/usr/bin/env python3
"""Prompt locally (hidden), verify the balance API, and save only local secret files."""
import getpass,json,os,re,sys,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def save_secret(path,key):
 path.parent.mkdir(parents=True,exist_ok=True)
 data=json.loads(path.read_text()) if path.is_file() else {}
 data['DEEPSEEK_API_KEY']=key
 # Mode 600 on the temporary file before writing any key material.
 temp=path.with_name(path.name+'.tmp')
 fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 try:
  os.fchmod(fd,0o600)
  with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
  temp.replace(path);path.chmod(0o600)
 finally:
  temp.unlink(missing_ok=True)
def main():
 key=getpass.getpass('DeepSeek API Key（输入不会显示）: ').strip()
 if not re.fullmatch(r'[A-Za-z0-9_-]+',key):raise ValueError('Key 格式无效，未保存')
 request=urllib.request.Request('https://api.deepseek.com/user/balance',headers={'Authorization':'Bearer '+key,'User-Agent':'InkDesk/2'})
 with urllib.request.urlopen(request,timeout=20) as r:data=json.load(r)
 if not data.get('balance_infos'):raise ValueError('余额接口未返回预期数据，未保存')
 config=json.loads((ROOT/'config.local.json').read_text())
 targets=[(ROOT/config['secrets_file']).resolve()]
 runtime=Path.home()/'Library/Application Support/InkDesk/report/config.local.json'
 if runtime.is_file():
  c=json.loads(runtime.read_text());targets.append((runtime.parent/c['secrets_file']).resolve())
 for target in set(targets):save_secret(target,key)
 print('余额接口验证通过。Key 已保存到本地项目和已安装的定时任务配置；未显示或上传 Key。')
 print('各币种剩余余额将在下次报告更新时自动获取，不做汇率换算。')
if __name__=='__main__':
 try:main()
 except urllib.error.HTTPError as e:
  print('验证失败：HTTP '+str(e.code)+'，未保存 Key。',file=sys.stderr);sys.exit(1)
 except Exception as e:
  print('配置未完成：'+(str(e) if isinstance(e,ValueError) else type(e).__name__),file=sys.stderr);sys.exit(1)
