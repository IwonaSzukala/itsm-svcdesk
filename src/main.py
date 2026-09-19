# ai-generated: 100% - generated with AI from the course API contract and reviewed by the student

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, time, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from starlette.exceptions import HTTPException as StarletteHTTPException


app = FastAPI()

WARSAW = ZoneInfo("Europe/Warsaw")
DB_PATH = os.getenv("SVCDESK_DB", "./svcdesk.db")

C1 = "wallclock"
C2 = "immutable"
C3 = "vip"


class Reporter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=100)
    email: Optional[str] = None
    vip: bool = False


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    reporter: Reporter
    impact: StrictInt = Field(ge=1, le=3)
    urgency: StrictInt = Field(ge=1, le=3)
    related_to: Optional[str] = None


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )


init_db()


def error_response(status: int, code: str, message: str):
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return error_response(422, "validation", "request validation failed")


@app.exception_handler(StarletteHTTPException)
async def http_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return error_response(404, "not_found", "resource not found")
    return error_response(exc.status_code, "http_error", str(exc.detail))


def parse_instant(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("invalid timestamp")

    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")

    return parsed.astimezone(timezone.utc)


def now_for_request(request: Request) -> datetime:
    enabled = os.getenv("SVCDESK_TEST_CLOCK", "").lower() in ("1", "true")

    if enabled:
        value = request.headers.get("X-Test-Clock")
        if value:
            return parse_instant(value)

    return datetime.now(timezone.utc)


def format_instant(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def save_ticket(ticket: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO tickets(id, payload) VALUES (?, ?)",
            (ticket["id"], json.dumps(ticket)),
        )


def load_ticket(ticket_id: str) -> Optional[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT payload FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

    if not row:
        return None

    return json.loads(row[0])


def load_all_tickets() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT payload FROM tickets").fetchall()

    return [json.loads(row[0]) for row in rows]


def priority_for(impact: int, urgency: int, vip: bool) -> str:
    matrix = {
        (1, 1): "P1",
        (1, 2): "P2",
        (1, 3): "P3",
        (2, 1): "P2",
        (2, 2): "P3",
        (2, 3): "P4",
        (3, 1): "P3",
        (3, 2): "P4",
        (3, 3): "P4",
    }

    priority = matrix[(impact, urgency)]

    if C3 == "vip" and vip and priority in ("P3", "P4"):
        priority = "P2"

    return priority


ACK_TARGETS = {
    "P1": timedelta(minutes=15),
    "P2": timedelta(hours=1),
    "P3": timedelta(hours=4),
    "P4": timedelta(hours=8),
}

RESOLVE_TARGETS = {
    "P1": timedelta(hours=4),
    "P2": timedelta(hours=8),
    "P3": timedelta(hours=24),
    "P4": timedelta(hours=72),
}


def next_business_start(local: datetime) -> datetime:
    current = local

    while current.weekday() >= 5:
        current = datetime.combine(
            current.date() + timedelta(days=1),
            time(8, 0),
            WARSAW,
        )

    if current.time() < time(8, 0):
        return datetime.combine(current.date(), time(8, 0), WARSAW)

    if current.time() >= time(16, 0):
        current = datetime.combine(
            current.date() + timedelta(days=1),
            time(8, 0),
            WARSAW,
        )

        while current.weekday() >= 5:
            current = datetime.combine(
                current.date() + timedelta(days=1),
                time(8, 0),
                WARSAW,
            )

    return current


def add_business_time(start_utc: datetime, duration: timedelta) -> datetime:
    local = start_utc.astimezone(WARSAW)
    remaining = duration

    while True:
        local = next_business_start(local)

        end_of_day = datetime.combine(
            local.date(),
            time(16, 0),
            WARSAW,
        )

        available = end_of_day - local

        if remaining <= available:
            return (local + remaining).astimezone(timezone.utc)

        remaining -= available

        local = datetime.combine(
            local.date() + timedelta(days=1),
            time(8, 0),
            WARSAW,
        )


def uses_business_clock(priority: str) -> bool:
    if priority == "P1":
        return C1 == "business"
    return True


def due_time(created_at: datetime, priority: str, target: timedelta) -> datetime:
    if uses_business_clock(priority):
        return add_business_time(created_at, target)

    return created_at + target


def is_business_time(value: datetime) -> bool:
    local = value.astimezone(WARSAW)

    return (
        local.weekday() < 5
        and time(8, 0) <= local.time() < time(16, 0)
    )


def create_sla(created: datetime, priority: str) -> dict:
    return {
        "ack_due_at": format_instant(
            due_time(created, priority, ACK_TARGETS[priority])
        ),
        "resolve_due_at": format_instant(
            due_time(created, priority, RESOLVE_TARGETS[priority])
        ),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "svcdesk"}


@app.post("/tickets", status_code=201)
def create_ticket(body: TicketCreate, request: Request):
    try:
        now = now_for_request(request)
    except ValueError:
        return error_response(422, "validation", "invalid X-Test-Clock")

    priority = priority_for(
        body.impact,
        body.urgency,
        body.reporter.vip,
    )

    ticket = {
        "id": str(uuid.uuid4()),
        "title": body.title,
        "description": body.description,
        "reporter": body.reporter.model_dump(),
        "impact": body.impact,
        "urgency": body.urgency,
        "priority": priority,
        "state": "new",
        "created_at": format_instant(now),
        "acknowledged_at": None,
        "resolved_at": None,
        "closed_at": None,
        "related_to": body.related_to,
        "sla": create_sla(now, priority),
    }

    save_ticket(ticket)
    return ticket


@app.get("/tickets")
def list_tickets(
    state: Optional[str] = None,
    priority: Optional[str] = None,
):
    tickets = load_all_tickets()

    if state is not None:
        tickets = [t for t in tickets if t["state"] == state]

    if priority is not None:
        tickets = [t for t in tickets if t["priority"] == priority]

    return tickets


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    ticket = load_ticket(ticket_id)

    if ticket is None:
        return error_response(404, "not_found", "ticket not found")

    return ticket


@app.post("/tickets/{ticket_id}/ack")
def acknowledge(ticket_id: str, request: Request):
    ticket = load_ticket(ticket_id)

    if ticket is None:
        return error_response(404, "not_found", "ticket not found")

    if ticket["state"] != "new":
        return error_response(409, "invalid_transition", "cannot acknowledge ticket")

    try:
        now = now_for_request(request)
    except ValueError:
        return error_response(422, "validation", "invalid X-Test-Clock")

    ticket["state"] = "acknowledged"
    ticket["acknowledged_at"] = format_instant(now)

    save_ticket(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/start")
def start(ticket_id: str, request: Request):
    ticket = load_ticket(ticket_id)

    if ticket is None:
        return error_response(404, "not_found", "ticket not found")

    if ticket["state"] != "acknowledged":
        return error_response(409, "invalid_transition", "cannot start ticket")

    try:
        now_for_request(request)
    except ValueError:
        return error_response(422, "validation", "invalid X-Test-Clock")

    ticket["state"] = "in_progress"

    save_ticket(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/resolve")
def resolve(ticket_id: str, request: Request):
    ticket = load_ticket(ticket_id)

    if ticket is None:
        return error_response(404, "not_found", "ticket not found")

    if ticket["state"] != "in_progress":
        return error_response(409, "invalid_transition", "cannot resolve ticket")

    try:
        now = now_for_request(request)
    except ValueError:
        return error_response(422, "validation", "invalid X-Test-Clock")

    ticket["state"] = "resolved"
    ticket["resolved_at"] = format_instant(now)

    save_ticket(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/close")
def close(ticket_id: str, request: Request):
    ticket = load_ticket(ticket_id)

    if ticket is None:
        return error_response(404, "not_found", "ticket not found")

    if ticket["state"] != "resolved":
        return error_response(409, "invalid_transition", "cannot close ticket")

    try:
        now = now_for_request(request)
    except ValueError:
        return error_response(422, "validation", "invalid X-Test-Clock")

    ticket["state"] = "closed"
    ticket["closed_at"] = format_instant(now)

    save_ticket(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/reopen")
def reopen(ticket_id: str, request: Request):
    ticket = load_ticket(ticket_id)

    if ticket is None:
        return error_response(404, "not_found", "ticket not found")

    try:
        now = now_for_request(request)
    except ValueError:
        return error_response(422, "validation", "invalid X-Test-Clock")

    if ticket["state"] == "closed":
        if C2 == "immutable":
            return error_response(409, "ticket_closed", "closed ticket is immutable")

        reference = parse_instant(ticket["closed_at"])

    elif ticket["state"] == "resolved":
        reference = parse_instant(ticket["resolved_at"])

    else:
        return error_response(409, "invalid_transition", "cannot reopen ticket")

    if now > reference + timedelta(days=7):
        return error_response(
            409,
            "reopen_window_expired",
            "reopen window expired",
        )

    ticket["state"] = "in_progress"
    ticket["resolved_at"] = None
    ticket["closed_at"] = None

    save_ticket(ticket)
    return ticket


@app.get("/tickets/{ticket_id}/sla")
def ticket_sla(ticket_id: str, request: Request):
    ticket = load_ticket(ticket_id)

    if ticket is None:
        return error_response(404, "not_found", "ticket not found")

    try:
        now = now_for_request(request)
    except ValueError:
        return error_response(422, "validation", "invalid X-Test-Clock")

    ack_due = parse_instant(ticket["sla"]["ack_due_at"])
    resolve_due = parse_instant(ticket["sla"]["resolve_due_at"])

    if ticket["acknowledged_at"] is None:
        ack_breached = now > ack_due
    else:
        ack_breached = parse_instant(ticket["acknowledged_at"]) > ack_due

    if ticket["resolved_at"] is None:
        resolve_breached = now > resolve_due
    else:
        resolve_breached = parse_instant(ticket["resolved_at"]) > resolve_due

    paused = (
        ticket["state"] not in ("resolved", "closed")
        and uses_business_clock(ticket["priority"])
        and not is_business_time(now)
    )

    return {
        "priority": ticket["priority"],
        "ack_due_at": ticket["sla"]["ack_due_at"],
        "resolve_due_at": ticket["sla"]["resolve_due_at"],
        "ack_breached": ack_breached,
        "resolve_breached": resolve_breached,
        "paused": paused,
    }