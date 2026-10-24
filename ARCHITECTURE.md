# Architecture

```
app.py (Streamlit UI)  /  scripts/cli.py
        │
   pipeline.py ── orchestrates ──┐
        │                        │
 security.py   scope, authorization, SSRF guard, robots.txt, rate limit
 ingestion.py  Playwright render (+axe-core) or static fallback
 dom_analysis.py  BeautifulSoup: headings/labels/links/images/forms + selectors + context
 checks.py     built-in rules + axe-core normalisation + de-duplication
 prioritization.py  severity × confidence score, grouping, filters
 remediation.py  LLMAdapter (Anthropic / none) + rule knowledge base; AI output labelled
 manual_review.py  keyboard / focus / screen-reader checklist
 storage.py    SQLite: scans, findings, manual outcomes (history)
 compare.py    repeat-scan diff (new / resolved / persistent by fingerprint)
 report.py     JSON / CSV / PDF export with metadata
```

**Business rules** (severity, confidence, WCAG refs, user impact, fixes) live in `config/rules.json`.
**Runtime settings** live in environment variables (`.env.example`).

## Data flow
1. Targets validated (authorization + allowed domain / approved local dir + private-IP block + robots.txt).
2. Page rendered (or fetched statically); axe-core run if `vendor/axe.min.js` exists.
3. Findings produced (built-in rules; axe results replace overlapping built-in rules).
4. Findings grouped by `(rule, page, selector-without-indexes)`; one remediation per group (LLM calls bounded by `A11Y_LLM_MAX_ITEMS`).
5. Result stored; UI shows evidence, guidance (AI vs rule-based labelled), manual review, diff, export.

## Responsible AI
- Every remediation records `ai_generated`, `origin`, evidence (selector + HTML) and a disclaimer.
- The LLM only sees one finding's snippet/context, never full pages or credentials.
- Fallback to rule-based guidance on any AI failure.
- Manual outcomes are stored in a separate table and labelled `manual`.
