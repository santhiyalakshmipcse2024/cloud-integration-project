from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

SEVERITIES = ["critical", "serious", "moderate", "minor"]
CONFIDENCES = ["high", "medium", "low"]
SEVERITY_WEIGHT = {"critical": 4, "serious": 3, "moderate": 2, "minor": 1}
CONFIDENCE_WEIGHT = {"high": 3, "medium": 2, "low": 1}

DISCLAIMER = (
    "Automated scans detect only a subset of accessibility problems and cannot prove WCAG "
    "compliance. Findings marked AI-generated are suggestions that require human review. "
    "Manual keyboard, focus and screen-reader testing is still required."
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Finding:
    rule_id: str
    source: str            # "builtin" | "axe-core"
    severity: str
    confidence: str
    page_url: str
    selector: str
    html: str
    message: str
    context: str = ""
    wcag: str = ""
    help_url: str = ""
    remediation: dict | None = None

    @property
    def component_key(self) -> str:
        """Selector without nth-of-type indexes -> groups repeated component issues."""
        return re.sub(r":nth-of-type\(\d+\)", "", self.selector)

    @property
    def fingerprint(self) -> str:
        norm = re.sub(r"\s+", " ", self.html)[:200]
        raw = f"{self.rule_id}|{self.page_url}|{self.selector}|{norm}"
        return hashlib.sha1(raw.encode()).hexdigest()[:16]

    @property
    def score(self) -> int:
        return SEVERITY_WEIGHT.get(self.severity, 1) * CONFIDENCE_WEIGHT.get(self.confidence, 1)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["fingerprint"] = self.fingerprint
        d["component_key"] = self.component_key
        d["score"] = self.score
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Finding":
        keys = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in d.items() if k in keys})


@dataclass
class ScanResult:
    scan_id: int | None
    started: str
    finished: str
    targets: list[str]
    findings: list[Finding]
    page_status: dict          # url -> {"status": "ok"|"error", "message": str, "notes": [...]}
    metadata: dict
