"""SQLite persistence (scan history, findings, manual review outcomes)."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .models import Finding, ScanResult, now_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans(id INTEGER PRIMARY KEY, started TEXT, finished TEXT, targets TEXT, page_status TEXT, metadata TEXT);
CREATE TABLE IF NOT EXISTS findings(id INTEGER PRIMARY KEY, scan_id INTEGER, fingerprint TEXT, page_url TEXT, rule_id TEXT, data TEXT);
CREATE INDEX IF NOT EXISTS idx_f_scan ON findings(scan_id);
CREATE TABLE IF NOT EXISTS manual(id INTEGER PRIMARY KEY, scan_id INTEGER, page_url TEXT, check_id TEXT, outcome TEXT, notes TEXT, tester TEXT, ts TEXT,
  UNIQUE(scan_id, page_url, check_id));
"""


class Storage:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save_scan(self, r: ScanResult) -> int:
        with self._conn() as c:
            cur = c.execute("INSERT INTO scans(started,finished,targets,page_status,metadata) VALUES(?,?,?,?,?)",
                            (r.started, r.finished, json.dumps(r.targets), json.dumps(r.page_status), json.dumps(r.metadata)))
            sid = cur.lastrowid
            c.executemany("INSERT INTO findings(scan_id,fingerprint,page_url,rule_id,data) VALUES(?,?,?,?,?)",
                          [(sid, f.fingerprint, f.page_url, f.rule_id, json.dumps(f.to_dict())) for f in r.findings])
        r.scan_id = sid
        return sid

    def list_scans(self, limit: int = 50) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("""SELECT s.id, s.started, s.targets, (SELECT COUNT(*) FROM findings f WHERE f.scan_id=s.id) n
                                FROM scans s ORDER BY s.id DESC LIMIT ?""", (limit,)).fetchall()
        return [{"id": r["id"], "started": r["started"], "targets": json.loads(r["targets"]), "findings": r["n"]} for r in rows]

    def load_scan(self, scan_id: int) -> ScanResult | None:
        with self._conn() as c:
            s = c.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
            if not s:
                return None
            fr = c.execute("SELECT data FROM findings WHERE scan_id=? ORDER BY id", (scan_id,)).fetchall()
        return ScanResult(scan_id, s["started"], s["finished"], json.loads(s["targets"]),
                          [Finding.from_dict(json.loads(r["data"])) for r in fr],
                          json.loads(s["page_status"]), json.loads(s["metadata"]))

    def previous_scan_id(self, targets: list[str], before_id: int) -> int | None:
        key = json.dumps(sorted(targets))
        with self._conn() as c:
            for r in c.execute("SELECT id, targets FROM scans WHERE id<? ORDER BY id DESC", (before_id,)):
                if json.dumps(sorted(json.loads(r["targets"]))) == key:
                    return r["id"]
        return None

    def save_manual(self, scan_id: int, page_url: str, check_id: str, outcome: str, notes: str = "", tester: str = ""):
        with self._conn() as c:
            c.execute("""INSERT INTO manual(scan_id,page_url,check_id,outcome,notes,tester,ts) VALUES(?,?,?,?,?,?,?)
                         ON CONFLICT(scan_id,page_url,check_id) DO UPDATE SET outcome=excluded.outcome,
                         notes=excluded.notes, tester=excluded.tester, ts=excluded.ts""",
                      (scan_id, page_url, check_id, outcome, notes, tester, now_iso()))

    def load_manual(self, scan_id: int) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM manual WHERE scan_id=? ORDER BY page_url, check_id", (scan_id,)).fetchall()
        return [dict(r, source="manual") for r in rows]
