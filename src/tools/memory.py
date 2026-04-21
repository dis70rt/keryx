"""Episodic memory for the Matchmaker agent.

Stores successful outreach hooks so the Matchmaker can learn from past wins
and generate better angles for similar prospects over time.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class EpisodicMemory:
    """SQLite-backed long-term memory for successful outreach hooks.

    After the Reviewer approves a set of messages, the pipeline records the
    winning hook along with target metadata. Before the Matchmaker generates
    new angles, it queries this table for relevant past successes.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS successful_hooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_industry TEXT,
                    target_title TEXT,
                    target_name TEXT,
                    hook_name TEXT NOT NULL,
                    hook_reasoning TEXT,
                    hook_sentence TEXT NOT NULL,
                    reviewer_approved INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def record_success(
        self,
        target_industry: str,
        target_title: str,
        target_name: str,
        hook_name: str,
        hook_reasoning: str,
        hook_sentence: str,
    ) -> None:
        """Store a hook that passed the Reviewer's quality check."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO successful_hooks
                   (target_industry, target_title, target_name,
                    hook_name, hook_reasoning, hook_sentence, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    target_industry,
                    target_title,
                    target_name,
                    hook_name,
                    hook_reasoning,
                    hook_sentence,
                    now,
                ),
            )

    def recall(
        self,
        target_industry: str = "",
        target_title: str = "",
        limit: int = 3,
    ) -> list[dict]:
        """Retrieve past successful hooks, prioritizing matches by industry/title.

        Returns up to `limit` hooks, ordered by relevance:
        1. Hooks matching both industry AND title
        2. Hooks matching industry only
        3. Hooks matching title only
        4. Any other hooks (most recent first)
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    target_industry,
                    target_title,
                    target_name,
                    hook_name,
                    hook_reasoning,
                    hook_sentence,
                    created_at,
                    CASE
                        WHEN LOWER(target_industry) LIKE ? AND LOWER(target_title) LIKE ? THEN 3
                        WHEN LOWER(target_industry) LIKE ? THEN 2
                        WHEN LOWER(target_title) LIKE ? THEN 1
                        ELSE 0
                    END AS relevance_score
                FROM successful_hooks
                ORDER BY relevance_score DESC, created_at DESC
                LIMIT ?
                """,
                (
                    f"%{target_industry.lower()}%",
                    f"%{target_title.lower()}%",
                    f"%{target_industry.lower()}%",
                    f"%{target_title.lower()}%",
                    limit,
                ),
            ).fetchall()

        return [dict(row) for row in rows]

    def format_for_prompt(self, hooks: list[dict]) -> str:
        """Format recalled hooks into a string suitable for LLM injection.

        Returns an empty string if no hooks are available (so the prompt
        section can be cleanly omitted).
        """
        if not hooks:
            return ""

        parts: list[str] = []
        for i, hook in enumerate(hooks, 1):
            parts.append(
                f"Example {i} (used for {hook['target_title']} in {hook['target_industry']}):\n"
                f"  Angle: {hook['hook_name']}\n"
                f"  Reasoning: {hook['hook_reasoning']}\n"
                f"  Hook: {hook['hook_sentence']}"
            )

        return "PAST SUCCESSFUL HOOKS (learn from these):\n\n" + "\n\n".join(parts)
