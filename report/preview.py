"""Render the actual Kindle report controller with real downloaded/generated JSON."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse,subprocess,json,shutil,tempfile,shlex
from PIL import Image
root=Path(__file__).resolve().parent;project=root.parent
parser=argparse.ArgumentParser();parser.add_argument('--portrait',action='store_true');parser.add_argument('--weather',type=Path);args=parser.parse_args()
r=json.loads((root/'output/report.json').read_text());portrait=args.portrait;mode='report-portrait' if portrait else 'report'
font=next(p for p in [Path('/Volumes/Kindle/dashboard/fonts/cjk-bold.ttf'),*sorted((project/'.device-config/kindle-backups').glob('*/dashboard/fonts/cjk-bold.ttf'))] if p.is_file())
with tempfile.TemporaryDirectory() as tmp:
 base=Path(tmp);fixture=base/('a'*64);fixture.mkdir();shutil.copyfile(root/'output/report.json',fixture/'report.json');shutil.copytree(root/'output/assets',fixture/'assets')
 (base/'bin').mkdir()
 for name,data in [('lunar.sh','lunar.dat'),('terms.sh','terms.dat')]:
  text=(project/'kindle/extensions/dashboard/bin'/name).read_text().replace('/mnt/us/dashboard/'+data,str(project/'kindle/dashboard'/data))
  file=base/'bin'/name;file.write_text(text);file.chmod(0o755)
 code=(project/'kindle/extensions/dashboard/bin/report-layout.sh').read_text()
 code=code.replace('. "$DASH_DIR/bin/report-download.sh"',':')
 code=code.replace('. "$DASH_DIR/bin/report-weather.sh"', (project/'kindle/extensions/dashboard/bin/report-weather.sh').read_text())
 code=code.replace('cat /mnt/us/dashboard/report-current 2>/dev/null',"printf '"+'a'*64+"'")
 code=code.replace('current=/mnt/us/dashboard/report-cache/$id','current='+shlex.quote(str(base))+'/$id')
 code=code.replace('"$DASH_DIR/bin/reportread"','"$REPORTREAD_HOST"')
 def assign(k,v):return k+'='+shlex.quote(str(v))+'\n'
 harness=''
 for k,v in dict(DASH_LAYOUT=mode,DASH_DIR=base,REPORTREAD_HOST=project/'.device-config/reportread-host').items():harness+=assign(k,v)
 harness+='. '+shlex.quote(str(project/'kindle/extensions/dashboard/bin/raster.sh'))+'\n'
 harness+='. '+shlex.quote(str(project/'kindle/extensions/dashboard/bin/calendar.sh'))+'\n'+code+'\n'
 for k,v in dict(RENDER=project/'.device-config/render-host',FRAME=base/'page.pgm',COMMANDS=base/'commands.txt',REPORT_COMMANDS=base/'report-commands.txt',FONT_BOLD=font,FBINK='true',ICONS=project/'kindle/dashboard/icons',CLOCK_TEXT=datetime.now(ZoneInfo(r['timezone'])).strftime('%H:%M'),BATTERY_LEVEL='',LOG=base/'log').items():harness+=assign(k,v)
 if args.weather:harness+=assign('WEATHER_CACHE',args.weather.resolve())
 harness+='draw_page\n'
 import os
 subprocess.run(['sh'],input=harness,text=True,check=True,env=dict(os.environ,TZ=r['timezone']))
 im=Image.open(base/'page.pgm');assert im.size==(1072,1448)
 if not portrait:im=im.transpose(Image.Transpose.ROTATE_270)
 output=root/('preview-portrait.png' if portrait else 'preview.png');im.save(output);print(output)
