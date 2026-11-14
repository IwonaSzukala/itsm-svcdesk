# ai-generated: 80% - Claude Code wrote these test cases for semgrep/rules.yml; I chose which cases must fire and which must not (CI-SPEC.md P-31)
import json
import sqlite3
import time
from datetime import date, datetime, timezone


def save_ticket(ticket):
    with sqlite3.connect("svcdesk.db") as conn:
        # ruleid: svcdesk-tickets-table-write
        conn.execute("INSERT OR REPLACE INTO tickets(id, payload) VALUES (?, ?)", (ticket["id"], json.dumps(ticket)))


def close_ticket_in_place(ticket_id):
    with sqlite3.connect("svcdesk.db") as conn:
        # ruleid: svcdesk-tickets-table-write
        conn.execute("UPDATE tickets SET payload = json_set(payload, '$.state', 'closed') WHERE id = ?", (ticket_id,))


def purge_ticket(ticket_id):
    with sqlite3.connect("svcdesk.db") as conn:
        # ruleid: svcdesk-tickets-table-write
        conn.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))


def load_ticket(ticket_id):
    with sqlite3.connect("svcdesk.db") as conn:
        # ok: svcdesk-tickets-table-write
        return conn.execute("SELECT payload FROM tickets WHERE id = ?", (ticket_id,)).fetchone()


def init_db():
    with sqlite3.connect("svcdesk.db") as conn:
        # ok: svcdesk-tickets-table-write
        conn.execute("CREATE TABLE IF NOT EXISTS tickets (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")


def write_audit(entry):
    with sqlite3.connect("svcdesk.db") as conn:
        # ok: svcdesk-tickets-table-write
        conn.execute("INSERT INTO audit(entry) VALUES (?)", (entry,))


def now_for_request(request):
    value = request.headers.get("X-Test-Clock")
    if value:
        # ok: svcdesk-wall-clock-read
        return datetime.fromisoformat(value)
    # ruleid: svcdesk-wall-clock-read
    return datetime.now(timezone.utc)


def acknowledge(ticket, request):
    # ruleid: svcdesk-wall-clock-read
    ticket["acknowledged_at"] = datetime.utcnow()
    # ok: svcdesk-wall-clock-read
    ticket["acknowledged_at"] = now_for_request(request)
    return ticket


def report_day():
    # ruleid: svcdesk-wall-clock-read
    return date.today()


def stamp_event():
    # ruleid: svcdesk-wall-clock-read
    return time.time()


def observe(handler):
    # ok: svcdesk-wall-clock-read
    started = time.perf_counter()
    handler()
    # ok: svcdesk-wall-clock-read
    return time.perf_counter() - started
