"""Configuration + business rules (rules.json) – edit these without touching code."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

try:  # optional
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = ROOT / "config" / "rules.json"


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _list(name: str) -> list[str]:
    return [x.strip().lower() for x in os.getenv(name, "").split(",") if x.strip()]


@dataclass
class Config:
    allowed_domains: list[str]
    approved_local_dir: Path
    max_pages: int = 10
    timeout_s: int = 30
    min_delay_s: float = 2.0
    respect_robots: bool = True
    allow_private_hosts: bool = False
    db_path: Path = ROOT / "data" / "auditor.db"
    axe_path: Path = ROOT / "vendor" / "axe.min.js"
    llm_provider: str = "none"
    llm_model: str = "claude-sonnet-5-5"
    llm_max_items: int = 10
    user_agent: str = "A11yAuditorBot/0.1 (+authorized accessibility scan)"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            allowed_domains=_list("A11Y_ALLOWED_DOMAINS"),
            approved_local_dir=Path(os.getenv("A11Y_LOCAL_DIR", ROOT / "data" / "approved_html")),
            max_pages=int(os.getenv("A11Y_MAX_PAGES", "10")),
            timeout_s=int(os.getenv("A11Y_TIMEOUT_S", "30")),
            min_delay_s=float(os.getenv("A11Y_MIN_DELAY_S", "2")),
            respect_robots=_bool("A11Y_RESPECT_ROBOTS", True),
            allow_private_hosts=_bool("A11Y_ALLOW_PRIVATE_HOSTS", False),
            db_path=Path(os.getenv("A11Y_DB_PATH", ROOT / "data" / "auditor.db")),
            axe_path=Path(os.getenv("A11Y_AXE_PATH", ROOT / "vendor" / "axe.min.js")),
            llm_provider=os.getenv("A11Y_LLM_PROVIDER", "none").lower(),
            llm_model=os.getenv("A11Y_LLM_MODEL", "claude-sonnet-5-5"),
            llm_max_items=int(os.getenv("A11Y_LLM_MAX_ITEMS", "10")),
        )


def load_rules(path: Path = RULES_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
