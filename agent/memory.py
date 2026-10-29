from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MemoryStore:
    """SQLite-backed conversation, task, and session-state memory."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id, id);
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'normal',
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_session
                    ON tasks(session_id, status, id);
                CREATE TABLE IF NOT EXISTS session_state (
                    session_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO messages(session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, self._now()),
            )

    def history(self, session_id: str, limit: int = 12) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def get_state(self, session_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM session_state WHERE session_id = ?", (session_id,)
            ).fetchone()
        return json.loads(row["state_json"]) if row else {}

    def set_state(self, session_id: str, state: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO session_state(session_id, state_json) VALUES (?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET state_json = excluded.state_json",
                (session_id, json.dumps(state, ensure_ascii=False)),
            )

    def add_task(self, session_id: str, title: str, priority: str = "normal") -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO tasks(session_id, title, priority, created_at) VALUES (?, ?, ?, ?)",
                (session_id, title, priority, self._now()),
            )
            task_id = cursor.lastrowid
        return {"task_id": task_id, "title": title, "priority": priority, "status": "pending"}

    def list_tasks(self, session_id: str, status: str = "pending") -> list[dict[str, Any]]:
        query = "SELECT * FROM tasks WHERE session_id = ?"
        params: list[Any] = [session_id]
        if status != "all":
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY id"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def complete_task(self, session_id: str, task_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE session_id = ? AND id = ?", (session_id, task_id)
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE tasks SET status = 'done', completed_at = ? WHERE id = ?",
                (self._now(), task_id),
            )
        return {"task_id": task_id, "title": row["title"], "status": "done"}
