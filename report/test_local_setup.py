import contextlib,importlib.util,io,json,stat,tempfile,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
def load(name):
 spec=importlib.util.spec_from_file_location(name,HERE/(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
startup=load('install_startup');deepseek=load('configure_deepseek')
class LocalSetupTests(unittest.TestCase):
 def test_login_agent_runs_once_and_does_not_duplicate_daily_timer(self):
  config=startup.make_plist(Path('/Users/example/Library/Application Support/InkDesk'))
  self.assertTrue(config['RunAtLoad']);self.assertNotIn('KeepAlive',config)
  self.assertNotIn('StartInterval',config);self.assertNotIn('StartCalendarInterval',config)
  self.assertEqual(config['ProgramArguments'][0],'/bin/sh')
 def test_key_is_saved_privately_to_both_configs_without_echo(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'project/report';source.mkdir(parents=True)
   (source/'config.local.json').write_text(json.dumps({'secrets_file':'../.device-config/report-secrets.json'}))
   home=root/'home';runtime=home/'Library/Application Support/InkDesk/report';runtime.mkdir(parents=True)
   (runtime/'config.local.json').write_text(json.dumps({'secrets_file':'../.device-config/report-secrets.json'}))
   data=io.StringIO(json.dumps({'balance_infos':[{'currency':'CNY','total_balance':'3.14'}]}));output=io.StringIO()
   with patch.object(deepseek,'ROOT',source),patch.object(Path,'home',return_value=home),patch.object(deepseek.getpass,'getpass',return_value='sk-LOCAL_TEST_SECRET'),patch.object(deepseek.urllib.request,'urlopen',return_value=data),contextlib.redirect_stdout(output):deepseek.main()
   self.assertNotIn('sk-LOCAL_TEST_SECRET',output.getvalue())
   for file in [source.parent/'.device-config/report-secrets.json',runtime.parent/'.device-config/report-secrets.json']:
    self.assertEqual(json.loads(file.read_text())['DEEPSEEK_API_KEY'],'sk-LOCAL_TEST_SECRET')
    self.assertEqual(stat.S_IMODE(file.stat().st_mode),0o600)
 def test_failed_api_validation_does_not_write_secret(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   error=urllib.error.HTTPError('https://api.deepseek.com/user/balance',401,'Unauthorized',{},None)
   with patch.object(deepseek,'ROOT',root),patch.object(deepseek.getpass,'getpass',return_value='sk-NO_SAVE'),patch.object(deepseek.urllib.request,'urlopen',side_effect=error):
    with self.assertRaises(urllib.error.HTTPError):deepseek.main()
   self.assertEqual(list(root.iterdir()),[])
if __name__=='__main__':unittest.main()
