"""Cross-session learning database.

Persists knowledge across runs so the system gets cheaper over time:
- Selector history: which CSS selectors work for which OA pages
- Task history: what tier was used, how long it took, success/failure
- UI patterns: learned behaviors (e.g., "after Save, a modal appears")
- Error solutions: known fixes for common errors
"""

import json
import sqlite3
import time
from pathlib import Path

from core.config import LEARNING_DB_PATH


def _ensure_dir():
    LEARNING_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class LearningDB:
    """SQLite-backed learning memory for Options-Claw."""

    def __init__(self, db_path: Path = LEARNING_DB_PATH):
        _ensure_dir()
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS selector_history (
                page TEXT,
                element TEXT,
                selector TEXT,
                last_verified TEXT,
                failure_count INTEGER DEFAULT 0,
                PRIMARY KEY (page, element)
            );

            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT,
                parameters TEXT,
                tier_used INTEGER,
                duration_seconds INTEGER,
                cost_estimate REAL,
                success INTEGER,
                error_message TEXT,
                timestamp TEXT
            );

            CREATE TABLE IF NOT EXISTS ui_patterns (
                page TEXT,
                pattern TEXT,
                confidence REAL DEFAULT 0.5,
                last_seen TEXT,
                PRIMARY KEY (page, pattern)
            );

            CREATE TABLE IF NOT EXISTS error_solutions (
                error_pattern TEXT PRIMARY KEY,
                solution TEXT,
                success_rate REAL DEFAULT 0.0,
                times_used INTEGER DEFAULT 0
            );
        """)
        self.conn.commit()

    # ---- Selector management ----

    def get_selector(self, page: str, element: str) -> str | None:
        """Get the current best selector for a page element."""
        row = self.conn.execute(
            "SELECT selector FROM selector_history WHERE page=? AND element=? AND failure_count < 3",
            (page, element),
        ).fetchone()
        return row["selector"] if row else None

    def selector_confidence(self, page: str, element: str = None) -> float:
        """Get confidence score for selectors on a page (0.0-1.0)."""
        if element:
            row = self.conn.execute(
                "SELECT failure_count FROM selector_history WHERE page=? AND element=?",
                (page, element),
            ).fetchone()
            if not row:
                return 0.0
            return max(0.0, 1.0 - row["failure_count"] * 0.3)

        rows = self.conn.execute(
            "SELECT failure_count FROM selector_history WHERE page=?", (page,)
        ).fetchall()
        if not rows:
            return 0.0
        avg_failures = sum(r["failure_count"] for r in rows) / len(rows)
        return max(0.0, 1.0 - avg_failures * 0.2)

    def record_selector_success(self, page: str, element: str, selector: str):
        """Record that a selector worked."""
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.conn.execute(
            """INSERT INTO selector_history (page, element, selector, last_verified, failure_count)
               VALUES (?, ?, ?, ?, 0)
               ON CONFLICT(page, element) DO UPDATE SET
                   selector=excluded.selector, last_verified=excluded.last_verified, failure_count=0""",
            (page, element, selector, now),
        )
        self.conn.commit()

    def record_selector_failure(self, page: str, element: str):
        """Record that a selector failed."""
        self.conn.execute(
            """UPDATE selector_history SET failure_count = failure_count + 1
               WHERE page=? AND element=?""",
            (page, element),
        )
        self.conn.commit()

    def record_new_selector(self, page: str, element: str, selector: str):
        """Record a new selector discovered by Computer Use (Tier 3)."""
        self.record_selector_success(page, element, selector)

    # ---- Task history ----

    def record_task(self, task_type: str, parameters: dict, tier: int,
                    duration_s: int, cost: float, success: bool,
                    error_msg: str = None):
        """Record a completed task for cost/performance analysis."""
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.conn.execute(
            """INSERT INTO task_history
               (task_type, parameters, tier_used, duration_seconds, cost_estimate, success, error_message, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_type, json.dumps(parameters), tier, duration_s, cost, int(success), error_msg, now),
        )
        self.conn.commit()

    def get_task_stats(self, task_type: str) -> dict:
        """Get aggregate stats for a task type."""
        rows = self.conn.execute(
            "SELECT tier_used, AVG(duration_seconds) as avg_dur, AVG(cost_estimate) as avg_cost, "
            "SUM(success) as successes, COUNT(*) as total "
            "FROM task_history WHERE task_type=? GROUP BY tier_used",
            (task_type,),
        ).fetchall()
        return {r["tier_used"]: dict(r) for r in rows}

    # ---- UI patterns ----

    def record_pattern(self, page: str, pattern: str, confidence: float = 0.5):
        """Record or update a UI behavior pattern."""
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.conn.execute(
            """INSERT INTO ui_patterns (page, pattern, confidence, last_seen)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(page, pattern) DO UPDATE SET
                   confidence = MIN(1.0, ui_patterns.confidence + 0.1),
                   last_seen = excluded.last_seen""",
            (page, pattern, confidence, now),
        )
        self.conn.commit()

    def get_patterns(self, page: str) -> list[dict]:
        """Get known UI patterns for a page."""
        rows = self.conn.execute(
            "SELECT pattern, confidence FROM ui_patterns WHERE page=? AND confidence > 0.3 ORDER BY confidence DESC",
            (page,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- Error solutions ----

    def get_error_solution(self, error_pattern: str) -> str | None:
        """Look up a known solution for an error pattern."""
        row = self.conn.execute(
            "SELECT solution, success_rate FROM error_solutions WHERE error_pattern=? AND success_rate > 0.3",
            (error_pattern,),
        ).fetchone()
        return row["solution"] if row else None

    def record_error_solution(self, error_pattern: str, solution: str, worked: bool):
        """Record whether a solution worked for an error."""
        existing = self.conn.execute(
            "SELECT times_used, success_rate FROM error_solutions WHERE error_pattern=?",
            (error_pattern,),
        ).fetchone()

        if existing:
            n = existing["times_used"]
            old_rate = existing["success_rate"]
            new_rate = (old_rate * n + (1.0 if worked else 0.0)) / (n + 1)
            self.conn.execute(
                "UPDATE error_solutions SET solution=?, success_rate=?, times_used=? WHERE error_pattern=?",
                (solution, new_rate, n + 1, error_pattern),
            )
        else:
            self.conn.execute(
                "INSERT INTO error_solutions (error_pattern, solution, success_rate, times_used) VALUES (?, ?, ?, 1)",
                (error_pattern, solution, 1.0 if worked else 0.0),
            )
        self.conn.commit()

    # ---- Promotion pipeline ----

    def get_promotion_candidates(self) -> list[dict]:
        """Find tasks that Computer Use handled 3+ times with same pattern.

        These are candidates for Playwright automation (cost reduction).
        """
        rows = self.conn.execute(
            """SELECT task_type, parameters, COUNT(*) as times
               FROM task_history
               WHERE tier_used = 3 AND success = 1
               GROUP BY task_type, parameters
               HAVING COUNT(*) >= 3
               ORDER BY times DESC""",
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
