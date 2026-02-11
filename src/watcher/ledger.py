"""Download ledger for Watcher to avoid duplicate work."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Tuple


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS downloads (
    guid TEXT PRIMARY KEY,
    feed_id TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class DownloadLedger:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(CREATE_TABLE_SQL)
        self._conn.commit()

    def has_guid(self, guid: str) -> bool:
        cur = self._conn.execute("SELECT 1 FROM downloads WHERE guid = ?", (guid,))
        return cur.fetchone() is not None

    def record(self, guid: str, feed_id: str, stored_path: Path) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO downloads (guid, feed_id, stored_path) VALUES (?, ?, ?)",
            (guid, feed_id, str(stored_path)),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def iter_downloads(db_path: Path) -> Iterable[Tuple[str, str]]:
    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT guid, stored_path FROM downloads")
    return cur.fetchall()
