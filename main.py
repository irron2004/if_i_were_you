from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
APP_ROOT = BASE_DIR / "mbti-arcade"

os.chdir(APP_ROOT)
sys.path.insert(0, str(APP_ROOT))

module_path = APP_ROOT / "app" / "main.py"
spec = importlib.util.spec_from_file_location("mbti_app_main", module_path)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load mbti-arcade app module")

mbti_app_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mbti_app_main)
app = mbti_app_main.app
