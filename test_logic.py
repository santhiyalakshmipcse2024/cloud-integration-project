from a11y_auditor.compare import compare_runs
from a11y_auditor.pipeline import run_scan
from a11y_auditor.prioritization import filter_findings, group_findings
from a11y_auditor.report import to_csv, to_json
from a11y_auditor.storage import Storage
from conftest import FIX


def scan(cfg, rules, name):
    return run_scan([str(FIX / name)], True, cfg, rules, use_browser=False)


def test_pipeline_group_rank_filter(cfg, rules):
    r = scan(cfg, rules, "bad_page.html")
    assert r.scan_id and r.page_status[str(FIX / "bad_page.html")]["status"] == "ok"
    groups = group_findings(r.findings)
    assert groups[0]["score"] >= groups[-1]["score"]
    assert all(f.remediation and not f.remediation["ai_generated"] for f in r.findings)
    assert filter_findings(r.findings, rule="image-alt")
    assert "disclaimer" in to_json(r) and "rule_id" in to_csv(r)


def test_partial_failure_does_not_crash(cfg, rules):
    r = run_scan(["https://evil.org", str(FIX / "good_page.html")], True, cfg, rules, use_browser=False)
    assert r.page_status["https://evil.org"]["status"] == "error"
    assert r.page_status[str(FIX / "good_page.html")]["status"] == "ok"


def test_unauthorized_scan(cfg, rules):
    r = run_scan([str(FIX / "good_page.html")], False, cfg, rules, use_browser=False)
    assert list(r.page_status.values())[0]["status"] == "error"


def test_compare_and_storage(cfg, rules):
    a = scan(cfg, rules, "bad_page.html"); b = scan(cfg, rules, "good_page.html")
    d = compare_runs(a.findings, b.findings)
    assert d["resolved"] and not d["new"]
    db = Storage(cfg.db_path)
    db.save_manual(a.scan_id, "p", "kbd-reach", "pass", "ok", "me")
    db.save_manual(a.scan_id, "p", "kbd-reach", "fail", "changed", "me")
    assert db.load_manual(a.scan_id)[0]["outcome"] == "fail"
    assert len(db.load_scan(a.scan_id).findings) == len(a.findings)
