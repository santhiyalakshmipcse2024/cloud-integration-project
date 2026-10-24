"""Orchestrates a scan: validate -> ingest -> analyse -> check -> prioritise -> remediate -> store."""
from __future__ import annotations

from typing import Callable
from urllib.parse import urlparse

from . import __version__
from .checks import merge_with_axe, normalise_axe, run_builtin_checks
from .config import Config
from .dom_analysis import collect, parse
from .ingestion import IngestionError, load_page
from .models import DISCLAIMER, Finding, ScanResult, now_iso
from .prioritization import group_findings
from .remediation import LLMAdapter, remediate
from .security import RateLimiter, ScanNotAllowed, robots_allowed, validate_target
from .storage import Storage

Progress = Callable[[float, str], None]


def run_scan(targets: list[str], authorized: bool, cfg: Config, rules: dict,
             adapter: LLMAdapter | None = None, use_browser: bool = True, use_axe: bool = True,
             progress: Progress | None = None, store: bool = True,
             limiter: RateLimiter | None = None) -> ScanResult:
    progress = progress or (lambda p, m: None)
    started = now_iso()
    limiter = limiter or RateLimiter(cfg.min_delay_s)
    targets = [t.strip() for t in targets if t.strip()][: cfg.max_pages]
    findings: list[Finding] = []
    status: dict = {}
    axe_version = None

    for i, t in enumerate(targets):
        progress(i / max(len(targets), 1), f"Scanning {t} ({i + 1}/{len(targets)})")
        try:
            kind = validate_target(t, cfg, authorized)
            if kind == "url":
                if cfg.respect_robots and not robots_allowed(t, cfg.user_agent):
                    raise ScanNotAllowed("Blocked by robots.txt for this user agent.")
                limiter.wait(urlparse(t).hostname or "")
            snap = load_page(t, kind, cfg, use_browser=use_browser, use_axe=use_axe)
            builtin = run_builtin_checks(snap.html, snap.url, rules)
            if snap.axe:
                axe_version = snap.axe.get("testEngine", {}).get("version", axe_version)
                page_f = merge_with_axe(builtin, normalise_axe(snap.axe, snap.url), rules)
            else:
                page_f = builtin
            dom = collect(parse(snap.html))
            findings += page_f
            status[snap.url] = {"status": "ok", "message": f"{len(page_f)} findings",
                                "notes": snap.notes, "rendered": snap.rendered,
                                "dom_summary": {k: len(v) for k, v in dom.items() if isinstance(v, list)}}
        except (ScanNotAllowed, IngestionError) as e:
            status[t] = {"status": "error", "message": str(e), "notes": []}
        except Exception as e:  # never crash the whole scan on one bad page
            status[t] = {"status": "error", "message": f"Unexpected {type(e).__name__}: {e}", "notes": []}

    # AI remediation: one call per group representative (bounded), shared across the group
    progress(0.9, "Generating remediation guidance")
    for n, g in enumerate(group_findings(findings)):
        use = adapter if n < cfg.llm_max_items else None
        rem = remediate(g["representative"], rules, use)
        for f in g["items"]:
            f.remediation = rem

    result = ScanResult(
        scan_id=None, started=started, finished=now_iso(), targets=targets, findings=findings, page_status=status,
        metadata={
            "tool": {"name": "a11y-auditor", "version": __version__, "axe_core": axe_version or "not used"},
            "llm": adapter.name if adapter else "none (rule-based guidance only)",
            "browser_rendering": use_browser, "respect_robots": cfg.respect_robots,
            "min_delay_s": cfg.min_delay_s, "disclaimer": DISCLAIMER,
        },
    )
    if store:
        Storage(cfg.db_path).save_scan(result)
    progress(1.0, "Done")
    return result
