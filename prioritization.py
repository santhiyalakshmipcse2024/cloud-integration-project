from __future__ import annotations

from collections import defaultdict

from .models import CONFIDENCE_WEIGHT, SEVERITY_WEIGHT, Finding


def filter_findings(findings, page=None, rule=None, severity=None, min_confidence=None, source=None):
    out = []
    for f in findings:
        if page and f.page_url != page:
            continue
        if rule and f.rule_id != rule:
            continue
        if severity and f.severity not in severity:
            continue
        if min_confidence and CONFIDENCE_WEIGHT[f.confidence] < CONFIDENCE_WEIGHT[min_confidence]:
            continue
        if source and f.source != source:
            continue
        out.append(f)
    return out


def group_findings(findings: list[Finding]) -> list[dict]:
    """Group repeated component issues (same rule + same selector pattern + same page) and rank them."""
    buckets: dict[tuple, list[Finding]] = defaultdict(list)
    for f in findings:
        buckets[(f.rule_id, f.page_url, f.component_key)].append(f)
    groups = []
    for (rule, page, comp), items in buckets.items():
        rep = max(items, key=lambda x: x.score)
        groups.append({
            "rule_id": rule, "page_url": page, "component": comp, "count": len(items),
            "severity": max((i.severity for i in items), key=lambda s: SEVERITY_WEIGHT[s]),
            "confidence": rep.confidence, "score": rep.score, "source": rep.source,
            "message": rep.message, "representative": rep, "items": items,
        })
    groups.sort(key=lambda g: (-g["score"], -g["count"], g["rule_id"]))
    return groups
