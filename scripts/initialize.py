import subprocess
import sys
for args in [['migrate','--noinput'],['bootstrap_roles'],['collectstatic','--noinput']]:
    subprocess.run([sys.executable,'manage.py',*args],check=True)
