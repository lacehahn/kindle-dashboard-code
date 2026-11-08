import os, subprocess, time, base64, sqlite3, tempfile
from pathlib import Path
STABLE=Path('/Users/lance/.cache/inknotifier/adb35/platform-tools/adb')
ADB=os.environ.get('INK_ADB',str(STABLE) if STABLE.exists() else 'adb')
PACKAGE='dev.inknotifier'
def shell(serial,command):
    for attempt in range(5):
        r=subprocess.run([ADB,'-s',serial,'shell','-n',command],capture_output=True,timeout=25)
        if r.returncode==0 and r.stdout:return r.stdout
        if attempt==4:raise RuntimeError('ADB command failed: '+r.stderr.decode(errors='replace')[:200])
        time.sleep(0.5)
def stats(serial):
    private=Path(__file__).resolve().parents[1]/'.device-config';private.mkdir(mode=0o700,exist_ok=True)
    b=base64.b64decode(shell(serial,f'run-as {PACKAGE} cat databases/ink.db | base64'))
    if not b.startswith(b'SQLite format 3'):raise RuntimeError('Incomplete database snapshot')
    fd,path=tempfile.mkstemp(dir=private,suffix='.db')
    try:
        os.write(fd,b);os.close(fd)
        d=sqlite3.connect(path)
        result={t:d.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['inbox','outbox','seen']}
        # Return only synthetic test rows, never personal notification content.
        result['tests']=d.execute("SELECT title,version,instance FROM inbox WHERE pkg='com.android.shell' OR pkg='dev.inknotifier'").fetchall()
        d.close();return result
    finally:os.unlink(path)
