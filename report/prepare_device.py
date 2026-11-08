"""Configure the connected Kindle without displaying or publishing its read-only token."""
import json,re,shlex,sys
from pathlib import Path
from run import ROOT,read_github_token,verify_private_repo
c=json.loads((ROOT/'config.local.json').read_text())
try:
 repo=verify_private_repo(c);token=read_github_token(c)
 branch=c.get('github_branch','reports')
 if not re.fullmatch(r'[A-Za-z0-9_-]+',branch):raise ValueError('invalid branch')
 device=Path('/Volumes/Kindle/dashboard')
 if not device.is_dir():raise ValueError('请将 Kindle 接入 USB 磁盘模式')
 conf=device/'report.conf';auth=device/'report-auth.conf'
 conf.write_text('REPORT_REPOSITORY='+shlex.quote(repo)+'\nREPORT_REF='+shlex.quote(branch)+'\n')
 auth.write_text('header = "Authorization: Bearer '+token+'"\nheader = "Accept: application/vnd.github.raw+json"\nproto = "=https"\n')
 auth.chmod(0o600);conf.chmod(0o600)
 print('Kindle 私有仓库读取已配置；未输出或上传令牌。')
except Exception as e:
 print('配置未完成：'+(str(e) if isinstance(e,ValueError) else type(e).__name__),file=sys.stderr);sys.exit(1)
