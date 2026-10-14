# Harness — HW 5: Campus Customs Multi-Agent Ops Board

System writeup, grown problem by problem. By Problem 9 this covers: the database tables, all 12
MCP tools, the five agents and how they connect, the backend's API routes, the React dashboard,
the safety/guardrail rules, and the real end-to-end run that resolved all three tickets.

**Contents:** [Database](#database) &middot; [Tables](#tables) &middot;
[MCP server tools](#mcp-server-tools-problem-3) &middot; [The agent team](#the-agent-team-problem-5)
&middot; [Growing the MCP server](#growing-the-mcp-server-problem-5--8-new-tools-11-total) &middot;
[Safety](#safety) &middot; [The backend API](#the-backend-api-problem-7) &middot;
[The dashboard](#the-dashboard-problem-8) &middot;
[Resolving all three tickets](#resolving-all-three-tickets-problem-9)

## Database

Two files in `data/` (gitignored): `campus_customs.db` is the original, left untouched; `campus_customs_new.db` is the working copy every tool/MCP server/backend reads and writes. To restart a full run, re-copy the original over the working copy.

## Tables

### `desk`
Fields: `date_today`, `notes`.
Why it matters: this is the shop's single source of truth for "today" — every overdue check (rent, invoices) compares against `desk.date_today`, not the real wall-clock date. Currently `2026-08-31`.

### `tickets`
Fields: `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`.
Why it matters: this is the board itself — every agent's job starts from a row here. `type` routes it toward an agent (customer_order → Inventory/Customer Service, rent_notice → Facilities, price_override → Inventory/Accounting), and the optional `sku`/`lease_id`/`invoice_id` foreign keys are how a ticket pulls in the rest of the schema.

### `inventory`
Fields: `sku`, `name`, `size`, `qty`, `location`. Primary key is `(sku, size)`.
Why it matters: the Inventory agent's stock check — whether a ticket's requested `sku`+`size`+`qty` can be filled from what's on the shelf, or needs a restock.

### `pricing`
Fields: `sku`, `unit_cost`, `list_price`.
Why it matters: lets Inventory/Accounting compute margin per unit (`list_price - unit_cost`), which is what a price-override or bulk-discount ticket (like #103) has to be checked against before Accounting can approve one.

### `vendors`
Fields: `id`, `name`, `specialty`, `lead_days`.
Why it matters: when Inventory finds a shortfall, this is how it picks who can restock and how long that takes — and it's the table Accounting's invoices point back to, which is where the "won't ship with an unpaid invoice" rule gets enforced.

### `leases`
Fields: `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`.
Why it matters: Facilities' territory — rent tickets (like #102) link here via `tickets.lease_id` to get the amount and due date Accounting needs before it can prepare a payment.

### `cash_accounts`
Fields: `name` (primary key), `balance`, `date`.
Why it matters: the hard constraint on every payment the Accounting agent proposes — cash only goes out in this assignment, so the pay tool must refuse anything that would take a balance negative.

### `payments`
Fields: `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`.
Why it matters: the audit trail of money actually spent, and the only place a human approval (`approved_by`) is recorded — every payment tool call should end with a row here, never a bypass.

### `invoices`
Fields: `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`.
Why it matters: tracks what the shop owes each vendor; an `open` invoice on a vendor blocks that vendor from shipping new stock, so Inventory and Accounting both have to check this table before Inventory can promise a restock.

## How the three starting tickets link across tables

- **#101** (`customer_order`, Tauhid Zaman, "Bulldog tee") — `sku=CC-TEE-WHITE`, `size=S`, `qty=1`. `inventory` shows **0** units of that sku/size in stock. It also carries `invoice_id=501`, which is `invoices` row 501: an **open**, $840 invoice to vendor 1 (Bulldog Print Co) for "Rush reprint CC-TEE-WHITE S" — i.e. this exact shortage was already being restocked, but the restock is blocked because that invoice is unpaid. This ticket is the clearest end-to-end case: Inventory sees the stockout, Accounting has to clear invoice 501 (with human approval) before Bulldog Print Co will ship, and only then can the order be fulfilled.
- **#102** (`rent_notice`, Elm City Properties, "Rent due") — `lease_id=1`, which is the Chapel Street shop lease: $2,400/month, `next_due = 2026-09-02`. Against `desk.date_today = 2026-08-31`, that's 2 days out, matching the ticket's own note. Facilities reads the lease terms; Accounting prepares the rent payment for human approval.
- **#103** (`price_override`, Yale AI Club, "Bulk hoodie discount") — `sku=CC-HOOD-NAVY`, `size=M`, `qty=20`. `inventory` only has **8** units of that sku/size (a shortfall of 12), and `pricing` gives unit_cost $22 / list_price $58. Inventory flags the shortfall and vendor options; Accounting checks margin on the requested discount before any override can be approved; Customer Service eventually drafts the reply to Yale AI Club.

## MCP server tools (Problem 3)

Three tools in `mcp_server/server.py`, built with FastMCP. Not connected to anything yet — that's a later problem.

| Tool | Table it reads | Ticket it unlocks | Why |
| --- | --- | --- | --- |
| `check_stock(sku, size)` | `inventory` | **#101** and **#103** | For #101, confirms `CC-TEE-WHITE`/S is really at **0** before anyone looks for a restock. For #103, shows `CC-HOOD-NAVY`/M has only **8** on the shelf against the 20 the Yale AI Club wants — the exact shortfall Inventory has to flag before a bulk discount can even be discussed. |
| `get_invoice_status(invoice_id)` | `invoices` (joined to `vendors` for the name) | **#101** | Ticket 101's own `invoice_id` is **501** — this tool is how an agent learns that invoice is still **open** and unpaid, which under the shop's rules means Bulldog Print Co won't ship the restocked tee until Accounting pays it. |
| `get_lease_status(lease_id)` | `leases` (plus `desk.date_today` for the overdue check) | **#102** | Ticket 102's own `lease_id` is **1** — this tool returns the Chapel Street lease's $2,400 rent and `2026-09-02` due date, and computes that it's 2 days out from `desk.date_today`, matching the ticket's own note and giving Facilities/Accounting the numbers to act on. |

Every tool returns `found: false` on a missing row instead of guessing — no tool invents data not already in `campus_customs_new.db`.

## Running the MCP server (Problem 4)

This machine only shipped with system Python 3.9.6 (the `mcp` package needs ≥3.10, no Homebrew/pyenv/uv present). Installed `uv` (astral.sh's official installer, user-level, no sudo), used it to fetch an isolated Python 3.12, and rebuilt `.venv` on that interpreter per the course's `AGENTS.md` convention. The `mcp` package has since moved to a 2.x line that renamed `FastMCP` to `MCPServer`; pinned `mcp_server/requirements.txt` to `mcp<2` so the server keeps using `mcp.server.fastmcp.FastMCP` as the assignment specifies.

The server is registered as a project MCP server in `.mcp.json` at the repo root, pointing at `.venv/bin/python mcp_server/server.py`. Connected to it exactly as an MCP client would (stdio handshake, `list_tools`, `call_tool`) and confirmed all three tools come back online: `check_stock`, `get_invoice_status`, `get_lease_status`. Full prompt/tool/output evidence, cross-checked line-by-line against `data/campus_customs_new.db`, is in `output/mcp_smoke.json`.

## The agent team (Problem 5)

Five PydanticAI agents, every one on `gpt-6-luna` through Portkey (`backend/agent_team.py`'s `load_model()` refuses to build any agent if `MODEL_NAME` is set to anything else). Each agent's full system prompt lives in its own file under `backend/prompts/` — written out in detail on purpose, since a short generic prompt can't carry the shop-specific rules each role actually needs:

| Agent | Role | Prompt |
| --- | --- | --- |
| **Boss** | Reads each ticket, decides who should work it, makes the final call, closes the ticket out | [`backend/prompts/boss.md`](../backend/prompts/boss.md) |
| **Inventory** | Checks stock by sku/size, sizes up shortfalls, picks a vendor who can restock and isn't blocked by an unpaid invoice | [`backend/prompts/inventory.md`](../backend/prompts/inventory.md) |
| **Accounting** | Watches cash and invoices, checks margins, drafts payments — never executes one without a human's sign-off | [`backend/prompts/accounting.md`](../backend/prompts/accounting.md) |
| **Facilities** | Reads lease terms and rent due dates | [`backend/prompts/facilities.md`](../backend/prompts/facilities.md) |
| **Customer Service** | Drafts messages back to whoever filed the ticket — never sends anything for real | [`backend/prompts/customer_service.md`](../backend/prompts/customer_service.md) |

**Full connectivity.** `backend/agent_team.py`'s `build_agent_team()` builds all five, then gives each one a `delegate_to_<other>` tool for every other agent (20 tools total, generated by one small loop instead of hand-written) — so any agent can hand work to any other, in any order, for as long as the shared request budget allows. A delegated call shares the parent's `RunContext.usage` **and** `RunContext.usage_limits`, so the whole tree — Boss delegating to Inventory delegating to Accounting delegating back to Boss, however deep — is one shared budget, not five separate ones. This was a real bug I caught while testing, not just a design intention: forwarding only `usage=` and not `usage_limits=` let every nested call silently fall back to the framework's own default limit (50 requests) instead of inheriting the parent's, so a capped top-level run was effectively uncapped underneath. Fixed by forwarding both.

**Least-privilege tool access.** Every agent only sees the MCP tools its own role actually needs (`AGENT_TOOLS` in `agent_team.py`, enforced with the toolset's own `.filtered()`) — e.g. Customer Service sees only `get_ticket`; nobody but Accounting can even see `make_payment`. See the full table below.

## Growing the MCP server (Problem 5) — 8 new tools, 11 total

| Tool | Table(s) it uses | Added in | Who can call it |
| --- | --- | --- | --- |
| `check_stock(sku, size)` | `inventory` | Problem 3 | Boss, Inventory |
| `get_invoice_status(invoice_id)` | `invoices`, `vendors` | Problem 3 | Boss, Accounting |
| `get_lease_status(lease_id)` | `leases`, `desk` | Problem 3 | Boss, Facilities, Accounting |
| `get_ticket(ticket_id)` | `tickets` | Problem 5 | all five agents |
| `update_ticket_status(ticket_id, status, note, updated_by)` | `tickets` | Problem 5 | Boss |
| `list_vendors()` | `vendors` | Problem 5 | Boss, Inventory |
| `list_open_invoices_for_vendor(vendor_id)` | `invoices` | Problem 5 | Boss, Inventory, Accounting |
| `list_leases()` | `leases` | Problem 5 | Boss, Facilities, Accounting |
| `get_pricing(sku)` | `pricing` | Problem 5 | Boss, Inventory, Accounting |
| `get_cash_balance(account)` | `cash_accounts` | Problem 5 | Boss, Accounting |
| `make_payment(kind, ref_id, amount, account, approved_by)` | `payments`, `cash_accounts`, `invoices` | Problem 5 | **Accounting only**, and only after human approval (see Safety below) |

`get_ticket` and `update_ticket_status` close the loop the Problem 3 tools opened: every agent can now pull the authoritative current ticket row instead of trusting a paraphrase, and Boss can write a final `resolved` / `pending_approval` / `blocked` status plus a dated note back to `tickets` instead of just talking about a decision. `list_open_invoices_for_vendor` generalizes Problem 3's ticket-101-specific `get_invoice_status(501)` lookup to any vendor Inventory is considering for a restock (needed for ticket #103, which has no `invoice_id` of its own to check). `make_payment` is the only tool in the whole server that writes to `payments` or moves cash — every other new tool is read-only.

## Safety

**Guardrails a real business would want, here and now:**

- **Human approval on every payment is enforced by the framework, not just requested in a prompt.** `make_payment` is wrapped in PydanticAI's `approval_required()` on Accounting's toolset — a model-initiated call to it comes back as a `DeferredToolRequests` object instead of executing, full stop. Verified live (with `TestModel`, no real model needed to prove the mechanism): a simulated attempt to pay invoice 501 produced a pending approval and left `cash_accounts.balance` and `payments` completely untouched. Accounting's own prompt reinforces this in writing — never fabricate a human's name, never say a payment "was made" unless the tool actually returned `ok: true`.
- **No negative balances, no silent partial payments.** `make_payment` refuses outright (no DB write at all) if the account's balance is less than the amount — checked in the tool itself, not left to the model's arithmetic.
- **Least-privilege tool access per agent**, not one shared toolbox. Only Accounting can even see `make_payment`; Customer Service sees only `get_ticket`. A prompt-injection attempt or a model mistake in Customer Service literally cannot call a payment tool that was never in its tool list to begin with.
- **Nothing ever contacts a real customer or vendor.** No agent has an email/send/call tool of any kind — Customer Service's whole job is producing a draft string that a human would have to copy and send themselves. This is enforced by omission (the tool doesn't exist), not just by prompt instruction.
- **Every step is audited.** Every agent-loop iteration — every tool call, every delegation, every plain response — across the whole delegation tree for a ticket is appended to `output/audit_trail.json`, tagged with `run_id` (one per ticket), `agent` (whose step it was), and a timestamp. A failed run still leaves a trace (`append_audit_failure`) instead of vanishing.
- **Resettable by design.** The agents only ever touch `data/campus_customs_new.db`; `campus_customs.db` stays untouched so a bad run can be undone by re-copying the original over the working copy, per the shop's own rule.

**Limits that keep token use in check:**

- One shared `UsageLimits(request_limit=40, total_tokens_limit=80_000)` covers Boss's entire run for one ticket, including every nested delegated call, however deep — not a separate budget per agent. Confirmed this is a real ceiling, not just a documented intention: a deliberately pathological test (a stub model calling every tool it could see, including every delegate tool, at every level) hit the shared limit and raised `UsageLimitExceeded` rather than spiraling indefinitely.
- Each agent's prompt explicitly asks for a focused, specific delegation request rather than an open-ended "handle this," so a realistic model keeps each teammate's own run short — the hard `UsageLimits` ceiling is the backstop for when a model doesn't cooperate, not the only defense.
- Tool result summaries in the audit trail are truncated (`_summarize`, 300 chars) — keeps the audit file itself cheap to store and read, though it isn't itself a token-cost control on the model.

## Running the agent team

Once a key is available: `cp backend/.env.example backend/.env`, fill in `PORTKEY_API_KEY`, then `.venv/bin/python backend/run_tickets.py` (the project-root `.venv`, which has `pydantic-ai-slim[openai,mcp]` installed — see `backend/requirements.txt`) to run the whole team against every open ticket and grow `output/audit_trail.json` with real model runs.

## The backend API (Problem 7)

`backend/main.py` — FastAPI, started from the `backend/` folder with `uvicorn main:app --reload --port 8000`. Every route goes through `mcp_server/server.py`, either via the agent team (`agent_team.run_ticket`) or via a thin direct MCP client (`backend/mcp_client.py`) — no second, bypass data layer, same rule as the agents themselves.

| Route | What it does |
| --- | --- |
| `GET /api/health` | Confirms the backend is up |
| `GET /api/tickets` | The 3 tickets, each with its real `status` plus a derived `is_resolved` boolean |
| `POST /api/tickets/{ticket_id}/run` | Starts the agent team on one ticket in the background (409 if that ticket is already running); poll the routes below to watch it work |
| `GET /api/events` | Recent agent-loop steps from `output/audit_trail.json` — which agent, which tool, what it said — optionally filtered by `?ticket_id=` |
| `GET /api/payments/pending` | Payments an agent drafted but couldn't execute — each one a real `approval_required()` call still waiting, derived from the audit trail |
| `POST /api/payments/approve` | What actually changes cash — takes `{ticket_id, approved_by}`, calls `make_payment` with the human's real name (never whatever the agent proposed), and only then marks the ticket resolved |
| `GET /api/cash` | The current balance from `cash_accounts` (`?account=` to pick one other than `checking`) |
| `POST /api/reset` | Copies `campus_customs.db` back over `campus_customs_new.db` — the shop's own "reset before a fresh run" rule |

Grew the MCP server to 12 tools: added `list_tickets()` (reads `tickets`) so the dashboard can list all three at once instead of looking each up by id.

**Verified every route against the real system, not just read the code:** started the real server, ran real tickets through `POST /tickets/{id}/run`, watched them move `open → pending_approval` by polling `GET /api/tickets`, confirmed `GET /api/events` picks up the real agent steps (200 entries across all three tickets in one concurrent pass). Caught and fixed one real bug in `mcp_client.py`: a `list[dict]`-returning MCP tool comes back as one content block *per row* under this server's `FastMCP` (v1) API, not one block holding a JSON array — my first version only read block 0, so `GET /api/tickets` 500'd. Fixed with a separate `call_list_tool` helper that reads every block (pydantic-ai's own MCP toolset already handled this correctly, which is why the agents themselves never hit it).

Because the real model consistently chose, across several genuine runs, to report a recommended payment without ever actually attempting `make_payment` (exactly what `accounting.md` asks for — a correctly conservative model, not a bug), there was no organic pending approval left to test `POST /api/payments/approve`'s success path against. Staged one realistic pending-approval audit entry to exercise that path specifically, confirmed end to end against the real database: cash dropped from `$3,400` to `$2,560`, invoice #501 flipped to `paid` with `approved_by: "Rahi Joshi"` (the name from the request, not the blank placeholder in the staged entry), the ticket moved to `resolved`, a second approve attempt correctly refused (`409`, "invoice 501 is already 'paid'"), and a stale pending entry correctly stopped showing as pending once approved (a second real bug, fixed in `_latest_pending_payments`: it only looked for `awaiting_human_approval` entries, so an already-approved ticket would show as pending forever — fixed to take the *latest* payment-related entry per ticket and only count it if that latest one is still awaiting approval). Reset the database afterward and removed the two staged entries from `output/audit_trail.json`, then ran a final genuine pass over all three tickets to leave real evidence in place.

Everything below was first verified structurally with PydanticAI's `TestModel` (no network/key needed) — the full-connectivity build, the least-privilege scoping, the shared-budget bug-and-fix, the approval gate — then **confirmed for real** once a key was in hand, against the actual `gpt-6-luna` model, on all three open tickets:

- **One real surprise**: `gpt-6-luna` is served as a reasoning model on Azure OpenAI through Portkey, which rejects function tools over `/v1/chat/completions` unless `reasoning_effort` is explicitly turned off (`BadRequestError: Function tools with reasoning_effort are not supported for gpt-6-luna-global`). Every agent here depends on tool calls, so every agent is built with `model_settings={"openai_reasoning_effort": "none"}` — without it, no agent could call a single tool.
- **All three tickets resolved correctly end to end** (`.venv/bin/python backend/run_tickets.py`), with real delegation across the team: Boss → Inventory + Accounting + Customer Service on #101 and #103, Boss → Facilities + Accounting on #102. Each landed on `pending_approval` with an accurate, specific note written via `update_ticket_status` — e.g. ticket #101's note correctly states the tee is short by 1, names invoice #501 as the blocker, confirms $3,400 covers the $840 invoice, and says payment "has not been made and requires human approval."
- **The approval gate held in the real run, not just the stress test**: after all three tickets, `cash_accounts.balance` is still exactly `3400.0`, `payments` still has 0 rows, and invoice #501 is still `open` — Accounting correctly concluded a payment was affordable and recommended, and correctly never called `make_payment` to execute it.
- **88 real audit trail entries** across all five agents (`accounting: 37, inventory: 25, boss: 17, customer_service: 6, facilities: 3`), grouped into three `run_id`s (`ticket-101`, `ticket-102`, `ticket-103`) in `output/audit_trail.json`. A sample from ticket #101: Boss delegates to Inventory with a specific, bounded ask ("check on-shelf stock... if short, identify a suitable restock vendor... don't place an order"), gets back the exact shortfall (0 on shelf, short by 1) and Bulldog Print Co's 5-day lead time; delegates to Accounting, which checks `get_cash_balance` and `get_invoice_status(501)` before reporting the payment is affordable but unmade; delegates to Customer Service, which drafts a board-only reply and says so explicitly; Boss then calls `update_ticket_status` with a note synthesizing all three reports.

## The dashboard (Problem 8)

`frontend/` — React + Vite + TypeScript, started with `npm run dev` (talks to the backend at a
hardcoded `http://localhost:8000`; the backend's CORS allows exactly `http://localhost:5173` /
`127.0.0.1:5173` back). Built around a "real desk" metaphor — a board of ticket cards on the left,
the selected ticket's full desk (facts, start/re-run button, live agent feed, per-agent summary) on
the right. Full design rationale — the lavender/yellow palette, why yellow means "needs a human"
and nothing else, the per-agent color system, the "signature slip" approval interaction, why
resolved tickets and cash changes are deliberately quiet rather than celebratory — is in
[`output/design.md`](design.md).

All data comes from the Problem 7 routes, polled every 2 seconds (`src/api.ts`, `src/App.tsx`):
tickets, cash, and pending payments always; the selected ticket's events additionally. A ticket is
tracked as "running" client-side from a successful `POST /run` until its status leaves `open` on a
later poll, since the backend has no separate in-progress status field. Verified live in a real
browser, not just by reading the component code: triggered a real run, watched the feed fill in
over an actual `gpt-6-luna` call, watched a ticket flip to resolved and the per-agent summary cards
render, and clicked an approval through end to end (signed a name, watched the cash widget flash
and the balance actually drop). Caught and fixed one real responsive bug (header overlap at mobile
widths) by testing at a 375px viewport rather than assuming the flexbox would wrap.

## Resolving all three tickets (Problem 9)

`data/campus_customs_new.db` was reset to the original seed, and the starting checking balance was
confirmed at **$3,400.00** before running anything.

**A real architecture bug, found only by trying to finish the job.** Accounting's Problem 5 prompt
said *never* call `make_payment` unless told mid-conversation that a human already approved it —
which sounded safety-conscious, but actually made the `approval_required()` framework gate
(Accounting formally proposing a payment by attempting the call, then the framework pausing it)
unreachable in normal operation: Accounting would only ever **describe** a payment in a note, never
propose one the dashboard could act on. There was no way to fully resolve a ticket this way. Fixed
`accounting.md` to say the opposite: calling `make_payment` *is* the safe, correct way to formally
propose a payment, since the tool itself cannot execute without a human — attempting it isn't
risky, it's the whole point of having built the gate. This single fix is what made every real
approval in this problem possible.

**A real budget-tuning bug, found the same way.** Ticket #103's first real attempt hit the shared
40-request budget *before* Boss could close the ticket — not a runaway loop, but legitimate work (a
stock check, a margin check, and a payment consideration) compounded by real over-delegation: every
agent, not just Boss, was independently re-asking teammates questions Boss already had answers for.
Fixed by adding "don't re-delegate redundantly" guidance to all five prompts (not just Boss's) and
raising `REQUEST_LIMIT`/`TOTAL_TOKENS_LIMIT` from 40/80k to 110/220k as a safety margin for
legitimately heavier tickets. Ticket #103's final resolving run took 6 agent-loop steps at Boss's
level instead of hitting the ceiling.

**The run itself**, ticket by ticket, cash tracked live via `GET /api/cash` after each approval:

| Ticket | What happened | Cash effect |
| --- | --- | --- |
| **#101** | Inventory found the size-S tee out of stock, blocked by Bulldog Print Co's open invoice #501. Accounting called `make_payment` for real — paused for approval. Approved by **Rahi Joshi**. | $3,400.00 → **$2,560.00** (−$840) |
| **#103** | Ran *after* #101 specifically so the vendor's invoice would already be clear. Needed two rounds of real human input mid-process — the requester's actual discount ask (15% off, supplied as a reply in the ticket's own notes) and confirmation that approving a discount isn't a `make_payment` action at all (no cash moves to grant a discount, and there's no tool to place a brand-new vendor purchase order — correctly left as a manual follow-up outside the system). | **$2,560.00** (unchanged) |
| **#102** | Facilities confirmed the $2,400 rent wasn't yet overdue; Accounting called `make_payment` for real — paused for approval. Approved by **Rahi Joshi**. | $2,560.00 → **$160.00** (−$2,400) |

**Ending balance: $160.00** ($3,400.00 − $840.00 − $2,400.00), confirmed against
`cash_accounts.balance` in `data/campus_customs_new.db` directly, not just trusted from the API.
All three tickets show `resolved`. Full itemization, and each ticket's Expected-vs-Actual
comparison (including the exact places real delegation differed from the Problem 6 plan), is in
[`output/desk_tickets.html`](desk_tickets.html). Per-ticket outcome, agent contributions, and the
two human approvals are in [`output/resolved_tickets.json`](resolved_tickets.json). Screenshots of
the real dashboard showing all three resolved are in
[`output/resolved_board.html`](resolved_board.html). `output/audit_trail.json` now holds every real
run from every problem, appended, never wiped — including the failed budget attempts on #103,
left in rather than cleaned up, since they're genuine evidence of a real bug and its fix.
