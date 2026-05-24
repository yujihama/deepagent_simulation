from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Iterable

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .db import connect, dumps, fetch_all, fetch_one, init_db, now_iso
from .deepagent_adapter import runtime_status
from .domain_config import application_to_business_record, get_theme, observation_theme_catalog, set_active_theme_id
from .scenario import (
    ScenarioEngine,
    new_id,
    normalize_agent,
    normalize_application,
    normalize_audit,
    normalize_document,
    normalize_event,
    normalize_message,
    normalize_run,
)
from .scenario_config import get_scenario_initial_instructions, save_scenario_initial_instructions
from .schemas import (
    AgentUpdate,
    ApprovalSettings,
    DocumentUpdate,
    MessageCreate,
    ObservationThemeUpdate,
    ScenarioInitialInstructionUpdate,
    ScenarioRunRequest,
)
from .seed import seed_defaults


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect()
    init_db(conn)
    seed_defaults(conn)
    app.state.conn = conn
    try:
        yield
    finally:
        conn.close()


app = FastAPI(title="DeepAgent Simulation API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:5175", "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn() -> sqlite3.Connection:
    return app.state.conn


def execute_scenario_in_background(run_id: str, case_type: str, mode: str) -> None:
    conn = connect()
    try:
        engine = ScenarioEngine(conn)
        engine.execute_run(run_id, case_type, mode)
    finally:
        conn.close()


def stream_run_events(run_id: str, poll_seconds: float = 0.25) -> Iterable[str]:
    conn = connect()
    last_rowid = 0
    try:
        while True:
            rows = fetch_all(
                conn,
                """
                SELECT rowid AS event_rowid, *
                FROM run_events
                WHERE run_id = ? AND rowid > ?
                ORDER BY rowid
                """,
                (run_id, last_rowid),
            )
            for row in rows:
                last_rowid = int(row["event_rowid"])
                yield f"event: run_event\ndata: {dumps(normalize_event(row))}\n\n"

            run = fetch_one(conn, "SELECT status FROM scenario_runs WHERE id = ?", (run_id,))
            if not run:
                yield "event: error\ndata: {\"message\":\"run not found\"}\n\n"
                return
            if run["status"] in {"completed", "failed", "aborted"} and not rows:
                yield "event: done\ndata: {}\n\n"
                return

            yield "event: ping\ndata: {}\n\n"
            time.sleep(poll_seconds)
    finally:
        conn.close()


@app.get("/api/runtime")
def get_runtime() -> dict[str, Any]:
    status = runtime_status()
    return {
        "openaiKeyAvailable": status.openai_key_available,
        "deepagentsAvailable": status.deepagents_available,
        "model": status.model,
        "liveReady": status.live_ready,
        "message": status.message,
    }


@app.get("/api/agents")
def list_agents(conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    rows = fetch_all(conn, "SELECT * FROM agents ORDER BY created_at")
    return [normalize_agent(row) for row in rows]


@app.post("/api/agents")
def create_agent(payload: AgentUpdate, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    agent_id = new_id("agent")
    ts = now_iso()
    conn.execute(
        """
        INSERT INTO agents (
            id, name, role, persona, status, allowed_tools, document_ids,
            model_override, memory, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            agent_id,
            payload.name,
            payload.role,
            payload.persona,
            payload.status,
            dumps(payload.allowedTools),
            dumps(payload.documentIds),
            payload.modelOverride,
            payload.memory,
            ts,
            ts,
        ),
    )
    conn.commit()
    row = fetch_one(conn, "SELECT * FROM agents WHERE id = ?", (agent_id,))
    return normalize_agent(row or {})


@app.put("/api/agents/{agent_id}")
def update_agent(agent_id: str, payload: AgentUpdate, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    ts = now_iso()
    cur = conn.execute(
        """
        UPDATE agents
        SET name = ?, role = ?, persona = ?, status = ?, allowed_tools = ?,
            document_ids = ?, model_override = ?, memory = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            payload.name,
            payload.role,
            payload.persona,
            payload.status,
            dumps(payload.allowedTools),
            dumps(payload.documentIds),
            payload.modelOverride,
            payload.memory,
            ts,
            agent_id,
        ),
    )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="agent not found")
    conn.commit()
    row = fetch_one(conn, "SELECT * FROM agents WHERE id = ?", (agent_id,))
    return normalize_agent(row or {})


@app.get("/api/documents")
def list_documents(conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    rows = fetch_all(conn, "SELECT * FROM documents ORDER BY created_at")
    return [normalize_document(row) for row in rows]


@app.post("/api/documents")
def create_document(payload: DocumentUpdate, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    doc_id = new_id("doc")
    ts = now_iso()
    conn.execute(
        """
        INSERT INTO documents (id, title, category, body, enabled, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (doc_id, payload.title, payload.category, payload.body, int(payload.enabled), ts, ts),
    )
    conn.commit()
    row = fetch_one(conn, "SELECT * FROM documents WHERE id = ?", (doc_id,))
    return normalize_document(row or {})


@app.put("/api/documents/{document_id}")
def update_document(document_id: str, payload: DocumentUpdate, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    ts = now_iso()
    cur = conn.execute(
        """
        UPDATE documents
        SET title = ?, category = ?, body = ?, enabled = ?, updated_at = ?
        WHERE id = ?
        """,
        (payload.title, payload.category, payload.body, int(payload.enabled), ts, document_id),
    )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="document not found")
    conn.commit()
    row = fetch_one(conn, "SELECT * FROM documents WHERE id = ?", (document_id,))
    return normalize_document(row or {})


@app.get("/api/settings")
def get_settings(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    row = fetch_one(conn, "SELECT value FROM settings WHERE key = 'approval'")
    return {"approval": ApprovalSettings.model_validate_json(row["value"]).model_dump()} if row else {"approval": ApprovalSettings().model_dump()}


@app.put("/api/settings")
def update_settings(payload: ApprovalSettings, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    ts = now_iso()
    conn.execute(
        """
        INSERT INTO settings (key, value, updated_at)
        VALUES ('approval', ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (payload.model_dump_json(), ts),
    )
    conn.commit()
    return {"approval": payload.model_dump()}


@app.get("/api/observation-themes")
def list_observation_themes(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    return observation_theme_catalog(conn)


@app.put("/api/observation-theme")
def update_observation_theme(payload: ObservationThemeUpdate, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    theme = get_theme(payload.themeId)
    if theme["id"] != payload.themeId:
        raise HTTPException(status_code=404, detail="observation theme not found")
    if not theme.get("enabled"):
        raise HTTPException(status_code=400, detail="observation theme is a template only")
    set_active_theme_id(conn, theme["id"])
    return observation_theme_catalog(conn)


@app.get("/api/scenario-instructions")
def list_scenario_instructions(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, list[dict[str, Any]]]:
    return get_scenario_initial_instructions(conn)


@app.put("/api/scenario-instructions/{case_type}")
def update_scenario_instructions(
    case_type: str,
    payload: ScenarioInitialInstructionUpdate,
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, list[dict[str, Any]]]:
    if case_type not in {"normal", "high_correct", "split_inducement", "urgent"}:
        raise HTTPException(status_code=404, detail="scenario case not found")
    config = get_scenario_initial_instructions(conn)
    config[case_type] = [item.model_dump() for item in payload.instructions]
    return save_scenario_initial_instructions(conn, config)


@app.post("/api/scenarios/run")
def run_scenario(payload: ScenarioRunRequest, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    status = runtime_status()
    mode = payload.mode
    if mode == "live" and not status.live_ready:
        mode = "mock"
    engine = ScenarioEngine(conn)
    run = engine.start_run(payload.caseType)
    worker = threading.Thread(target=execute_scenario_in_background, args=(run["id"], payload.caseType, mode), daemon=True)
    worker.start()
    run["runtime"] = {
        "requestedMode": payload.mode,
        "actualMode": mode,
        "message": status.message,
    }
    return run


@app.get("/api/scenarios/{run_id}")
def get_scenario(run_id: str, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    row = fetch_one(conn, "SELECT * FROM scenario_runs WHERE id = ?", (run_id,))
    if not row:
        raise HTTPException(status_code=404, detail="run not found")
    return normalize_run(row)


@app.get("/api/scenarios/{run_id}/stream")
def stream_scenario(run_id: str) -> StreamingResponse:
    return StreamingResponse(stream_run_events(run_id), media_type="text/event-stream")


@app.get("/api/scenarios/{run_id}/events")
def list_run_events(run_id: str, conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    run = fetch_one(conn, "SELECT id FROM scenario_runs WHERE id = ?", (run_id,))
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    rows = fetch_all(conn, "SELECT * FROM run_events WHERE run_id = ? ORDER BY timestamp", (run_id,))
    return [normalize_event(row) for row in rows]


@app.get("/api/scenarios")
def list_scenarios(conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    rows = fetch_all(conn, "SELECT * FROM scenario_runs ORDER BY started_at DESC LIMIT 20")
    return [normalize_run(row) for row in rows]


@app.post("/api/messages")
def post_message(payload: MessageCreate, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    run = fetch_one(conn, "SELECT id FROM scenario_runs WHERE id = ?", (payload.runId,))
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    engine = ScenarioEngine(conn)
    msg = engine.message(
        payload.runId,
        payload.fromAgent,
        payload.toAgent,
        payload.subject,
        payload.body,
        payload.relatedApplicationId,
    )
    conn.commit()
    return normalize_message(msg)


@app.get("/api/messages")
def list_messages(
    run_id: str | None = Query(default=None, alias="runId"),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[dict[str, Any]]:
    if run_id:
        rows = fetch_all(conn, "SELECT * FROM messages WHERE run_id = ? ORDER BY timestamp", (run_id,))
    else:
        rows = fetch_all(conn, "SELECT * FROM messages ORDER BY timestamp DESC LIMIT 100")
    return [normalize_message(row) for row in rows]


@app.get("/api/applications")
def list_applications(
    run_id: str | None = Query(default=None, alias="runId"),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[dict[str, Any]]:
    if run_id:
        rows = fetch_all(conn, "SELECT * FROM applications WHERE run_id = ? ORDER BY created_at", (run_id,))
    else:
        rows = fetch_all(conn, "SELECT * FROM applications ORDER BY created_at DESC LIMIT 100")
    return [normalize_application(row) for row in rows]


@app.get("/api/business-records")
def list_business_records(
    run_id: str | None = Query(default=None, alias="runId"),
    conn: sqlite3.Connection = Depends(get_conn),
) -> list[dict[str, Any]]:
    catalog = observation_theme_catalog(conn)
    theme = get_theme(catalog["activeThemeId"])
    if theme["id"] != "application_approval":
        return []
    if run_id:
        rows = fetch_all(conn, "SELECT * FROM applications WHERE run_id = ? ORDER BY created_at", (run_id,))
    else:
        rows = []
    return [application_to_business_record(row, theme) for row in rows]


@app.get("/api/audit-reports/{run_id}")
def get_audit_report(run_id: str, conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    row = fetch_one(conn, "SELECT * FROM audit_reports WHERE run_id = ?", (run_id,))
    if not row:
        raise HTTPException(status_code=404, detail="audit report not found")
    return normalize_audit(row)


@app.post("/api/dev/reset-seed")
def reset_seed(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    seed_defaults(conn, reset=True)
    return {"status": "ok"}
