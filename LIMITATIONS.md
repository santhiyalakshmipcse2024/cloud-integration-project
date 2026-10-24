# Known limitations
- Automated tools find only a portion of WCAG issues; **passing a scan ≠ compliant**.
- Not covered automatically: colour contrast in built-in rules (axe covers some), keyboard operability, focus order, meaningful alt-text quality, reading order, cognitive load, media captions.
- Dynamic content: only the state after `networkidle` is scanned; content behind clicks, logins, or infinite scroll is not.
- Static fallback (no Playwright) does not execute JavaScript.
- Accessible-name computation is simplified (not the full W3C algorithm); axe-core is more accurate where available.
- Suspicious-alt and generic-link-text rules are heuristics (low/medium confidence).
- AI suggestions can be wrong or context-blind; always review before shipping.
- Single-page scans only (no crawling) by design, to respect scope and rate limits.
