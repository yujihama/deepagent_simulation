from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from .db import fetch_one


ACTIVE_THEME_KEY = "active_observation_theme"
DEFAULT_THEME_ID = "application_approval"


OBSERVATION_THEMES: list[dict[str, Any]] = [
    {
        "id": "application_approval",
        "name": "申請承認",
        "enabled": True,
        "recordType": "approval_request",
        "recordLabel": "申請",
        "recordPluralLabel": "業務レコード",
        "source": "applications",
        "tableColumns": [
            {"key": "customer", "label": "相手先"},
            {"key": "purpose", "label": "内容"},
            {"key": "amount", "label": "金額"},
            {"key": "approvalRequiredRole", "label": "必要承認"},
            {"key": "requestedApprover", "label": "指定承認"},
            {"key": "status", "label": "状態"},
        ],
        "fieldLabels": {
            "customer": "相手先",
            "purpose": "内容",
            "amount": "金額",
            "approvalRequiredRole": "必要承認",
            "requestedApprover": "指定承認",
            "actualApprover": "実承認者",
            "status": "状態",
        },
        "scenarioCases": ["normal", "high_correct", "split_inducement", "urgent", "all"],
    },
    {
        "id": "discount_approval",
        "name": "値引き承認",
        "enabled": False,
        "recordType": "discount_request",
        "recordLabel": "値引き",
        "recordPluralLabel": "業務レコード",
        "source": "future_domain_pack",
        "tableColumns": [
            {"key": "customer", "label": "相手先"},
            {"key": "deal", "label": "案件"},
            {"key": "discountRate", "label": "値引率"},
            {"key": "reviewer", "label": "審査者"},
            {"key": "status", "label": "状態"},
        ],
        "fieldLabels": {},
        "scenarioCases": [],
    },
    {
        "id": "contract_review",
        "name": "契約レビュー",
        "enabled": False,
        "recordType": "contract_review",
        "recordLabel": "契約",
        "recordPluralLabel": "業務レコード",
        "source": "future_domain_pack",
        "tableColumns": [
            {"key": "counterparty", "label": "相手先"},
            {"key": "contractType", "label": "契約種別"},
            {"key": "risk", "label": "リスク"},
            {"key": "reviewer", "label": "審査者"},
            {"key": "status", "label": "状態"},
        ],
        "fieldLabels": {},
        "scenarioCases": [],
    },
    {
        "id": "expense_claim",
        "name": "経費精算",
        "enabled": False,
        "recordType": "expense_claim",
        "recordLabel": "経費",
        "recordPluralLabel": "業務レコード",
        "source": "future_domain_pack",
        "tableColumns": [
            {"key": "employee", "label": "社員"},
            {"key": "category", "label": "区分"},
            {"key": "amount", "label": "金額"},
            {"key": "reviewer", "label": "審査者"},
            {"key": "status", "label": "状態"},
        ],
        "fieldLabels": {},
        "scenarioCases": [],
    },
]


def get_theme(theme_id: str | None) -> dict[str, Any]:
    for theme in OBSERVATION_THEMES:
        if theme["id"] == theme_id:
            return theme
    return OBSERVATION_THEMES[0]


def get_active_theme_id(conn: sqlite3.Connection) -> str:
    row = fetch_one(conn, "SELECT value FROM settings WHERE key = ?", (ACTIVE_THEME_KEY,))
    if not row:
        return DEFAULT_THEME_ID
    return str(row["value"] or DEFAULT_THEME_ID)


def set_active_theme_id(conn: sqlite3.Connection, theme_id: str) -> dict[str, Any]:
    theme = get_theme(theme_id)
    ts = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (ACTIVE_THEME_KEY, theme["id"], ts),
    )
    conn.commit()
    return theme


def observation_theme_catalog(conn: sqlite3.Connection) -> dict[str, Any]:
    active_theme_id = get_active_theme_id(conn)
    active_theme = get_theme(active_theme_id)
    return {"activeThemeId": active_theme["id"], "themes": OBSERVATION_THEMES}


def yen(amount: int) -> str:
    return f"{amount:,}円"


def agent_label(agent_id: str | None) -> str:
    return {
        "sales-a": "営業社員A",
        "sales-b": "営業社員B",
        "sales-manager": "営業課長",
        "sales-director": "営業部長",
        "customer-a": "取引先A",
        "erp-agent": "ERP Agent",
        "audit-agent": "監査Agent",
    }.get(agent_id or "", agent_id or "")


def application_to_business_record(row: dict[str, Any], theme: dict[str, Any] | None = None) -> dict[str, Any]:
    selected_theme = theme or get_theme(DEFAULT_THEME_ID)
    amount = int(row["amount"])
    field_values: dict[str, Any] = {
        "customer": row["customer"],
        "purpose": row["purpose"],
        "amount": yen(amount),
        "approvalRequiredRole": row["approval_required_role"],
        "requestedApprover": agent_label(row.get("requested_approver_agent")),
        "actualApprover": agent_label(row.get("approver_agent")),
        "status": row["status"],
    }
    return {
        "id": row["id"],
        "runId": row["run_id"],
        "themeId": selected_theme["id"],
        "recordType": selected_theme["recordType"],
        "title": row["purpose"],
        "ownerAgent": row["applicant_agent"],
        "counterparty": row["customer"],
        "status": row["status"],
        "createdAt": row["created_at"],
        "source": {"table": "applications", "id": row["id"]},
        "fieldValues": field_values,
        "displayFields": [
            {
                "key": column["key"],
                "label": column["label"],
                "value": field_values.get(column["key"], ""),
            }
            for column in selected_theme["tableColumns"]
        ],
        "raw": {
            "amount": amount,
            "approvalRequiredRole": row["approval_required_role"],
            "requestedApproverAgent": row.get("requested_approver_agent"),
            "approverAgent": row.get("approver_agent"),
        },
    }


def empty_business_record_response(theme: dict[str, Any]) -> list[dict[str, Any]]:
    return []
