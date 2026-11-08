"""Generate native 1072×1448 monochrome assets; requires Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math
ROOT = Path(__file__).parent / 'dashboard'
ROOT.mkdir(exist_ok=True)
im=Image.new('L',(1072,1448),255); d=ImageDraw.Draw(im)
for box in [(18,16,1054,409),(18,426,1054,1041),(18,1061,1054,1428)]:
 d.rounded_rectangle(box,20,outline=0,width=3)
for line in [(552,42,552,382),(582,296,1020,296),(52,514,1020,514),(52,918,1020,918),(514,936,514,1012),(371,1148,371,1389),(703,1148,703,1389)]: d.line(line,fill=0,width=2)
im.save(ROOT/'bg_page.png')
# Outlined weather symbols are raster assets rather than font-dependent glyphs.
def icon(name):
 im=Image.new('L',(160,160),255); d=ImageDraw.Draw(im)
 if name in ('clear','partly'):
  cx,cy,r=(80,77,32) if name=='clear' else (103,49,27)
  for a in range(0,360,45):
   q=math.radians(a);d.line((cx+math.cos(q)*(r+12),cy+math.sin(q)*(r+12),cx+math.cos(q)*(r+26),cy+math.sin(q)*(r+26)),fill=0,width=6)
  d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=255,outline=0,width=6)
 if name!='clear':
  d.ellipse((17,67,76,125),fill=255,outline=0,width=6)
  d.ellipse((48,40,113,111),fill=255,outline=0,width=6)
  d.ellipse((88,68,143,125),fill=255,outline=0,width=6)
  d.rectangle((45,80,117,122),fill=255);d.line((44,124,116,124),fill=0,width=6)
 if name=='rain':
  for x in [45,80,115]: d.line((x,135,x-6,151),fill=0,width=5)
 if name=='snow':
  for x in [45,80,115]:
   d.line((x-6,142,x+6,142),fill=0,width=3);d.line((x,136,x,148),fill=0,width=3)
 if name=='fog':
  for y in [137,150]: d.line((24,y,138,y),fill=0,width=4)
 im.save(ROOT/'icons'/f'{name}.png')
for name in ['clear','partly','cloud','rain','snow','fog']:icon(name)
im=Image.new('L',(64,64),255);ImageDraw.Draw(im).ellipse((1,1,63,63),fill=0);im.save(ROOT/'icons/ui/circle.png')

# Use the device's exact font; fallback to a private local backup when disconnected.
fonts = [Path('/Volumes/Kindle/dashboard/fonts/cjk-bold.ttf')]
fonts += sorted((ROOT.parent.parent/'.device-config/kindle-backups').glob('*/dashboard/fonts/cjk-bold.ttf'))
font_path = next((p for p in fonts if p.is_file()), None)
if font_path is None:
 raise SystemExit('Connect Kindle once to generate date badges with its font.')
font=ImageFont.truetype(str(font_path),38)
for day in range(1,32):
 badge=Image.new('L',(56,56),255);draw=ImageDraw.Draw(badge)
 draw.ellipse((1,1,54,54),fill=0)
 box=draw.textbbox((0,0),str(day),font=font)
 draw.text(((56-(box[2]-box[0]))/2-box[0],(56-(box[3]-box[1]))/2-box[1]),str(day),font=font,fill=255)
 badge.save(ROOT/'icons/ui'/f'day-{day}.png')

im=Image.new('L',(1448,1072),255);d=ImageDraw.Draw(im)
for box in [(18,16,702,700),(720,16,1430,700),(18,720,1430,1054)]:
 d.rounded_rectangle(box,20,outline=0,width=3)
for line in [(54,424,666,424),(54,594,666,594),(750,104,1400,104),(750,550,1400,550),(1070,574,1070,674),(510,804,510,1024),(976,804,976,1024)]:
 d.line(line,fill=0,width=2)
im.save(ROOT/'bg_landscape.png')
