"""One-command local launcher. Requires Python 3.11+ for a fresh installation."""
from pathlib import Path
import os
import subprocess
import sys
import venv

root=Path(__file__).resolve().parent
environment=root/".venv"
python=environment/("Scripts/python.exe" if os.name=="nt" else "bin/python")
if not python.exists():
    if not (3,11) <= sys.version_info[:2] < (3,15):
        raise SystemExit("Install Python 3.11–3.14, then rerun this launcher. Windows: py -3.12 launch.py")
    print("Creating a project-local Python environment…",flush=True)
    venv.EnvBuilder(with_pip=True).create(environment)
check=subprocess.run([str(python),"-c","import flowworkbench, streamlit"],cwd=root,capture_output=True)
if check.returncode:
    subprocess.run([str(python),"-m","pip","install","--upgrade","pip"],check=True,cwd=root)
    subprocess.run([str(python),"-m","pip","install","-e",str(root)],check=True,cwd=root)
raise SystemExit(subprocess.call([str(python),"-m","flowworkbench.cli",*sys.argv[1:]] if len(sys.argv)>1 else [str(python),"-m","flowworkbench.cli","gui"],cwd=root))
