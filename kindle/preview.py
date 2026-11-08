"""Preview the actual C raster backend with sample weather, without a Kindle runtime."""
from pathlib import Path
import subprocess, tempfile, os, sys
from PIL import Image
root=Path(__file__).resolve().parent
landscape='--landscape' in sys.argv
mode='landscape' if landscape else 'portrait'
font=next(p for p in [Path('/Volumes/Kindle/dashboard/fonts/cjk-bold.ttf'),*sorted((root.parent/'.device-config/kindle-backups').glob('*/dashboard/fonts/cjk-bold.ttf'))] if p.is_file())
source=(root/'extensions/dashboard/bin/clock.sh').read_text()
functions=source[source.index('ri()'):source.index('# Render both layouts')]
a=functions.index('weather_line()');b=functions.index('# ---- 卡片 1',a)
functions=functions[:a]+functions[b:]
if landscape:functions+='\n'+(root/'extensions/dashboard/bin/landscape.sh').read_text()
functions=functions.replace('"$DASH_DIR/bin/weather.sh" cn "$tok"','sample_cn "$tok"').replace('"$DASH_DIR/bin/weather.sh" forecast 2>/dev/null',"printf '明天 11/09|clear|21|13\\n后天 11/10|partly|22|14\\n大后天 11/11|cloud|19|15\\n'")
functions=functions.replace('"$DASH_DIR/bin/lunar.sh" gz','echo 丙午').replace('"$DASH_DIR/bin/lunar.sh"','echo 九月三十').replace('"$DASH_DIR/bin/terms.sh" now','echo 立冬').replace('"$DASH_DIR/bin/terms.sh" next',"echo '小雪 14'")
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp)
 harness='''. "$DASH_DIR/bin/ui.sh"
. "$DASH_DIR/bin/calendar.sh"
FONT=x; CITY=东京; M=44
sample_cn() { case "$1" in clear) echo 晴;; partly) echo 多云;; *) echo 阴;; esac; }
weather_line() { echo 'PARTLY CLOUDY|18|68|3|21|12|14:50|partly|partly'; }
'''+functions+'''
. "$DASH_DIR/bin/raster.sh"
FBINK=true
LOG=/dev/null
'''
 env=dict(os.environ,DASH_LAYOUT='portrait',DASH_DIR=str(root/'extensions/dashboard'))
 # Font and paths are shell-quoted even though these are controlled local files.
 import shlex
 def assign(key,value):return key+'='+shlex.quote(str(value))+'\n'
 for key,value in dict(FONT_BOLD=font,RENDER=root.parent/'.device-config/render-host',COMMANDS=t/'draw.txt',FRAME=t/'page.pgm',BG=root/'dashboard'/('bg_landscape.png' if landscape else 'bg_page.png'),ICONS=root/'dashboard/icons',DASH_LAYOUT=mode).items():
  harness+=assign(key,value)
 harness+='draw_page\nFRAME='+shlex.quote(str(t/'clock.pgm'))+'\nrender_begin\ndraw_time_digits\nrender_present 1\n'
 subprocess.run(['sh'],input=harness,text=True,env=env,check=True)
 full=Image.open(t/'page.pgm');clock=Image.open(t/'clock.pgm')
 assert full.size==(1072,1448),full.size
 rect=(156,768,400,1408) if landscape else (40,138,548,360)
 # Partial minute updates must produce the exact pixels shown on the full page.
 assert full.crop(rect).tobytes()==clock.tobytes(),'Clock crop does not match full page'
 if landscape:full=full.transpose(Image.Transpose.ROTATE_270)
 output=root/('preview-landscape.png' if landscape else 'preview.png');full.save(output)
 print(f'PASS: {mode} native raster and clock crop; preview: {output}')
