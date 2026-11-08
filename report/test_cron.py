import importlib.util,shlex,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('cron_installer',Path(__file__).with_name('install_cron.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CronTests(unittest.TestCase):
 def test_preserves_existing_jobs_and_is_idempotent(self):
  existing='MAILTO=user@example.com\n5 3 * * * /usr/bin/true\n'
  path=Path('/Users/example/Library/Application Support/InkDesk/report/daily-report.sh')
  result=m.render_crontab(existing,path)
  self.assertTrue(result.startswith(existing.rstrip()+'\n\n'))
  self.assertEqual(m.render_crontab(result,path),result)
  entry=next(l for l in result.splitlines() if l.startswith('0 20 '))
  self.assertEqual(shlex.split(entry.split(' ',5)[5]),['/bin/sh',str(path)])
 def test_only_replaces_owned_entry(self):
  old='1 1 * * * first\n'+m.BEGIN+'\n0 20 * * * old\n'+m.END+'\n2 2 * * * last\n'
  result=m.render_crontab(old,Path('/tmp/new.sh'))
  self.assertIn('1 1 * * * first',result);self.assertIn('2 2 * * * last',result)
  self.assertNotIn('* old',result);self.assertEqual(result.count(m.BEGIN),1)
 def test_malformed_markers_are_not_overwritten(self):
  with self.assertRaises(ValueError):m.render_crontab(m.BEGIN+'\nbroken\n',Path('/tmp/a.sh'))
if __name__=='__main__':unittest.main()
