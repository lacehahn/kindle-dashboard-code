import importlib.util,json,tempfile,subprocess,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('report_run',Path(__file__).with_name('run.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ReportTests(unittest.TestCase):
 def test_codex_only_aggregates(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'x.jsonl';p.write_text(json.dumps({'type':'event_msg','timestamp':'2026-11-08T10:00:00Z','payload':{'type':'token_count','secret':'NEVER_PUBLISH','rate_limits':{'primary':{'used_percent':38,'resets_at':123},'secondary':{'used_percent':6,'resets_at':456}}}})+'\n')
   r=m.codex({'codex_sessions':tmp});self.assertEqual(r['five_hour']['used_percent'],38);self.assertNotIn('NEVER_PUBLISH',json.dumps(r))
 def test_balance_does_not_invent_spending(self):
  with patch.dict(m.os.environ,{'DEEPSEEK_API_KEY':'PRIVATE_KEY'}),patch.object(m,'fetch',return_value={'balance_infos':[{'currency':'CNY','total_balance':'482.36'}]}):
   r=m.deepseek({'secrets_file':'missing.json'});self.assertEqual(r['balance'],482.36);self.assertIsNone(r['spent']);self.assertIsNone(r['tokens']);self.assertNotIn('PRIVATE_KEY',json.dumps(r))
 def test_generated_json_native_roundtrip(self):
  file=m.OUT/'report.json';r=json.loads(file.read_text());self.assertEqual(r['schema_version'],1)
  decoded=subprocess.check_output([str(m.PROJECT/'.device-config/reportread-host'),str(file)],text=True).splitlines();self.assertEqual(decoded,r['commands'])
  portrait=subprocess.check_output([str(m.PROJECT/'.device-config/reportread-host'),str(file),'--portrait'],text=True).splitlines();self.assertEqual(portrait,r['portrait_commands'])
  stamp=subprocess.check_output([str(m.PROJECT/'.device-config/reportread-host'),str(file),'--stamp'],text=True).strip();self.assertEqual(stamp,''.join(c for c in r['generated_at'][:16] if c.isdigit()))
  epoch=subprocess.check_output([str(m.PROJECT/'.device-config/reportread-host'),str(file),'--epoch'],text=True).strip();self.assertEqual(int(epoch),r['generated_epoch'])
 def test_all_balance_currencies_retained(self):
  response={'is_available':True,'balance_infos':[{'currency':'CNY','total_balance':'12.34'},{'currency':'USD','total_balance':'2.00'}]}
  with patch.dict(m.os.environ,{'DEEPSEEK_API_KEY':'TEST_ONLY'}),patch.object(m,'fetch',return_value=response):
   r=m.deepseek({'secrets_file':'missing.json'});self.assertEqual(r['balances'],[{'currency':'CNY','balance':12.34},{'currency':'USD','balance':2.0}]);self.assertTrue(r['is_available']);self.assertNotIn('TEST_ONLY',json.dumps(r))
 def test_invalid_json_rejected(self):
  with tempfile.NamedTemporaryFile(mode='w') as f:
   f.write('{"schema_version":1,"commands":["I|0|0|0|0|/etc/passwd"]}');f.flush()
   self.assertNotEqual(subprocess.run([str(m.PROJECT/'.device-config/reportread-host'),f.name],capture_output=True).returncode,0)
 def test_private_mode_prevents_public_push(self):
  with self.assertRaisesRegex(ValueError,'隐私模式'):m.publish({'github_repository':'example/kindle-dashboard','publish_mode':'local_only'})
 def test_no_repository_no_push(self):
  with self.assertRaisesRegex(ValueError,'github_repository'):m.publish({'github_repository':''})
if __name__=='__main__':unittest.main()
