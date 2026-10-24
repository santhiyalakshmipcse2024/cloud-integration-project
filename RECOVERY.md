# Recovery steps
- **Interrupted scan:** pages are processed one by one; per-page failures are recorded in *Scan status* and do not stop the run. Results are saved only when the scan completes, so simply re-run the scan (rate limiting prevents hammering the site).
- **Rate-limited (HTTP 429) / timeout:** increase `A11Y_MIN_DELAY_S` / `A11Y_TIMEOUT_S`, reduce `A11Y_MAX_PAGES`, retry later.
- **AI service down / quota:** findings still include rule-based guidance; re-run with AI enabled later.
- **Playwright missing:** `playwright install chromium`; otherwise the tool falls back to static HTML.
- **Corrupt DB:** history lives in `data/auditor.db`; exports (JSON/CSV/PDF) are the portable backup. Delete the file to start fresh.
