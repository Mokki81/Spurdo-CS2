# -*- coding: utf-8 -*-
"""SPURDO launcher — merges halves and runs."""
from pathlib import Path
import runpy
base = Path(__file__).parent
code = (base / "Spurdo_half1.py").read_text(encoding="utf-8") + (base / "Spurdo_half2.py").read_text(encoding="utf-8")
out = base / "_spurdo_full.py"
out.write_text(code, encoding="utf-8")
runpy.run_path(str(out), run_name="__main__")
