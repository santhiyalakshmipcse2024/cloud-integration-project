"""Automated checks: built-in DOM rules + normalisation of axe-core results."""
from __future__ import annotations

import re
from collections import Counter

from bs4 import BeautifulSoup

from .dom_analysis import accessible_name, context, css_selector, parse, snippet, text_of
from .models import Finding

GENERIC_LINK_TEXT = {"click here", "here", "read more", "more", "learn more", "link", "this", "details"}
SUSPICIOUS_ALT = re.compile(r"^(img|image|photo|picture|dsc|screenshot)?[\s_\-]*\d*(\.(jpe?g|png|gif|svg|webp))?$|\.(jpe?g|png|gif|svg|webp)$", re.I)


def _mk(rule_id, el, page, message, rules, **over) -> Finding:
    r = rules[rule_id]
    return Finding(
        rule_id=rule_id, source="builtin",
        severity=over.get("severity", r["severity"]), confidence=over.get("confidence", r["confidence"]),
        page_url=page, selector=css_selector(el) if el is not None else "html",
        html=snippet(el) if el is not None else "", context=context(el) if el is not None else "",
        message=message, wcag=r["wcag"],
    )


def run_builtin_checks(html: str, page_url: str, rules: dict) -> list[Finding]:
    soup: BeautifulSoup = parse(html)
    out: list[Finding] = []
    root = soup.html

    if root is not None and not (root.get("lang") or "").strip():
        out.append(_mk("html-lang", root, page_url, "<html> element has no lang attribute.", rules))
    if not soup.title or not text_of(soup.title):
        out.append(_mk("document-title", soup.head or root, page_url, "Document has no non-empty <title>.", rules))

    for img in soup.find_all("img"):
        alt = img.get("alt")
        if alt is None and img.get("role") not in {"presentation", "none"}:
            out.append(_mk("image-alt", img, page_url, "Image has no alt attribute.", rules))
        elif alt and SUSPICIOUS_ALT.search(alt.strip()):
            out.append(_mk("image-alt-suspicious", img, page_url, f"Alt text '{alt}' looks like a placeholder.", rules))

    for a in soup.find_all("a", href=True):
        name = accessible_name(a, soup)
        if not name:
            out.append(_mk("link-name", a, page_url, "Link has no accessible name.", rules))
        elif name.lower().strip(" .!") in GENERIC_LINK_TEXT:
            out.append(_mk("link-generic-text", a, page_url, f"Link text '{name}' is not descriptive.", rules))

    for b in soup.find_all("button"):
        if not accessible_name(b, soup):
            out.append(_mk("button-name", b, page_url, "Button has no accessible name.", rules))

    for c in soup.find_all(["input", "select", "textarea"]):
        if c.get("type") in {"hidden", "submit", "button", "reset", "image"}:
            continue
        if not accessible_name(c, soup):
            conf = "high"
            msg = "Form control has no label."
            if c.get("placeholder"):
                msg += " A placeholder is present but is not an accessible label."
            out.append(_mk("form-label", c, page_url, msg, rules, confidence=conf))

    headings = soup.find_all(re.compile(r"^h[1-6]$"))
    h1s = [h for h in headings if h.name == "h1"]
    if len(h1s) != 1 and soup.body is not None:
        out.append(_mk("heading-h1", h1s[1] if len(h1s) > 1 else soup.body, page_url,
                       f"Found {len(h1s)} h1 elements (expected exactly 1).", rules))
    prev = 0
    for h in headings:
        lvl = int(h.name[1])
        if prev and lvl > prev + 1:
            out.append(_mk("heading-order", h, page_url, f"Heading jumps from h{prev} to h{lvl}.", rules))
        prev = lvl

    if soup.body is not None and not soup.find(["main"]) and not soup.find(attrs={"role": "main"}):
        out.append(_mk("landmark-main", soup.body, page_url, "No <main> landmark found.", rules))

    ids = Counter(e["id"] for e in soup.find_all(id=True))
    for dup, n in ids.items():
        if n > 1:
            el = soup.find(id=dup)
            out.append(_mk("duplicate-id", el, page_url, f"id '{dup}' used {n} times.", rules))
    return out


AXE_SEVERITY = {"critical": "critical", "serious": "serious", "moderate": "moderate", "minor": "minor", None: "moderate"}


def normalise_axe(axe: dict, page_url: str) -> list[Finding]:
    out: list[Finding] = []
    for bucket, confidence in (("violations", "high"), ("incomplete", "low")):
        for v in axe.get(bucket, []):
            tags = [t for t in v.get("tags", []) if t.startswith("wcag") and any(ch.isdigit() for ch in t)]
            for node in v.get("nodes", []):
                target = node.get("target", [""])
                out.append(Finding(
                    rule_id=f"axe:{v['id']}", source="axe-core",
                    severity=AXE_SEVERITY.get(node.get("impact") or v.get("impact"), "moderate"),
                    confidence=confidence, page_url=page_url,
                    selector=" ".join(map(str, target)) if isinstance(target, list) else str(target),
                    html=(node.get("html") or "")[:240],
                    message=v.get("help", "") + (" (needs manual review)" if bucket == "incomplete" else ""),
                    wcag=", ".join(tags), help_url=v.get("helpUrl", ""),
                    context=(node.get("failureSummary") or "")[:200],
                ))
    return out


def merge_with_axe(builtin: list[Finding], axe_findings: list[Finding], rules: dict) -> list[Finding]:
    """When axe ran, drop built-in findings that axe already covers to avoid duplicates."""
    covered = {r["axe_equivalent"] for r in rules.values() if r.get("axe_equivalent")}
    covered_builtin = {k for k, r in rules.items() if r.get("axe_equivalent") in covered}
    kept = [f for f in builtin if f.rule_id not in covered_builtin]
    return kept + axe_findings
