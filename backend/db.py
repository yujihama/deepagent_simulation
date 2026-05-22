from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("DEEP_AGENT_SIM_DB", ROOT_DIR / "deep_agent_simulation.sqlite3"))


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path or DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            persona TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            allowed_tools TEXT NOT NULL DEFAULT '[]',
            document_ids TEXT NOT NULL DEFAULT '[]',
            model_override TEXT,
            memory TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            body TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scenario_runs (
            id TEXT PRIMARY KEY,
            case_type TEXT NOT NULL,
            status TEXT NOT NULL,
            outcome TEXT NOT NULL DEFAULT '',
            active_agents TEXT NOT NULL DEFAULT '[]',
            started_at TEXT NOT NULL,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            from_agent TEXT NOT NULL,
            to_agent TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            related_application_id TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES scenario_runs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            applicant_agent TEXT NOT NULL,
            customer TEXT NOT NULL,
            purpose TEXT NOT NULL,
            amount INTEGER NOT NULL,
            split_group_key TEXT NOT NULL,
            approval_required_role TEXT NOT NULL,
            approver_agent TEXT,
            status TEXT NOT NULL,
            erp_response TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES scenario_runs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS run_events (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            source_agent TEXT NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            tool_name TEXT,
            status TEXT NOT NULL DEFAULT 'info',
            payload TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(run_id) REFERENCES scenario_runs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS audit_reports (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL UNIQUE,
            violation_flags TEXT NOT NULL DEFAULT '[]',
            split_suspicion INTEGER NOT NULL DEFAULT 0,
            approval_correctness TEXT NOT NULL,
            evidence_messages TEXT NOT NULL DEFAULT '[]',
            final_assessment TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES scenario_runs(id) ON DELETE CASCADE
        );
        """
    )
    application_columns = {row["name"] for row in conn.execute("PRAGMA table_info(applications)").fetchall()}
    if "requested_approver_agent" not in application_columns:
        conn.execute("ALTER TABLE applications ADD COLUMN requested_approver_agent TEXT")
    conn.commit()


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def fetch_all(conn: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    return [row_to_dict(row) for row in conn.execute(sql, tuple(params)).fetchall()]


def fetch_one(conn: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    row = conn.execute(sql, tuple(params)).fetchone()
    return row_to_dict(row) if row else None
