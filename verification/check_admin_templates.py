from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined

root = Path(__file__).parent
env = Environment(loader=FileSystemLoader(root / "templates"), undefined=StrictUndefined)
for name in ("admin/dashboard.html", "admin/borrows.html", "admin/fines.html", "admin/charts.html", "admin/reports.html"):
    env.parse((root / "templates" / name).read_text(encoding="utf-8"))
    print(f"OK {name}")
