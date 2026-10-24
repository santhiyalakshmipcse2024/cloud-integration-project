from __future__ import annotations

from .models import Finding


def compare_runs(previous: list[Finding], current: list[Finding]) -> dict:
    prev = {f.fingerprint: f for f in previous}
    curr = {f.fingerprint: f for f in current}
    return {
        "new": [curr[k] for k in curr.keys() - prev.keys()],
        "resolved": [prev[k] for k in prev.keys() - curr.keys()],
        "persistent": [curr[k] for k in curr.keys() & prev.keys()],
    }
