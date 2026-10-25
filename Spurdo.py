# Spurdo CS2 — entry (reconstructs from chunks)
from pathlib import Path
import runpy, tempfile
base = Path(__file__).parent
parts = [(base / f"chunk_{i}.txt").read_text(encoding="utf-8") for i in range(4)]
code = "".join(parts)
p = Path(tempfile.gettempdir()) / "spurdo_run.py"
p.write_text(code, encoding="utf-8")
print("[+] SPURDO EXTERNAL xDDD — starting")
runpy.run_path(str(p), run_name="__main__")
