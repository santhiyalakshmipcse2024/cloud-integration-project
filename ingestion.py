"""Page ingestion: renders with Playwright when available, falls back to static HTML."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .config import Config

MAX_BYTES = 5 * 1024 * 1024


@dataclass
class PageSnapshot:
    url: str
    html: str
    status: int | None = None
    rendered: bool = False
    axe: dict | None = None
    notes: list[str] = field(default_factory=list)


class IngestionError(Exception):
    pass


def _static_fetch(url: str, cfg: Config) -> PageSnapshot:
    try:
        r = requests.get(url, timeout=cfg.timeout_s, headers={"User-Agent": cfg.user_agent})
    except requests.Timeout as e:
        raise IngestionError(f"Timed out after {cfg.timeout_s}s fetching {url}") from e
    except requests.RequestException as e:
        raise IngestionError(f"Could not fetch {url}: {e}") from e
    if r.status_code == 429:
        raise IngestionError("Rate limited by server (HTTP 429). Increase A11Y_MIN_DELAY_S and retry later.")
    if r.status_code >= 400:
        raise IngestionError(f"Server returned HTTP {r.status_code} for {url}")
    if len(r.content) > MAX_BYTES:
        raise IngestionError("Page larger than 5 MB limit.")
    return PageSnapshot(
        url=url, html=r.text, status=r.status_code, rendered=False,
        notes=["Static HTML only: JavaScript-generated content was NOT evaluated."],
    )


def _playwright_render(url: str, cfg: Config, use_axe: bool) -> PageSnapshot:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            ctx = browser.new_context(user_agent=cfg.user_agent)
            page = ctx.new_page()
            page.set_default_timeout(cfg.timeout_s * 1000)
            try:
                resp = page.goto(url, wait_until="networkidle")
            except PWTimeout as e:
                raise IngestionError(f"Timed out after {cfg.timeout_s}s loading {url}") from e
            status = resp.status if resp else None
            if status == 429:
                raise IngestionError("Rate limited by server (HTTP 429).")
            if status and status >= 400:
                raise IngestionError(f"Server returned HTTP {status} for {url}")
            html = page.content()
            notes = ["Rendered in Chromium after network idle. Content behind interaction/login is not covered."]
            axe = None
            if use_axe:
                if cfg.axe_path.exists():
                    page.add_script_tag(path=str(cfg.axe_path))
                    axe = page.evaluate(
                        "async () => await axe.run(document, {resultTypes:['violations','incomplete']})"
                    )
                else:
                    notes.append("axe-core not installed (run scripts/setup_axe.py); using built-in checks only.")
            return PageSnapshot(url=url, html=html, status=status, rendered=True, axe=axe, notes=notes)
        finally:
            browser.close()


def load_page(target: str, kind: str, cfg: Config, use_browser: bool = True, use_axe: bool = True) -> PageSnapshot:
    if kind == "file":
        path = Path(target).expanduser().resolve()
        if use_browser:
            try:
                snap = _playwright_render(path.as_uri(), cfg, use_axe)
                snap.url = str(path)
                return snap
            except ImportError:
                pass
            except IngestionError:
                raise
            except Exception as e:  # browser not installed etc.
                note = f"Browser unavailable ({type(e).__name__}); parsed static file."
                return PageSnapshot(url=str(path), html=path.read_text(encoding="utf-8", errors="replace"),
                                    notes=[note])
        return PageSnapshot(url=str(path), html=path.read_text(encoding="utf-8", errors="replace"),
                            notes=["Static file parsed; scripts not executed."])
    if use_browser:
        try:
            return _playwright_render(target, cfg, use_axe)
        except ImportError:
            snap = _static_fetch(target, cfg)
            snap.notes.append("Playwright not installed; fell back to static fetch.")
            return snap
        except IngestionError:
            raise
        except Exception as e:
            snap = _static_fetch(target, cfg)
            snap.notes.append(f"Browser unavailable ({type(e).__name__}); fell back to static fetch.")
            return snap
    return _static_fetch(target, cfg)
