import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/pattern-making/scripts'
sys.path.insert(0, str(SCRIPTS))
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
