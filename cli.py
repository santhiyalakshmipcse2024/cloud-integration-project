"""Headless scan: python scripts/cli.py --authorized URL_OR_FILE ... [--format json|csv|pdf]"""
import argparse, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from a11y_auditor.config import Config, load_rules
from a11y_auditor.pipeline import run_scan
from a11y_auditor.remediation import build_adapter
from a11y_auditor.report import to_csv, to_json, to_pdf

ap = argparse.ArgumentParser()
ap.add_argument("targets", nargs="+")
ap.add_argument("--authorized", action="store_true", help="confirm you are allowed to scan these targets")
ap.add_argument("--no-browser", action="store_true")
ap.add_argument("--ai", action="store_true")
ap.add_argument("--format", choices=["json", "csv", "pdf"], default="json")
ap.add_argument("--out", default="exports/report")
a = ap.parse_args()

cfg = Config.from_env()
adapter = build_adapter(cfg.llm_provider, cfg.llm_model) if a.ai else None
res = run_scan(a.targets, a.authorized, cfg, load_rules(), adapter, use_browser=not a.no_browser,
               progress=lambda p, m: print(f"[{p:4.0%}] {m}"))
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
path = Path(f"{a.out}.{a.format}")
if a.format == "pdf":
    path.write_bytes(to_pdf(res))
else:
    path.write_text(to_json(res) if a.format == "json" else to_csv(res), encoding="utf-8")
print(f"{len(res.findings)} findings -> {path}")
for url, s in res.page_status.items():
    if s["status"] == "error":
        print(f"ERROR {url}: {s['message']}")
