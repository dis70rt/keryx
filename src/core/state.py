import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class StateManager:
    """SQLite-backed fault-tolerance cache tracking processed LinkedIn URLs."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed (
                    linkedin_url TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'pending',
                    connection_note TEXT,
                    dm_message TEXT,
                    error_message TEXT,
                    processed_at TEXT
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def is_processed(self, url: str) -> bool:
        """Check if a URL has been successfully processed."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT status FROM processed WHERE linkedin_url = ?", (url,)
            ).fetchone()
        return row is not None and row[0] == "done"

    def mark_success(
        self, url: str, connection_note: str, dm_message: str
    ) -> None:
        """Record a successful processing result."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO processed
                   (linkedin_url, status, connection_note, dm_message, processed_at)
                   VALUES (?, 'done', ?, ?, ?)""",
                (url, connection_note, dm_message, now),
            )

    def mark_failed(self, url: str, error: str) -> None:
        """Record a processing failure for later retry."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO processed
                   (linkedin_url, status, error_message, processed_at)
                   VALUES (?, 'failed', ?, ?)""",
                (url, error, now),
            )

    def get_cached_result(self, url: str) -> dict | None:
        """Retrieve cached connection_note and dm_message for a URL."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT connection_note, dm_message FROM processed WHERE linkedin_url = ? AND status = 'done'",
                (url,),
            ).fetchone()
        if row:
            return {"connection_note": row[0], "dm_message": row[1]}
        return None
