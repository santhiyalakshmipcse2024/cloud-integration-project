"""Export: JSON, CSV and PDF with remediation guidance and scan metadata."""
from __future__ import annotations

import csv
import io
import json
from xml.sax.saxutils import escape

from .models import DISCLAIMER, ScanResult
from .prioritization import group_findings

CSV_FIELDS = ["page_url", "rule_id", "source", "severity", "confidence", "wcag", "selector", "message",
              "html", "user_impact", "suggested_fix", "sample_markup", "ai_generated", "fingerprint"]


def to_json(r: ScanResult, manual: list[dict] | None = None) -> str:
    return json.dumps({
        "disclaimer": DISCLAIMER, "scan_id": r.scan_id, "started": r.started, "finished": r.finished,
        "targets": r.targets, "metadata": r.metadata, "page_status": r.page_status,
        "automated_findings": [f.to_dict() for f in r.findings],
        "manual_review": manual or [],
    }, indent=2)


def to_csv(r: ScanResult) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS, extrasaction="ignore")
    w.writeheader()
    for f in r.findings:
        d = f.to_dict()
        rem = f.remediation or {}
        d.update({k: rem.get(k, "") for k in ("user_impact", "suggested_fix", "sample_markup", "ai_generated")})
        # neutralise spreadsheet formula injection
        w.writerow({k: ("'" + str(v) if isinstance(v, str) and v[:1] in "=+-@" else v) for k, v in d.items()})
    return buf.getvalue()


def to_pdf(r: ScanResult, manual: list[dict] | None = None) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer

    st = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Accessibility audit report")
    p = lambda t, s="BodyText": Paragraph(escape(str(t)), st[s])
    story = [p("Accessibility Audit Report", "Title"), p(DISCLAIMER),
             p(f"Scan #{r.scan_id} | {r.started} -> {r.finished}"),
             p("Targets: " + ", ".join(r.targets)),
             p("Tool: " + json.dumps(r.metadata.get("tool", {}))), Spacer(1, 12)]
    groups = group_findings(r.findings)
    story.append(p(f"{len(r.findings)} automated findings in {len(groups)} groups", "Heading2"))
    for g in groups:
        f = g["representative"]
        rem = f.remediation or {}
        story += [p(f"[{g['severity'].upper()} / {g['confidence']} confidence] {g['rule_id']} x{g['count']}", "Heading3"),
                  p(f"Page: {g['page_url']}"), p(f"Selector: {f.selector}"), p(f"Issue: {f.message}"),
                  p(f"User impact: {rem.get('user_impact', '')}"), p(f"Suggested fix: {rem.get('suggested_fix', '')}")]
        if rem.get("ai_generated"):
            story.append(p("(AI-generated suggestion - verify manually)"))
        if rem.get("sample_markup"):
            story.append(Preformatted(rem["sample_markup"][:600], st["Code"]))
        story.append(Spacer(1, 6))
    if manual:
        story.append(p("Manual review outcomes (human-recorded)", "Heading2"))
        for m in manual:
            story.append(p(f"{m['page_url']} | {m['check_id']}: {m['outcome']} {m.get('notes') or ''} ({m.get('tester') or 'n/a'})"))
    doc.build(story)
    return buf.getvalue()
