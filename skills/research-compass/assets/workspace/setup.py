#!/usr/bin/env python3
"""Create project-local skill links. No install, network, commit, or push."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
helper = root / 'skills/research-compass/scripts/compass.py'
if not helper.is_file():
    raise SystemExit('Canonical skill is missing: ' + str(helper))
raise SystemExit(subprocess.call([sys.executable, str(helper), 'install', '--root', str(root)]))
