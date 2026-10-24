"""Streamlit UI: Scan -> Findings -> Manual review -> Compare -> Export."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import streamlit as st

from a11y_auditor.compare import compare_runs
from a11y_auditor.config import Config, load_rules
from a11y_auditor.manual_review import CHECKLIST, OUTCOMES
from a11y_auditor.models import DISCLAIMER, SEVERITIES
from a11y_auditor.pipeline import run_scan
from a11y_auditor.prioritization import filter_findings, group_findings
from a11y_auditor.remediation import build_adapter
from a11y_auditor.report import to_csv, to_json, to_pdf
from a11y_auditor.storage import Storage

st.set_page_config(page_title="Accessibility Auditor", page_icon="♿", layout="wide")
cfg = Config.from_env()
rules = load_rules()
db = Storage(cfg.db_path)

st.title("♿ AI-Powered Website Accessibility Auditor")
st.warning(DISCLAIMER)

with st.sidebar:
    st.header("1. Input & scope")
    st.caption(f"Allowed domains: {', '.join(cfg.allowed_domains) or 'NONE configured'}")
    raw = st.text_area("URLs or approved local HTML paths (one per line)", height=120,
                       placeholder="https://example.com/\ndata/approved_html/demo.html")
    up = st.file_uploader("…or upload an HTML file", type=["html", "htm"])
    authorized = st.checkbox("I confirm I am authorized to scan these targets")
    use_browser = st.checkbox("Render with Playwright (dynamic content)", value=True)
    use_axe = st.checkbox("Run axe-core ruleset (if installed)", value=True)
    use_ai = st.checkbox(f"AI remediation ({cfg.llm_provider})", value=cfg.llm_provider != "none",
                         disabled=cfg.llm_provider == "none")
    go = st.button("Run scan", type="primary")

if go:
    targets = [t for t in raw.splitlines() if t.strip()]
    if up is not None:
        cfg.approved_local_dir.mkdir(parents=True, exist_ok=True)
        dest = cfg.approved_local_dir / Path(up.name).name
        dest.write_bytes(up.getvalue())
        targets.append(str(dest))
    if not targets:
        st.error("Enter at least one URL or file path.")
    else:
        bar = st.progress(0.0, text="Starting…")
        try:
            adapter = build_adapter(cfg.llm_provider, cfg.llm_model) if use_ai else None
        except Exception as e:
            adapter = None
            st.warning(f"AI adapter unavailable ({e}). Using rule-based guidance.")
        res = run_scan(targets, authorized, cfg, rules, adapter, use_browser, use_axe,
                       progress=lambda p, m: bar.progress(min(p, 1.0), text=m))
        st.session_state["scan_id"] = res.scan_id
        bar.empty()
        st.success(f"Scan #{res.scan_id} finished: {len(res.findings)} automated findings.")

scans = db.list_scans()
if not scans:
    st.info("No scans yet. Configure scope, tick authorization and run a scan.")
    st.stop()

ids = [s["id"] for s in scans]
sel = st.selectbox("Scan", ids, index=ids.index(st.session_state.get("scan_id", ids[0])) if st.session_state.get("scan_id") in ids else 0,
                   format_func=lambda i: next(f"#{s['id']} – {s['started']} – {len(s['targets'])} page(s), {s['findings']} findings" for s in scans if s["id"] == i))
scan = db.load_scan(sel)
manual = db.load_manual(sel)

tab_f, tab_m, tab_c, tab_e, tab_s = st.tabs(["Findings", "Manual review", "Compare runs", "Export", "Scan status"])

with tab_f:
    c1, c2, c3, c4 = st.columns(4)
    page = c1.selectbox("Page", ["(all)"] + sorted({f.page_url for f in scan.findings}))
    rule = c2.selectbox("Rule", ["(all)"] + sorted({f.rule_id for f in scan.findings}))
    sev = c3.multiselect("Severity", SEVERITIES, default=SEVERITIES)
    conf = c4.selectbox("Min confidence", ["(any)", "high", "medium", "low"])
    fl = filter_findings(scan.findings, None if page == "(all)" else page, None if rule == "(all)" else rule,
                         sev, None if conf == "(any)" else conf)
    groups = group_findings(fl)
    st.caption(f"{len(fl)} findings in {len(groups)} groups (ranked by severity × confidence). Source: automated.")
    for g in groups:
        f = g["representative"]
        rem = f.remediation or {}
        with st.expander(f"[{g['severity'].upper()} · {g['confidence']}] {g['rule_id']} ×{g['count']} — {g['message']}"):
            st.markdown(f"**Page:** `{g['page_url']}`  \n**WCAG:** {f.wcag or 'n/a'}  \n**Source:** {f.source}")
            st.markdown("**Evidence**")
            st.code(f.html or "(document-level)", language="html")
            st.caption(f"Selector: {f.selector}")
            if g["count"] > 1:
                st.caption("Also affects: " + "; ".join(i.selector for i in g["items"][1:6]) + (" …" if g["count"] > 6 else ""))
            tag = "🤖 AI-generated" if rem.get("ai_generated") else "📘 Rule-based"
            st.markdown(f"**{tag} guidance** — _{rem.get('origin', '')}_")
            st.write(f"**User impact:** {rem.get('user_impact', '')}")
            st.write(f"**Fix:** {rem.get('suggested_fix', '')}")
            if rem.get("sample_markup"):
                st.code(rem["sample_markup"], language="html")
            if rem.get("ai_error"):
                st.caption(rem["ai_error"])
            if f.help_url:
                st.markdown(f"[Rule documentation]({f.help_url})")

with tab_m:
    st.caption("Manual outcomes are recorded separately from automated findings.")
    pages = list(scan.page_status.keys())
    mp = st.selectbox("Page to review", pages, key="mp")
    tester = st.text_input("Tester name (optional)")
    saved = {m["check_id"]: m for m in manual if m["page_url"] == mp}
    for item in CHECKLIST:
        cur = saved.get(item["id"], {})
        with st.container(border=True):
            st.markdown(f"**{item['area']}** — {item['check']}")
            a, b, c = st.columns([1, 2, 1])
            out = a.selectbox("Outcome", OUTCOMES, index=OUTCOMES.index(cur.get("outcome", "not tested")), key=f"o{item['id']}{mp}")
            note = b.text_input("Notes", cur.get("notes", ""), key=f"n{item['id']}{mp}")
            if c.button("Save", key=f"s{item['id']}{mp}"):
                db.save_manual(sel, mp, item["id"], out, note, tester)
                st.toast("Saved")

with tab_c:
    others = [i for i in ids if i != sel]
    if not others:
        st.info("Run at least two scans to compare.")
    else:
        base = st.selectbox("Compare against (older scan)", others)
        diff = compare_runs(db.load_scan(base).findings, scan.findings)
        a, b, c = st.columns(3)
        a.metric("New", len(diff["new"])); b.metric("Resolved", len(diff["resolved"])); c.metric("Persistent", len(diff["persistent"]))
        for label in ("new", "resolved"):
            st.subheader(label.title())
            st.dataframe(pd.DataFrame([{"rule": f.rule_id, "severity": f.severity, "page": f.page_url, "selector": f.selector}
                                       for f in diff[label]]), use_container_width=True)

with tab_e:
    st.download_button("Download JSON", to_json(scan, manual), f"scan_{sel}.json", "application/json")
    st.download_button("Download CSV", to_csv(scan), f"scan_{sel}.csv", "text/csv")
    try:
        st.download_button("Download PDF", to_pdf(scan, manual), f"scan_{sel}.pdf", "application/pdf")
    except Exception as e:
        st.error(f"PDF export failed: {e}")

with tab_s:
    st.json(scan.metadata)
    st.dataframe(pd.DataFrame([{"page": k, **{kk: vv for kk, vv in v.items() if kk != 'dom_summary'}} for k, v in scan.page_status.items()]),
                 use_container_width=True)
