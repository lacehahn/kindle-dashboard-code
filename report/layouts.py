"""Shared report layouts, expressed as native raster commands for both orientations."""
import calendar,datetime as dt,shutil
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image,ImageDraw,ImageFont
CLOCKS={'landscape':{'width':1448,'height':1072,'size':220,'top':68,'left':58,'battery_size':24,'battery_top':34,'battery_left':482,'battery_x':612,'battery_y':42,'battery_w':40,'battery_h':24},
        'portrait':{'width':1072,'height':1448,'size':190,'top':0,'left':280,'battery_size':28,'battery_top':24,'battery_left':800,'battery_x':964,'battery_y':34,'battery_w':52,'battery_h':28}}
def build_layouts(r,out,project):
 assets=out/'assets';assets.mkdir(exist_ok=True)
 for file in assets.glob('*.png'):file.unlink()
 for file in (project/'kindle/dashboard/icons').glob('*.png'):shutil.copyfile(file,assets/file.name)
 for name in ['codex','deepseek']:shutil.copyfile(project/'report/brand'/(name+'.png'),assets/(name+'.png'))
 fontfile=next(p for p in [Path('/Volumes/Kindle/dashboard/fonts/cjk-bold.ttf'),*sorted((project/'.device-config/kindle-backups').glob('*/dashboard/fonts/cjk-bold.ttf'))] if p.is_file())
 def font(size):return ImageFont.truetype(str(fontfile),size)
 day=dt.date.fromisoformat(r['date']);l=r['lunar'];weather=r['weather'];codex=r['codex'];deep=r['deepseek']
 week=codex.get('week',{});percent=week.get('used_percent')
 stamp=codex.get('as_of');sample=dt.datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(ZoneInfo(r['timezone'])) if stamp else None
 updated=sample.strftime('%H:%M') if sample and sample.date()==day else sample.strftime('%m-%d') if sample else '未配置'
 reset=week.get('resets_at');reset_text=dt.datetime.fromtimestamp(reset,ZoneInfo(r['timezone'])).strftime('%m月%d日 %H:%M') if reset else '未配置'
 usage='已用 -- / 剩余 --' if percent is None else f'已用 {percent:g}% / 剩余 {100-percent:g}%'
 money_symbol={'CNY':'¥','USD':'$'}.get(deep.get('currency'),'')
 def money(value):return '未配置' if value is None else f'{money_symbol}{value:.2f}'
 def badge():
  im=Image.new('L',(44,44),255);d=ImageDraw.Draw(im);d.ellipse((0,0,43,43),fill=0);s=str(day.day);f=font(30);b=d.textbbox((0,0),s,font=f);d.text(((44-b[2]+b[0])/2-b[0],(44-b[3]+b[1])/2-b[1]),s,font=f,fill=255);im.save(assets/'today.png')
 badge()
 def weather_token(code):
  if code==0:return 'clear','晴'
  if code in [1,2]:return 'partly','多云'
  if code==3:return 'cloud','阴'
  if code in [45,48]:return 'fog','雾'
  if code in [71,73,75,77,85,86]:return 'snow','雪'
  return 'rain','雨'
 result={}
 for portrait in [False,True]:
  mode='portrait' if portrait else 'landscape';W,H=(1072,1448) if portrait else (1448,1072)
  bg=Image.new('L',(W,H),255);draw=ImageDraw.Draw(bg)
  boxes=[(18,14,1054,360),(18,376,1054,724),(18,742,1054,980),(18,996,1054,1210),(18,1228,1054,1406)] if portrait else [(18,16,674,548),(694,16,1430,548),(18,570,1430,764),(18,788,1430,1054)]
  for box in boxes:draw.rounded_rectangle(box,20,outline=0,width=3)
  lines=[(58,244,1016,244),(654,258,654,340),(58,442,682,442),(728,420,728,698),(766,504,1010,504),(766,582,1010,582),(382,822,382,952),(722,822,722,952),(184,1024,184,1080)] if portrait else [(58,408,644,408),(448,432,448,522),(720,100,1190,100),(1218,76,1218,520),(1240,232,1402,232),(1240,358,1402,358),(238,618,238,730),(622,618,622,730),(1014,618,1014,730),(766,822,766,1030),(164,830,164,886),(908,830,908,886)]
  for line in lines:draw.line(line,fill=0,width=2)
  name='bg_portrait.png' if portrait else 'bg_report.png';bg.save(assets/name)
  commands=[f'I|0|0|0|0|/mnt/us/dashboard/icons/{name}']
  def text(size,y,x,value,maxw=None):
   value=str(value)
   if maxw:
    while size>16 and font(size).getlength(value)>maxw:size-=1
   commands.append(f'T|{size}|{round(y-size*.45)}|{round(x)}|0|{value}')
  def center(size,y,x,value):text(size,y,x-font(size).getlength(str(value))/2,value)
  def image(name,x,y,w,h=None):commands.append(f'I|{x}|{y}|{w}|{h or w}|/mnt/us/dashboard/icons/{name}.png')
  text(40 if portrait else 34,36 if portrait else 44,64 if portrait else 58,r['city'])
  if weather.get('status') in ['ok','stale']:
   icon,condition=weather_token(weather['code'])
   if portrait:
    image(icon,160,254,128,104);text(64,256,360,f"{weather['temperature']:.0f}°C");text(30,266,548,condition)
    text(27,314,360,f"风速 {weather['wind']:g} m/s");text(30,262,720,f"↑{weather['high']:.0f}°  ↓{weather['low']:.0f}°");text(30,316,720,f"湿度 {weather['humidity']}%")
   else:
    image(icon,64,432,104);text(64,432,214,f"{weather['temperature']:.0f}°C");text(30,440,376,condition)
    text(25,492,214,f"风速 {weather['wind']:g} m/s");text(30,436,480,f"↑{weather['high']:.0f}° ↓{weather['low']:.0f}°");text(30,494,480,f"湿度 {weather['humidity']}%")
  else:text(30,300 if portrait else 464,100,'天气未配置')
  # Month grid uses six available rows, with the same seven weekday columns.
  text(44,398 if portrait else 42,74 if portrait else 880,f'{day.year}年{day.month}月')
  for i,wd in enumerate('一二三四五六日'):center(28,454 if portrait else 124,(125+i*84) if portrait else (735+i*70),wd)
  first,total=calendar.monthrange(day.year,day.month)
  for n in range(1,total+1):
   index=first+n-1;row,col=divmod(index,7);x=125+col*84 if portrait else 735+col*70;y=(500+row*37) if portrait else (184+row*58)
   if n==day.day:image('today',x-22,y-8,44)
   else:center(31 if portrait else 34,y,x,n)
  x=766 if portrait else 1240
  text(28 if portrait else 25,408 if portrait else 92,x,'农历')
  text(36 if portrait else 30,454 if portrait else 152,x,l['date'],maxw=250 if portrait else 168)
  text(30,534 if portrait else 280,x,l['year']+'年')
  text(29 if portrait else 26,606 if portrait else 390,x,'节气 '+l['term'])
  text(27 if portrait else 24,658 if portrait else 466,x,'距'+str(l['next_term'] or '--')+' '+str(l['days_to_next'] if l['days_to_next'] is not None else '--')+'天',maxw=250 if portrait else 170)
  if portrait:text(36,760,58,'未来3天预报')
  else:text(34,634,58,'未来3天');text(34,684,58,'预报')
  for i,f in enumerate(weather.get('forecast',[])[:3]):
   date=dt.date.fromisoformat(f['date']);ic,condition=weather_token(f['code']);label=f'{date.month}月{date.day}日（周'+ '一二三四五六日'[date.weekday()]+'）'
   if portrait:
    x=70+i*340;text(29,826,x,label,maxw=310);image(ic,x,874,88);text(30,880,x+112,condition);text(30,924,x+112,f"{f['low']:.0f}°~{f['high']:.0f}°C",maxw=210)
   else:
    x=290+i*384;text(29,612,x,label,maxw=350);image(ic,x,664,86);text(29,688,x+98,condition);text(29,688,x+160,f"{f['low']:.0f}°~{f['high']:.0f}°C",maxw=200)
  if portrait:
   image('codex',58,1018,80);text(48,1032,226,'Codex')
   image('deepseek',64,1242,90,74);text(48,1256,226,'DeepSeek')
  else:
   image('codex',64,820,80);text(48,838,190,'Codex')
   image('deepseek',812,824,82,74);text(48,838,932,'DeepSeek')
  bar_w=928 if portrait else 660;bar_h=34;bar=Image.new('L',(bar_w,bar_h),255);bd=ImageDraw.Draw(bar);bd.rounded_rectangle((0,0,bar_w-1,bar_h-1),bar_h//2,fill=210)
  fill=round(bar_w*percent/100) if percent is not None else 0
  if fill>0:
   mask=Image.new('L',bar.size,0);md=ImageDraw.Draw(mask);md.rounded_rectangle((0,0,bar_w-1,bar_h-1),bar_h//2,fill=255);md.rectangle((fill,0,bar_w,bar_h),fill=0);bar.paste(0,(0,0),mask)
  bar.save(assets/('quota_'+mode+'.png'));image('quota_'+mode,62,1103 if portrait else 930,bar_w,bar_h)
  if portrait:
   text(23,1160,78,usage if percent is not None else '周额度未配置',maxw=290);text(22,1160,390,'重置：'+reset_text,maxw=400);text(22,1160,838,'更新：'+updated,maxw=180)

  else:
   text(22,992,60,usage if percent is not None else '周额度未配置',maxw=240);text(21,992,310,'额度重置：'+reset_text,maxw=280);text(21,992,600,'更新 '+updated,maxw=140)

  balances=deep.get('balances') or ([{'currency':deep.get('currency'),'balance':deep['balance']}] if deep.get('balance') is not None else [])
  text(30 if portrait else 27,1344 if portrait else 932,80 if portrait else 816,'剩余余额')
  if not balances:text(38,1338 if portrait else 980,300 if portrait else 816,'未配置')
  else:
   left=300 if portrait else 816;available=720 if portrait else 590;slot=available/len(balances)
   for i,entry in enumerate(balances):
    currency=entry['currency'];symbol={'CNY':'¥','USD':'$'}.get(currency,'')
    text(38 if portrait else 36,1338 if portrait else 980,left+i*slot,f"{currency} {symbol}{entry['balance']:.2f}",maxw=slot-16)

  result[mode]=commands
 r['layouts']=CLOCKS
 return result['landscape'],result['portrait']
