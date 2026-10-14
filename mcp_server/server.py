"""MCP server for Campus Customs ops. Every agent's tools live here.

Reads/writes data/campus_customs_new.db only — never campus_customs.db (the
untouched original, used only to reset). Tools report exactly what the
database holds; a row that isn't found comes back with found=False rather
than a guessed value.
"""

import sqlite3
from datetime import date
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"

mcp = FastMCP("campus-customs-ops")

OPEN_TICKET_STATUSES = {"open", "pending_approval", "blocked", "resolved"}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _today(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    return row["date_today"] if row else None


@mcp.tool()
def check_stock(sku: str, size: str) -> dict:
    """Look up on-shelf quantity and location for one sku/size from `inventory`.

    Ticket #101 needs this to confirm CC-TEE-WHITE/S is actually out of
    stock before anyone looks for a restock. Ticket #103 needs it to see
    exactly how short the shop is on CC-HOOD-NAVY/M against the 20 requested.
    """
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return {"found": False, "sku": sku, "size": size}
    return {"found": True, **dict(row)}


@mcp.tool()
def get_invoice_status(invoice_id: int) -> dict:
    """Look up one invoice from `invoices` (joined to `vendors` for the name).

    Ticket #101 carries invoice_id=501 directly — this is how an agent
    discovers that invoice is still open and unpaid, which under the shop's
    rules means Bulldog Print Co will not ship the restocked tee until
    Accounting pays it.
    """
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT i.id, i.vendor_id, v.name AS vendor_name, i.amount,
                   i.due_date, i.status, i.description
            FROM invoices i
            JOIN vendors v ON v.id = i.vendor_id
            WHERE i.id = ?
            """,
            (invoice_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return {"found": False, "invoice_id": invoice_id}
    data = dict(row)
    data["found"] = True
    data["blocks_shipping"] = data["status"] == "open"
    return data


@mcp.tool()
def get_lease_status(lease_id: int) -> dict:
    """Look up one lease from `leases` and how it sits against `desk.date_today`.

    Ticket #102 carries lease_id=1 directly — this is how Facilities and
    Accounting get the rent amount and due date, and whether it's already
    overdue against the shop's own "today".
    """
    conn = _connect()
    try:
        lease_row = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes "
            "FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        today = _today(conn)
    finally:
        conn.close()
    if lease_row is None:
        return {"found": False, "lease_id": lease_id}
    data = dict(lease_row)
    data["found"] = True
    data["date_today"] = today
    if today:
        days_until_due = (date.fromisoformat(data["next_due"]) - date.fromisoformat(today)).days
        data["days_until_due"] = days_until_due
        data["overdue"] = days_until_due < 0
    return data


@mcp.tool()
def get_ticket(ticket_id: int) -> dict:
    """Look up one ticket from `tickets` — the authoritative current row,
    not whatever paraphrase of it an agent was handed in conversation.
    """
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return {"found": False, "ticket_id": ticket_id}
    return {"found": True, **dict(row)}


@mcp.tool()
def list_tickets() -> list[dict]:
    """List every ticket from `tickets` — id, type, status, and the rest.

    The backend's dashboard route (GET /api/tickets) uses this to show all
    three tickets and whether each is open or resolved at a glance,
    instead of looking each one up by id.
    """
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


@mcp.tool()
def update_ticket_status(ticket_id: int, status: str, note: str, updated_by: str = "") -> dict:
    """Set a ticket's status in `tickets` and append a dated note explaining why.

    `status` must be one of open, pending_approval, blocked, resolved.
    This is how Boss (or any agent making a final call) closes the loop on
    a ticket instead of just talking about it.
    """
    if status not in OPEN_TICKET_STATUSES:
        return {"found": False, "error": f"status must be one of {sorted(OPEN_TICKET_STATUSES)}"}
    conn = _connect()
    try:
        existing = conn.execute("SELECT notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if existing is None:
            return {"found": False, "ticket_id": ticket_id}
        who = f"[{updated_by}] " if updated_by else ""
        prior = existing["notes"] or ""
        new_notes = f"{prior}\n{who}{note}".strip() if prior else f"{who}{note}".strip()
        conn.execute(
            "UPDATE tickets SET status = ?, notes = ? WHERE id = ?",
            (status, new_notes, ticket_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    finally:
        conn.close()
    return {"found": True, **dict(row)}


@mcp.tool()
def list_vendors() -> list[dict]:
    """List every vendor from `vendors` — name, specialty, and lead_days.

    Inventory reads this to decide which vendor can restock a shortfall
    (e.g. "apparel reprint" for tees/hoodies) and how long it will take.
    """
    conn = _connect()
    try:
        rows = conn.execute("SELECT id, name, specialty, lead_days FROM vendors").fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


@mcp.tool()
def list_open_invoices_for_vendor(vendor_id: int) -> list[dict]:
    """List a vendor's open, unpaid invoices from `invoices`.

    Covers the general case ticket #103 needs: before recommending a vendor
    for a restock, check whether they already have an open invoice — the
    shop rule is that an open invoice blocks a vendor from shipping at all.
    """
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, vendor_id, amount, due_date, status, description "
            "FROM invoices WHERE vendor_id = ? AND status = 'open'",
            (vendor_id,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


@mcp.tool()
def list_leases() -> list[dict]:
    """List every lease from `leases` — space, landlord, rent, and next_due.

    Gives Facilities full visibility into shop space obligations, not just
    whatever lease_id a single ticket happens to carry.
    """
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases"
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


@mcp.tool()
def get_pricing(sku: str) -> dict:
    """Look up unit cost and list price for one sku from `pricing`.

    Accounting needs this to check margin before approving a bulk-discount
    ask like ticket #103's; Inventory needs it to weigh restock economics.
    """
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return {"found": False, "sku": sku}
    data = dict(row)
    data["found"] = True
    data["margin_per_unit"] = round(data["list_price"] - data["unit_cost"], 2)
    return data


@mcp.tool()
def get_cash_balance(account: str = "checking") -> dict:
    """Look up one cash account's balance from `cash_accounts`.

    Accounting checks this before proposing or making any payment — cash
    only goes out in this homework, so there is no way to replenish it.
    """
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return {"found": False, "account": account}
    return {"found": True, **dict(row)}


@mcp.tool()
def make_payment(
    kind: Literal["invoice", "rent"], ref_id: int, amount: float, account: str, approved_by: str
) -> dict:
    """Pay an open invoice or a lease's rent out of a cash account — writes
    `payments`, decrements `cash_accounts`, and (for an invoice) flips
    `invoices.status` to paid.

    Refuses outright, with no write at all, if: `approved_by` is blank (a
    human must approve every payment in this shop), the account doesn't
    have enough cash to cover it (balances must never go negative — there
    is no revenue modeled in this homework to refill them), or the
    referenced invoice/lease doesn't exist or (for an invoice) is already
    settled. This is the only tool in this server that moves money or
    writes to `payments`.
    """
    if not approved_by.strip():
        return {"ok": False, "reason": "human approval required — approved_by is blank"}
    conn = _connect()
    try:
        account_row = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()
        if account_row is None:
            return {"ok": False, "reason": f"no such cash account: {account}"}
        if account_row["balance"] < amount:
            return {
                "ok": False,
                "reason": "insufficient funds — refusing to let the balance go negative",
                "balance": account_row["balance"],
                "amount": amount,
            }

        if kind == "invoice":
            invoice_row = conn.execute(
                "SELECT status FROM invoices WHERE id = ?", (ref_id,)
            ).fetchone()
            if invoice_row is None:
                return {"ok": False, "reason": f"no such invoice: {ref_id}"}
            if invoice_row["status"] != "open":
                return {"ok": False, "reason": f"invoice {ref_id} is already '{invoice_row['status']}'"}
        else:
            lease_row = conn.execute("SELECT id FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if lease_row is None:
                return {"ok": False, "reason": f"no such lease: {ref_id}"}

        paid_at = _today(conn) or ""
        cursor = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (kind, ref_id, amount, account, paid_at, approved_by),
        )
        conn.execute(
            "UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ?",
            (amount, paid_at, account),
        )
        if kind == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
        conn.commit()

        new_balance = conn.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (account,)
        ).fetchone()["balance"]
        payment_row = conn.execute(
            "SELECT * FROM payments WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    finally:
        conn.close()
    return {"ok": True, "payment": dict(payment_row), "new_balance": new_balance}


if __name__ == "__main__":
    mcp.run()
