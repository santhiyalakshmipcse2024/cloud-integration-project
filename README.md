# ♿ AI-Powered Website Accessibility Auditor

Scan selected pages for common accessibility issues, get prioritised findings with AI-assisted remediation,
record manual keyboard / focus / screen-reader checks, compare repeat scans and export reports.

> **Automated scans do not replace manual testing.** This tool never claims WCAG compliance.

## Features
| Requirement | Implementation |
|---|---|
| Page input & scope | Public URLs or approved local HTML; domain allow-list, authorization checkbox, private-IP block, robots.txt |
| DOM analysis | BeautifulSoup collects headings, labels, links, images, forms with CSS selectors + context; Playwright renders dynamic pages |
| Automated checks | axe-core (if installed) + built-in rules (alt text, labels, link names, headings, lang, title, landmarks, duplicate ids) |
| AI remediation | Pluggable `LLMAdapter` (Anthropic included) → user impact, fix, sample markup; labelled AI vs rule-based; offline fallback |
| Prioritisation | Severity × confidence score, grouping of repeated components, filters by page/rule/severity/confidence |
| Manual review | 12-item keyboard/focus/screen-reader/visual checklist, outcomes stored separately |
| Dashboard & report | Streamlit evidence view; JSON / CSV / PDF export with metadata |
| Repeat scan | SQLite history, new/resolved/persistent diff, rate limiting |

## Quick start
```bash
git clone https://github.com/<you>/a11y-auditor.git && cd a11y-auditor
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
playwright install chromium
python scripts/setup_axe.py                             # downloads axe-core into ./vendor
cp .env.example .env                                    # set A11Y_ALLOWED_DOMAINS etc.
streamlit run app.py
```
Try without a website: put an HTML file in `data/approved_html/`, tick *authorized*, scan its path.

CLI: `python scripts/cli.py --authorized data/approved_html/demo.html --format pdf`

Enable AI: `A11Y_LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=...` in `.env` (never commit it).
To use another provider, subclass `LLMAdapter` in `remediation.py`.

Docker: `docker build -t a11y-auditor . && docker run -p 8501:8501 --env-file .env a11y-auditor`

## Tests
`pytest -q` (offline; uses local fixtures, no browser needed).

## Configuration
Environment variables: see `.env.example`. Rule severity/confidence/guidance: `config/rules.json`.

## Compatibility
Python 3.10–3.12; Windows, macOS, Linux; Chromium via Playwright; axe-core 4.x; Streamlit ≥ 1.36.

## Security & privacy
Credentials only via environment; scans restricted to configured domains/dirs; only one finding's snippet is sent to the LLM;
no secrets or page bodies are logged; CSV export neutralises formula injection. Scan only sites you are authorized to test.

## Docs
[Architecture](docs/ARCHITECTURE.md) · [Limitations](docs/LIMITATIONS.md) · [Recovery](docs/RECOVERY.md)

## License
MIT
