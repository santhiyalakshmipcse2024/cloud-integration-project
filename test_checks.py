from a11y_auditor.checks import run_builtin_checks, normalise_axe, merge_with_axe
from conftest import FIX


def ids(html, rules):
    return {f.rule_id for f in run_builtin_checks(html, "p", rules)}


def test_bad_page_detects_issues(rules):
    found = ids((FIX / "bad_page.html").read_text(), rules)
    assert {"html-lang", "document-title", "image-alt", "image-alt-suspicious", "link-name", "link-generic-text",
            "button-name", "form-label", "heading-h1", "heading-order", "landmark-main", "duplicate-id"} <= found


def test_good_page_clean(rules):
    assert ids((FIX / "good_page.html").read_text(), rules) == set()


def test_placeholder_is_not_label(rules):
    fs = run_builtin_checks('<html lang=en><title>t</title><body><main><h1>x</h1><input placeholder="Name"></main></body></html>', "p", rules)
    assert [f.rule_id for f in fs] == ["form-label"]


def test_axe_normalisation_and_dedupe(rules):
    axe = {"violations": [{"id": "image-alt", "impact": "critical", "help": "Images need alt", "helpUrl": "u",
                           "tags": ["wcag111"], "nodes": [{"target": ["img"], "html": "<img>"}]}], "incomplete": []}
    ax = normalise_axe(axe, "p")
    assert ax[0].rule_id == "axe:image-alt" and ax[0].severity == "critical"
    builtin = run_builtin_checks('<html lang=en><title>t</title><body><main><h1>x</h1><img src=a></main></body></html>', "p", rules)
    merged = merge_with_axe(builtin, ax, rules)
    assert [f.rule_id for f in merged] == ["axe:image-alt"]
