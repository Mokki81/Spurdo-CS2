import base64, pathlib, runpy, tempfile
base = pathlib.Path(__file__).parent
b64 = "".join((base / f"b{i:02d}").read_text(encoding="ascii") for i in range(10))
boot = base64.b64decode(b64).decode("utf-8")
p = pathlib.Path(tempfile.gettempdir()) / "spurdo_boot_run.py"
p.write_text(boot, encoding="utf-8")
runpy.run_path(str(p), run_name="__main__")
