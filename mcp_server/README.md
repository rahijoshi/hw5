# Campus Customs MCP server

FastMCP server that every agent in this homework calls through for database
access. It talks only to `data/campus_customs_new.db` — the working copy —
never the original `data/campus_customs.db`, so the shop can always be reset
by re-copying the original over the working copy.

Runs on its own virtual environment, `mcp_server/.venv` (Python 3.12,
`mcp<2` only — see `requirements.txt`), separate from the backend's own
`.venv`. The two pieces only ever talk to each other over the MCP protocol
as client and subprocess, so they don't need matching dependencies, and
`pydantic-ai-slim[mcp]`'s own newer `mcp` dependency in the backend never
collides with this server's older, `FastMCP`-API one.

## Tools

Read-only:

- **`check_stock(sku, size)`** — reads `inventory`. On-shelf quantity and
  location for one sku/size, or `found: false` if it doesn't exist.
- **`get_invoice_status(invoice_id)`** — reads `invoices` (joined to
  `vendors` for the name). Amount, due date, status, and whether that
  status currently blocks the vendor from shipping new stock.
- **`get_lease_status(lease_id)`** — reads `leases` and `desk.date_today`.
  Lease terms plus days until `next_due`, and whether it's already overdue.
- **`get_ticket(ticket_id)`** — reads `tickets`. The authoritative current
  row for one ticket.
- **`list_vendors()`** — reads `vendors`. Every vendor's specialty and
  lead_days.
- **`list_open_invoices_for_vendor(vendor_id)`** — reads `invoices`. A
  vendor's open, unpaid invoices — which block them from shipping at all.
- **`list_leases()`** — reads `leases`. Every lease's terms.
- **`get_pricing(sku)`** — reads `pricing`. Unit cost, list price, and the
  computed margin per unit.
- **`get_cash_balance(account)`** — reads `cash_accounts`. One account's
  current balance.

Write (one tool, gated):

- **`update_ticket_status(ticket_id, status, note, updated_by)`** — writes
  `tickets`. Sets status (`open` / `pending_approval` / `blocked` /
  `resolved`) and appends a dated note.
- **`make_payment(kind, ref_id, amount, account, approved_by)`** — writes
  `payments` and `cash_accounts`, and (for an invoice) flips
  `invoices.status` to paid. Refuses outright, with no write at all, if
  `approved_by` is blank, the account can't cover the amount (no negative
  balances), or the referenced invoice/lease doesn't exist or is already
  settled. The only tool here that moves money — in the agent team
  (`backend/agent_team.py`), it's additionally wrapped in PydanticAI's
  `approval_required()` so a model can't even execute it without a human
  approving the call first, and only Accounting's agent can see it at all.

Every tool returns the row's actual fields, never invented ones; a lookup
that finds nothing comes back as `found: false` instead of a guess.

Not every agent sees every tool — see `AGENT_TOOLS` in
`backend/agent_team.py` and `output/harness.md`'s safety section for the
least-privilege scoping and why.
