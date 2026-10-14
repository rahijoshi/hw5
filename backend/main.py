"""FastAPI backend for the Campus Customs ops board.

The second of the three pieces (MCP server, this backend, the React
dashboard). Every route goes through mcp_server/server.py — the same MCP
server the agent team itself calls through (see mcp_client.py) — never a
second, bypass data layer. See output/harness.md for the one-line route
list.

Run from the backend folder:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

from agent_team import run_ticket  # noqa: E402  (needs the path insert above)
from mcp_client import call_list_tool, call_tool  # noqa: E402

ROOT = Path(__file__).parent
DATA_DIR = ROOT.parent / "data"
ORIGINAL_DB = DATA_DIR / "campus_customs.db"
WORKING_DB = DATA_DIR / "campus_customs_new.db"
AUDIT_PATH = ROOT.parent / "output" / "audit_trail.json"

app = FastAPI(title="Campus Customs ops backend")

# The Vite dashboard's dev server origin — the only browser origin that
# needs to call these routes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ticket ids with a run already in flight — guards against the dashboard
# double-triggering the same ticket before the first run finishes.
_running_tickets: set[int] = set()


class ApproveRequest(BaseModel):
    ticket_id: int
    approved_by: str


def _load_audit_entries() -> list[dict]:
    if not AUDIT_PATH.is_file():
        return []
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else [data]


def _append_audit_entry(entry: dict) -> None:
    """Same append-don't-wipe convention as agent_team.append_audit_entries
    — a human's approval is itself one more auditable step."""
    entries = _load_audit_entries()
    entries.append(entry)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


async def _latest_pending_payments() -> list[dict]:
    """The most recent make_payment-related entry per ticket, kept only if
    it's still awaiting approval.

    Scanning for *any* awaiting_human_approval entry isn't enough — once a
    ticket's payment is actually approved, a later 'completed' entry (from
    approve_payment below) must supersede the earlier pending one, or an
    already-paid ticket would show as pending forever. Entries are
    chronological, so the last one seen per ticket wins.
    """
    latest_by_ticket: dict[int, dict] = {}
    for entry in _load_audit_entries():
        if not (entry.get("tool_name") or "").endswith("make_payment"):
            continue
        latest_by_ticket[entry["ticket_id"]] = entry
    return [e for e in latest_by_ticket.values() if e.get("stop_reason") == "awaiting_human_approval"]


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


@app.get("/api/tickets")
async def list_tickets() -> list[dict]:
    """The 3 tickets and whether each is open or resolved."""
    tickets = await call_list_tool("list_tickets")
    for ticket in tickets:
        ticket["is_resolved"] = ticket["status"] == "resolved"
    return tickets


@app.post("/api/tickets/{ticket_id}/run")
async def run_ticket_route(ticket_id: int, background_tasks: BackgroundTasks) -> dict:
    """Run the agent team on one ticket. Starts in the background and
    returns immediately — poll GET /api/events and GET /api/tickets to
    watch it work and see the ticket's status change.
    """
    if ticket_id in _running_tickets:
        raise HTTPException(status_code=409, detail=f"ticket {ticket_id} is already running")

    async def _run() -> None:
        _running_tickets.add(ticket_id)
        try:
            await run_ticket(ticket_id)
        finally:
            _running_tickets.discard(ticket_id)

    background_tasks.add_task(_run)
    return {"status": "started", "ticket_id": ticket_id}


@app.get("/api/events")
async def get_events(ticket_id: int | None = None, limit: int = 200) -> list[dict]:
    """Recent agent-loop steps — what each agent said and which tools it
    used — so the dashboard can refresh and show new activity.
    """
    entries = _load_audit_entries()
    if ticket_id is not None:
        entries = [e for e in entries if e.get("ticket_id") == ticket_id]
    return entries[-limit:]


@app.get("/api/payments/pending")
async def list_pending_payments() -> list[dict]:
    """Payments an agent drafted but could not execute without a human —
    each one is a real approval_required() tool call that's still paused,
    not just a note in some text.
    """
    return await _latest_pending_payments()


@app.post("/api/payments/approve")
async def approve_payment(body: ApproveRequest) -> dict:
    """What actually changes cash. Agents only ever draft a payment (see
    GET /api/payments/pending) — this route, triggered by a human clicking
    approve, is the only path in this whole system that executes one.
    """
    if not body.approved_by.strip():
        raise HTTPException(status_code=400, detail="approved_by is required")

    pending = await _latest_pending_payments()
    match = next((p for p in pending if p["ticket_id"] == body.ticket_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"no pending payment for ticket {body.ticket_id}")

    proposed_args = match["tool_args"]
    result = await call_tool(
        "make_payment",
        kind=proposed_args["kind"],
        ref_id=proposed_args["ref_id"],
        amount=proposed_args["amount"],
        account=proposed_args["account"],
        # The human's name from this request — never whatever string the
        # agent proposed, even if it happened to be non-blank.
        approved_by=body.approved_by,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("reason", "payment refused"))

    _append_audit_entry(
        {
            "run_id": f"ticket-{body.ticket_id}-approval",
            "ticket_id": body.ticket_id,
            "agent": "human-approval",
            "timestamp": result["payment"]["paid_at"],
            "iteration": 0,
            "thoughts": "",
            "tool_name": "make_payment",
            "tool_args": {**proposed_args, "approved_by": body.approved_by},
            "tool_result_summary": json.dumps(result)[:300],
            "stop_reason": "completed",
        }
    )
    await call_tool(
        "update_ticket_status",
        ticket_id=body.ticket_id,
        status="resolved",
        note=f"Payment approved and made by {body.approved_by}.",
        updated_by="backend",
    )
    return result


@app.get("/api/cash")
async def get_cash(account: str = "checking") -> dict:
    """The current balance from cash_accounts."""
    return await call_tool("get_cash_balance", account=account)


@app.post("/api/reset")
async def reset_database() -> dict:
    """Reset data/campus_customs_new.db back to the untouched original —
    the shop's own rule, for whenever you want a fresh run at the tickets.
    """
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    return {"ok": True}
