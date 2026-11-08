"""Clock cadence cases, including seconds, hour/day rollover and render delays."""
from pathlib import Path
import subprocess,datetime
power=Path(__file__).resolve().parent/'extensions/dashboard/bin/power.sh'
cases=[(14,52,0),(14,52,34),(14,59,59),(14,50,0),(23,59,59),(0,0,0),(15,0,3)]
base=datetime.datetime(2026,11,8,tzinfo=datetime.timezone.utc)
commands=['. "$1"']
expected=[]
for h,m,s in cases:
 now=base.replace(hour=h,minute=m,second=s)
 boundary=now.replace(minute=m-m%10,second=0)+datetime.timedelta(minutes=10)
 epoch=int(now.timestamp());commands.append(f'echo "$(next_refresh_epoch {epoch}) $(refresh_delay {epoch})"')
 expected.append(f'{int(boundary.timestamp())} {int((boundary-now).total_seconds())}')
actual=subprocess.check_output(['sh','-c','\n'.join(commands),'sh',str(power)],text=True).splitlines()
assert actual==expected,(actual,expected)
print('PASS: :52→8 min; :52:34→7m26s; :59:59→1s; exact boundary→10 min; midnight rollover; late render stays aligned')
