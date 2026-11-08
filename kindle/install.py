"""Install assets and scripts over USB, preserving device settings and fonts."""
from pathlib import Path
import shutil,datetime,hashlib
root=Path(__file__).resolve().parent
volume=Path('/Volumes/Kindle')
if not (volume/'extensions/dashboard/bin/config.sh').exists():
 raise SystemExit('Existing dashboard/config.sh not found; connect the configured Kindle first.')
backup=root.parent/'.device-config'/'kindle-backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
backup.mkdir(parents=True)
for folder in ['extensions/dashboard','dashboard']:
 shutil.copytree(volume/folder,backup/folder)
files=[]
for name in ['clock.sh','ui.sh','landscape.sh','start.sh','stop.sh','raster.sh','render','exclusive.sh','session.sh','button-exit.sh','power.sh','power-events.sh','tickwait','report-layout.sh','report-download.sh','reportread','report-weather.sh','weatherread']:
 files.append((root/'extensions/dashboard/bin'/name,volume/'extensions/dashboard/bin'/name))
files.append((root/'extensions/dashboard/menu.json',volume/'extensions/dashboard/menu.json'))
for src in (root/'dashboard').rglob('*.png'):
 files.append((src,volume/'dashboard'/src.relative_to(root/'dashboard')))
for src,dst in files:
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
 if src.suffix=='.sh' or src.name in ['render','tickwait','reportread','weatherread']:dst.chmod(0o755)
 assert hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256(dst.read_bytes()).digest(),dst
# These obsolete files belonged to the former touch-exit feature; backed up above.
for old in ['exitwatch','exitwatch.c']:
 (volume/'extensions/dashboard/bin'/old).unlink(missing_ok=True)
print(f'Installed and verified {len(files)} files. Backup: {backup}')
