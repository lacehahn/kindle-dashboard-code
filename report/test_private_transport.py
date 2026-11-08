import importlib.util,json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
spec=importlib.util.spec_from_file_location('private_run',ROOT/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PrivateTransport(unittest.TestCase):
 def test_repository_gate(self):
  c={'github_repository':'example/private-report'}
  for private,pages,ok in [(True,False,True),(False,False,False),(True,True,False),(True,None,False)]:
   with patch.object(m,'read_github_token',return_value='DUMMY_TOKEN'),patch.object(m,'fetch',return_value={'private':private,'has_pages':pages,'full_name':c['github_repository']}):
    if ok:self.assertEqual(m.verify_private_repo(c),c['github_repository'])
    else:
     with self.assertRaises(ValueError):m.verify_private_repo(c)
 def test_raw_json_png_and_atomic_cache(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);device=root/'device';device.mkdir();(device/'report-auth.conf').write_text('header="Authorization: Bearer NEVER_EXPOSE_TOKEN"\n')
   source=root/'remote';shutil.copytree(ROOT/'output',source)
   parser=root/'bin';parser.mkdir();shutil.copyfile(PROJECT/'.device-config/reportread-host',parser/'reportread');(parser/'reportread').chmod(0o755)
   commands=root/'tools';commands.mkdir();curl=commands/'curl'
   curl.write_text('''#!/usr/bin/env python3
import sys,os,json,urllib.parse
from pathlib import Path
a=sys.argv[1:]
with open(os.environ['ARGS'],'a') as f:f.write(json.dumps(a)+'\\n')
url=next(v for v in a if v.startswith('https://'));out=Path(a[a.index('-o')+1]);name=Path(urllib.parse.urlparse(url).path).name
src=Path(os.environ['REMOTE'])/('report.json' if name=='report.json' else 'assets/'+name)
if not src.exists():sys.exit(22)
out.write_bytes(src.read_bytes())
''');curl.chmod(0o755)
   lib=root/'download.sh';lib.write_text((PROJECT/'kindle/extensions/dashboard/bin/report-download.sh').read_text())
   env=dict(os.environ,PATH=str(commands)+':'+os.environ['PATH'],DASH_DIR=str(root),REPORT_ROOT=str(device),SCRIPT=str(lib),REMOTE=str(source),ARGS=str(root/'args'))
   harness='. "$SCRIPT"\nREPORT_REPOSITORY=example/private-report\nREPORT_REF=reports\nreport_download\n'
   def download():return subprocess.run(['sh'],input=harness,text=True,env=env,capture_output=True)
   result=download();self.assertEqual(result.returncode,0,result.stderr)
   pointer=(device/'report-current').read_text();cache=device/'report-cache'/pointer.strip()
   original=json.loads((source/'report.json').read_text());self.assertEqual(json.loads((cache/'report.json').read_text()),original)
   for p in (cache/'assets').iterdir():self.assertEqual(p.read_bytes(),(source/'assets'/p.name).read_bytes())
   self.assertNotIn('NEVER_EXPOSE_TOKEN',(root/'args').read_text())
   # Default GitHub metadata JSON must not be mistaken for raw JSON report.
   (source/'report.json').write_text('{"content":"BASE64_METADATA_NOT_A_REPORT"}')
   self.assertNotEqual(download().returncode,0);self.assertEqual((device/'report-current').read_text(),pointer)
   (source/'report.json').write_text(json.dumps(original,ensure_ascii=False))
   (source/'assets/today.png').write_bytes(b'CORRUPTED_PNG')
   self.assertNotEqual(download().returncode,0);self.assertEqual((device/'report-current').read_text(),pointer)
   (source/'assets/today.png').unlink()
   self.assertNotEqual(download().returncode,0);self.assertEqual((device/'report-current').read_text(),pointer)
   self.assertEqual(json.loads((cache/'report.json').read_text()),original)
if __name__=='__main__':unittest.main()
