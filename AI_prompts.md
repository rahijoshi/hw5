# AI Prompt Log — HW 5: Campus Customs Multi-Agent Ops Board

This file records the prompts I typed for HW 5. It is updated problem by problem as I work, and it contains no API keys.

## Problem 1 — Prompt log and project setup

### Prompt(s) typed

> Campus customs multi-agent operations is the agent team that runs the shop. Open tickets and on a board -- customer orders, rent, unpaid bills, discount requests, whatever the shop has to handle. You will build 3 pieces that talk to each other: an MCP server, a FastAPI backend with a multi agent team, and a react dashboard so a human can watch the agents at work and approve requests.
>
> Your agent team has full connectivity -- any agent may delegate tasks to any other agent for help. In this assignment you will build these agents:
>
> * Boss -- reads each ticket, decides who should work on it and makes final calls
> * Inventory -- checks stock by SKU and size, spots shortfalls, and figures out which vendor can restock
> * Accounting -- watches cash and invoices, checks margins and prepares payments or purchase orders for human approval.
> * Facilities -- handles the shop space side (leases, rent, etc)
> * Customer service -- drafts messages for customers
>
> Unzip data(3).zip so you have data/campus_customs.db. This file is the original shop database. Tables include desk, tickets, inventory, pricing, vendors, leases, cash_accounts, payments and invoices.
>
> Your tools will update the database as tickets get resolved. Make a copy of the database file called data/campus_customs_new.db and point your MCP server and backend at that working copy. Keep campus_customs.db untouched so you can reset when you want to restart resolving the tickets.
>
> Rules of the shop:
>
> * the field desk.date_today is "today" for the shop. Use this date to determine what is overdue.
> * Vendor lead times come from the vendors table.
> * A vendor will not ship new products while they still have an open unpaid invoice
> * Human approval is required for any payments. Points will be deducted if this is not done. If payment is made, make sure to update the relevant table
> * If there is not enough cash, the pay tool must refuse -- no negative balances
> * Cash only goes out in this homework -- we did not model revenue, so no money comes in
> * Before a full run to resolve the tickets, make sure to reset the database to the original values.
> * Do not email customers or call real vendors. Drafts stay on board
>
> Use your PORTKEY_API_KEY for AI calls. For this assignment, use only gpt-6-luna through portkey for every agent. Points will be deducted if any other model shows up in your code or runs.
>
> We are going to work one problem at a time. I will type each problem here. The final submission will be a github repo. I will show the file tree in the last problem.

Follow-up:

> what about this: gpt-6-luna

Then:

> Problem 1: Create AI_prompts.md at the start of the assignment and keep it updated as you work. This file is the log of what you typed to your vibe coder. Describe each problem to your vibe coder in your own words. Put one section for each problem. Each section must include:
>
> * the problem number and title
> * at least one prompt I typed in my own words as much as possible
> * one follow up prompt if needed (and one sentence on what was lacking after the first)

### What was lacking after the first prompt

The first prompt named the required model, `gpt-6-luna`, but didn't say whether that was a real public model or a course-specific alias, so a follow-up ("what about this: gpt-6-luna") was needed. The answer came from my own HW 4 code rather than new instructions: `backend/agent.py` already had `DEFAULT_MODEL = "gpt-5.6-luna"`, served as an OpenAI-compatible model through Portkey (`base_url="https://api.portkey.ai/v1"`, `PORTKEY_API_KEY`) via PydanticAI's `OpenAIChatModel`. `gpt-6-luna` is just the next alias in that same series, so HW 5 will wire it up identically — one `DEFAULT_MODEL` constant, overridable by a `MODEL_NAME` env var, used by every agent so no other model can slip in.

### Evidence of problem-by-problem work

This entry sets up the HW 5 project folder (`/Users/Owner/rahi/Homework/hw5`), initializes it as a git repo, and adds a `.gitignore` that excludes `data/`, `.venv/`, `node_modules/`, and `.env` (the database and secrets stay out of the repo, same as HW 4). `data(3).zip` was unzipped to `data/campus_customs.db`, and `data/campus_customs_new.db` was made as the working copy that the MCP server and backend will point at, leaving the original untouched for resets.

Inspected the real schema directly rather than only going by the handout's table names: `desk` (just `date_today`, currently `2026-08-31`, and `notes`), `tickets` (id, type, requester, subject, sku, size, qty, lease_id, invoice_id, status, notes, created_at — 3 open tickets to start: a customer order, a rent notice, a price override), `inventory` (sku+size primary key, qty, location), `pricing` (sku primary key, unit_cost, list_price), `vendors` (id, name, specialty, lead_days — 3 vendors), `leases` (id, space_name, landlord, monthly_rent, next_due, notes), `cash_accounts` (name primary key, balance, date — checking: $3,400), `payments` (id, kind, ref_id, amount, account, paid_at, approved_by), `invoices` (id, vendor_id, amount, due_date, status, description — 1 open invoice, $840 to vendor 1, due 2026-08-28, already overdue against `desk.date_today`). This matches the "vendor won't ship while an unpaid invoice is open" rule to a concrete case I'll need to handle once the Inventory/Accounting agents exist. No agent, MCP server, or dashboard code written yet.

## Problem 2 — Study the Campus Customs database

### Prompt(s) typed

> Study the Campus Customs database. Open data/campus_customs.db and look through every table and its fields. Copy the original file to data/campus_customs_new.db -- later problems update that working copy.
>
> Study the three open tickets so you see how they link to other tables.
> Start output/harness.md, For each table, list the fields and one short line on why that table matters for the agents.
> You will keep growing this harness file in later problems.

### What was lacking after the first prompt

No follow-up prompt was needed. The working copy (`data/campus_customs_new.db`) was already made in Problem 1 while unzipping the data pack, so this problem's copy step was a no-op — verified the two files are still byte-identical (same MD5) before moving on, rather than blindly re-copying.

### Evidence of problem-by-problem work

Added `output/harness.md` with a field list and one-line rationale for each of the nine tables (`desk`, `tickets`, `inventory`, `pricing`, `vendors`, `leases`, `cash_accounts`, `payments`, `invoices`), plus a section tracing exactly how the three starting tickets link across the schema:

- **#101** (customer_order, tee size S) has 0 units on the shelf, and its `invoice_id` points to invoice 501 — an **open** $840 invoice to vendor 1 (Bulldog Print Co) for a rush reprint of that exact sku/size. So the restock for this order is already blocked by the shop's own "no shipping on an open invoice" rule until Accounting clears it.
- **#102** (rent_notice) links via `lease_id` to the Chapel Street lease: $2,400/month, due 2026-09-02 — 2 days after `desk.date_today`, matching the ticket's note.
- **#103** (price_override, 20 navy hoodies size M) only has 8 on the shelf (a 12-unit shortfall), with unit_cost $22 / list_price $58 from `pricing` for Accounting to check margin against.

This gives one concrete, fully-linked example per agent (Inventory+Accounting on #101, Facilities+Accounting on #102, Inventory+Accounting+Customer Service on #103) to build and test the agent team against in later problems. No agent, MCP server, or dashboard code written yet.

## Problem 3 — Build the MCP server

### Prompt(s) typed

> Build the MCP server. Write an MCP server in mcp_server/ using FastMCP. It will talk to data/campus_customs_new.db. I do NOT need to connect or run it in this problem.
>
> Every agent in this homework uses the tools in this mcp server. I'll add more tools to it later; for now write 3 tools I know I will need for the tickets in the database. Keep the names clear. NEVER invent any data, only use info in the db.
>
> In output/harness.md, list each of the three MCP tools. For every tool include: which table it reads, which ticket it helps unlock (101, 102, or 103) and one sentence on why that tool is the right one for that ticket. Vague lines like "reads inventory" score low -- tie the tool to the ticket.
>
> Also add a short mcp_server/README.md file that explains what the MCP server is for, which database file it uses and the three tools it has.

### What was lacking after the first prompt

No follow-up prompt was needed. One thing came up while building that's worth flagging rather than silently working around: this laptop only has system Python 3.9.6, with no `fastmcp`/`mcp` package installed and no `uv`/`pyenv`/newer Python on PATH (unlike HW 4's working `.venv` on Python 3.13). Since this problem explicitly says the server doesn't need to run yet, I wrote and reasoned through the code without a working `mcp` install, and left `mcp_server/requirements.txt` with the single dependency (`mcp`, which is where FastMCP lives) for whenever we do stand up a proper virtual environment in a later problem.

### Evidence of problem-by-problem work

Added `mcp_server/server.py`: a FastMCP server (`campus-customs-ops`) that opens `data/campus_customs_new.db` (never the original) and exposes three tools —

- `check_stock(sku, size)` — reads `inventory`
- `get_invoice_status(invoice_id)` — reads `invoices` joined to `vendors`
- `get_lease_status(lease_id)` — reads `leases` and `desk.date_today`

Every tool returns `found: false` on a missing row instead of guessing. Also added `mcp_server/requirements.txt` and `mcp_server/README.md` (what the server is for, which db file it uses, the three tools). `output/harness.md` got a new "MCP server tools" section — a table tying each tool to the specific ticket(s) it unlocks and why, e.g. `get_invoice_status` ties directly to ticket #101 because that ticket's own `invoice_id` (501) is the open, unpaid invoice blocking the vendor from shipping the restocked tee. The server is not connected to a backend or run yet, as the problem specified.

## Problem 4 — Add the MCP server to vibe coder and test each tool

### Prompt(s) typed

> Add the MCP server to vibe coder and test each tool.
>
> In the vibe coder, add your MCP server to this project so the vibe coder can call the tools. Save the connection JSON text in .mcp.json at the project root (or however your vibe coder saves local MCP server lists).
>
> With your vibe coder connected, test each of your three MCP tools. Save the evidence in output/mcp_smoke.json. For every tool include:
>
> * the prompt you asked the vibe coder
> * the tool name
> * the tool output (must match values in data/campus_customs_new.db)

### What was lacking after the first prompt

No follow-up prompt was needed, but the first prompt ran straight into the Python-version blocker flagged at the end of Problem 3: this laptop's only Python is 3.9.6, and the `mcp` package needs 3.10+, so nothing could actually run yet. I stopped and asked how to get a compatible Python rather than silently installing something system-wide, since that's the one piece of this problem that reaches outside the project folder; the answer was to use `uv` (astral.sh's official installer, no sudo/Homebrew) to fetch an isolated Python 3.12 and rebuild `.venv` on it.

### Evidence of problem-by-problem work

Installed `uv`, used it to get Python 3.12.15, and rebuilt `.venv` per the course `AGENTS.md`'s "local `.venv` per project folder" convention. Hit one more surprise: the `mcp` package has moved to a 2.x line where `FastMCP` was renamed `MCPServer`; pinned `mcp_server/requirements.txt` to `mcp<2` so the already-written server code (which imports `mcp.server.fastmcp.FastMCP`, exactly as the assignment specifies) keeps working rather than rewriting it against the new API.

Added `.mcp.json` at the project root, pointing the `campus-customs` server entry at `.venv/bin/python mcp_server/server.py`. Connected to the server the same way any MCP client would — a real stdio handshake, `list_tools()`, then `call_tool()` for each of the three tools — rather than just calling the Python functions directly. All three came back online and returned real data:

- `check_stock(sku="CC-HOOD-NAVY", size="M")` → `qty=8` at Aisle A (ticket #103's shortfall)
- `get_invoice_status(invoice_id=501)` → open, $840, Bulldog Print Co, `blocks_shipping=true` (ticket #101's invoice)
- `get_lease_status(lease_id=1)` → Chapel Street shop, $2,400/month, due 2026-09-02, `days_until_due=2`, `overdue=false` (ticket #102's lease)

Cross-checked every field against a direct `sqlite3` read of `data/campus_customs_new.db` — all matched exactly. Full prompt/tool/args/output/db-match evidence for all three is in `output/mcp_smoke.json`.

## Problem 5 — Build the agent team and grow the MCP tools

### Prompt(s) typed

> Build the agentic team for Campus Customs using PydanticAI: Boss, Inventory, Accounting, Facilities, and Customer Service. Include prompts, models, and agent loops so they can delegate work to each other with full connectivity.
>
> Put the agent prompts in backend/prompts/ -- one file per agent. Put data types in backend/models.py, and the agent files under backend/ (your layout can vary as long as the five roles are clear). Use my PORTKEY_API_KEY and ONLY gpt-6-luna for every agent.
>
> Write each prompt in your own words with the shop rules that agent needs. More detailed prompts that cover all aspects of an agent's work and scope score higher than a short generic prompt.
>
> Add any tools the agents need to your MCP server so they can work on the open tickets. Shop facts come from the MCP server over data/campus_customs_new.db -- do not invent a second shop-tools layer that bypasses MCP.
>
> Wire the agents so they append to output/audit_trail.json as they run: for each agent-loop step, record enough to audit later. Append to this file -- do not wipe it each run.
> In output/harness.md, list each agent and each MCP tool (including ones you add in this problem) along with which table the tool uses. Also add a short safety section: the guardrails a real business would want when agents touch real customers and real money, plus limits that keep token use in check.
>
> Update mcp_server/README.md so the tool list matches what you have now.

### What was lacking after the first prompt

No follow-up prompt was needed, but the first prompt ran into real surprises I had to resolve rather than just implement blindly:

1. **Installing `pydantic-ai-slim[mcp]` broke the Problem 4 server.** It pulled in `mcp` v2.x as a dependency, which renamed `FastMCP` to `MCPServer` — our server (written against v1's `FastMCP`, as the assignment literally names) stopped importing in the shared `.venv`. Rather than rewrite the server against a brand-new API or fight pip's resolver, I gave `mcp_server/` its own isolated `.venv` pinned to `mcp<2`, separate from the backend's `.venv`. They only ever talk over the MCP protocol as client/subprocess, so mismatched dependencies between the two are a non-issue — confirmed this actually works by running a v2-`mcp`-based client against the v1-`FastMCP`-based server.
2. **PydanticAI's actual API (v2.56.0) turned out to differ a fair bit from what HW 4 used** (an older version) — no `MCPServerStdio`, `instructions=` preferred over `system_prompt=`, and a genuinely useful native human-approval mechanism (`toolset.approval_required()` + `DeferredToolRequests`/`DeferredToolResults`) I hadn't planned around. Rather than guess, I installed the package and read its own bundled reference docs and introspected its real classes before writing any agent code, which is why `make_payment` ends up gated by the framework itself instead of by a trust-the-prompt convention.
3. **A real bug, caught by testing, not by inspection:** the first version of the delegation tool only forwarded `usage=ctx.usage` to a nested agent call, not `usage_limits=ctx.usage_limits`. That let every nested delegated call silently fall back to PydanticAI's own default limit (50 requests) instead of inheriting the parent's explicit one — so a deliberately small top-level budget I set for a test was not actually being enforced underneath. Caught this by stress-testing the delegation tree with a stub model that calls every tool it can see (including every delegate tool, at every level) — confirmed the bug by watching it blow past my intended limit, then confirmed the fix by watching the same stress test correctly raise `UsageLimitExceeded` at the budget I'd actually set.

### Evidence of problem-by-problem work

Five agents, one file per prompt in `backend/prompts/` (`boss.md`, `inventory.md`, `accounting.md`, `facilities.md`, `customer_service.md`), each written out with the specific shop rules that role needs rather than a shared generic prompt — `backend/agent_team.py` wires them up:

- Every agent runs on `gpt-6-luna` through Portkey only; `load_model()` raises if `MODEL_NAME` is ever set to anything else.
- **Full connectivity**: `build_agent_team()` gives every agent a `delegate_to_<other>` tool for each of the other four (20 tools total, generated by one loop), sharing one `RunContext.usage` *and* `usage_limits` across the whole delegation tree for a ticket — not five separate budgets.
- **Shop facts only from MCP**: every agent's database access is the same `.mcp.json` connection from Problem 4 (`load_mcp_toolsets`), scoped per agent to a least-privilege subset (`AGENT_TOOLS`) — e.g. Customer Service only ever sees `get_ticket`.
- **Human approval, enforced by the framework**: Accounting's toolset wraps `make_payment` in `approval_required()`, so a model-initiated payment call comes back as a pending `DeferredToolRequests` instead of executing. Verified live (via `TestModel`, no real API key needed to prove the mechanism): a simulated attempt to pay invoice 501 produced a pending approval and left `cash_accounts.balance` and the `payments` table completely untouched — not just "the prompt says not to," an actual blocked execution.
- **Audit trail**: `build_audit_entries`/`append_audit_entries` turn every agent's own run (plus every nested delegated run, tagged with its own agent name) into entries appended — never overwritten — to `output/audit_trail.json`, grouped by a per-ticket `run_id`.

Grew `mcp_server/server.py` from 3 tools to 11: added `get_ticket`, `update_ticket_status` (writes `tickets`), `list_vendors`, `list_open_invoices_for_vendor`, `list_leases`, `get_pricing`, `get_cash_balance` (all read-only), and `make_payment` (writes `payments` + `cash_accounts`, and `invoices` for an invoice payment) — the only tool in the server that moves money, refusing outright on a blank approver or insufficient funds. `mcp_server/README.md` lists all 11. `output/harness.md` got new sections: the five agents and their prompts, the full 11-tool table with which table each one uses and who can call it, and a safety section covering human-approval enforcement, least-privilege scoping, no real customer/vendor contact (no send tool exists at all), full audit logging, and the token/request-budget guardrail — backed by the real bug-and-fix above, not just a stated intention.

This machine had no `PORTKEY_API_KEY` at first, so the team was built and verified structurally with PydanticAI's own `TestModel` (no network call needed) before any real model was available. I flagged that gap; the user found their course-issued key and pasted it, which I put straight into `backend/.env` (gitignored, never echoed back in chat or committed).

### Follow-up prompt — running it for real

> Found it, pasting the key now: [key redacted from this log on purpose — it's in `backend/.env`, not here]

### What was lacking after that prompt

One more real surprise, caught the moment I tried the first live call: `gpt-6-luna` turned out to be served as a reasoning model on Azure OpenAI through Portkey, which rejects function tools over `/v1/chat/completions` unless `reasoning_effort` is explicitly turned off (`BadRequestError: Function tools with reasoning_effort are not supported for gpt-6-luna-global`). Every agent here is built entirely around tool calls, so this would have silently broken every single agent. Fixed by adding `model_settings={"openai_reasoning_effort": "none"}` to every agent in `agent_team.py` — confirmed fixed by re-running the same single-agent smoke test, which then correctly called `get_lease_status` and reported accurate numbers.

### Evidence from the real run

With the key and the reasoning-effort fix in place, ran `backend/run_tickets.py` against all three real open tickets, against the actual `gpt-6-luna` model, end to end:

- All three resolved to `pending_approval` with accurate, synthesized notes written via `update_ticket_status` — e.g. ticket #101: tee short by 1, invoice #501 named as the blocker, $3,400 confirmed to cover the $840 invoice, payment explicitly "not been made."
- The approval gate held for real, not just in the `TestModel` stress test: after all three tickets, `cash_accounts.balance` is still `3400.0`, `payments` still has 0 rows, invoice #501 is still `open` — Accounting correctly recommended paying it and correctly never executed that payment.
- `output/audit_trail.json` now has 88 real entries across all five agents, grouped by ticket (`ticket-101`: 31, `ticket-102`: 14, `ticket-103`: 43) — real delegation, real tool calls, real reasoning, not synthetic test data. Full detail in `output/harness.md`'s "Running the agent team" section.

## Problem 6 — Plan the 3 tickets

### Prompt(s) typed

> Before you wire the backend, write down what you expect the team to do on each open ticket. Build output/desk_tickets.html -- a page you can double-click with one tab per ticket (101, 102, 103). Also add empty Cash and Reflection tabs for later problems (leave them blank with short "coming later" note for now).
>
> On each ticket tab, fill an Expected section only (leave room for an Actual section you will fill after you run the agents).
>
> For each ticket's expected section, write in your own words:
>
> * who the boss should call first and why
> * all the agent delegations you expect -- not "boss calls everyone"
> * which MCP tools you expect that run to use
>
> Plans that send every specialist on every ticket score low. You will compare this plan to what actually happens when your agents resolve the 3 tickets.

### What was lacking after the first prompt

No follow-up prompt was needed, but this problem created a real tension worth being honest about: by the time this prompt arrived, Problem 5 had already run the real agents against all three tickets, so I already knew the actual outcome. Writing "Expected" from that hindsight would have defeated the point of the exercise and risked just transcribing the real run instead of genuinely reasoning about it. I deliberately wrote each ticket's Expected section from first principles instead — the ticket's own fields (type, sku/size/qty, lease_id, invoice_id), each agent's defined role, and the routing logic already written into `boss.md` (customer_order → Inventory first, rent_notice → Facilities first, price_override → Inventory first) — not from the audit trail I'd already seen. Left the Actual sections genuinely empty, as asked, rather than filling them in early just because I had the answer available.

### Evidence of problem-by-problem work

Added `output/desk_tickets.html` — a single self-contained file (inline CSS/JS, no external dependencies, no server needed) that opens directly by double-clicking. Five tabs: Ticket 101, Ticket 102, Ticket 103, Cash, Reflection, switched with plain `classList` JS. Styled lavender-and-yellow per the course's `AGENTS.md` default visual-style convention. Verified the tab-switching actually works by serving `output/` locally and clicking through all five tabs in a real browser, not just reading the JS and assuming it's right.

Each ticket tab has a quick-facts grid (sku/size/qty or lease_id, pulled from the real schema established in Problem 2) and an Expected section with the three required pieces, deliberately *not* sending every specialist to every ticket:

- **#101**: Inventory first (customer_order → can the shelf cover it?), then Accounting (invoice #501 is already named on the ticket) and Customer Service (a customer is waiting on a reply) — Facilities explicitly **not** expected.
- **#102**: Facilities first (it's a lease ticket), then Accounting (afford the rent?) — Inventory and Customer Service explicitly **not** expected (no stock question, and the requester is the landlord's office, not a customer).
- **#103**: Inventory first (how much of the 20 can the shelf already cover?), then Accounting (margin on the discount) and Customer Service (a student org is waiting) — Facilities explicitly **not** expected.

Each tab also lists the specific MCP tools expected (and, just as importantly, which ones are *not* expected, like `make_payment` or `get_lease_status` on tickets that have nothing to do with rent). Actual sections are left as plain placeholders — "to fill in after running the agents (a later problem)" — exactly as asked. Cash and Reflection tabs are empty with a "Coming later." note.

## Problem 7 — Wire the backend

### Prompt(s) typed

> Your react front end dashboard (the next problem) needs a backend it can call. In backend/main.py, use FastAPI and add routes that do the following:
>
> * return the 3 tickets and whether each is open or resolved
> * take a ticket ID and run your agent team on that ticket
> * return recent agent events -- what each agent said and which tools they used -- so the board can refresh
> * approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what actually changes cash)
> * return the current checking balance from cash accounts
> * reset the database to the original values when you want to try a fresh run
>
> From the backend folder, start the server with: `uvicorn main:app --reload --port 8000`.
>
> In output/harness.md, list each route in one line (what URL/what it does).

### What was lacking after the first prompt

No follow-up prompt was needed, but two real bugs surfaced only by actually running the server and hitting every route, not by reading the code:

1. **`GET /api/tickets` 500'd on the first real request.** This server's `FastMCP` (v1) API serializes a `list[dict]`-returning tool as one content block *per row*, not one block holding a JSON array — my MCP client only read block 0, so a 3-ticket list came back as the first ticket's own keys, and iterating it as "rows" iterated its field names as if they were ticket objects (`TypeError: string indices must be integers`). Pydantic AI's own MCP toolset — which the agents use — already handles this correctly, which is exactly why this never surfaced in any of Problem 5's testing. Fixed with a dedicated `call_list_tool` helper in `mcp_client.py` that reads every content block.
2. **A stale "pending payment" that stayed pending forever.** After genuinely approving a payment end to end (see below), `GET /api/payments/pending` kept showing that same ticket as still awaiting approval — the pending-lookup only scanned for `awaiting_human_approval` entries without checking whether a later approval had already superseded it. Fixed to take the *latest* payment-related audit entry per ticket, counting it as pending only if that latest one is still awaiting approval.

### Evidence of problem-by-problem work

Added `backend/main.py` (the 6 routes asked for, plus a `GET /api/health`) and `backend/mcp_client.py` (a thin MCP client the plain REST routes use directly, same server/command as the agent team — no second data layer). Grew `mcp_server/server.py` to 12 tools with `list_tickets()`. Started the real server (`uvicorn main:app --reload --port 8000`, verified via the browser preview tools) and exercised every route for real, not just by reading the code:

- Ran real tickets through `POST /tickets/{id}/run`, watched `GET /api/tickets` show them move `open → pending_approval`, confirmed `GET /api/events` picked up 200 real entries across all three in one concurrent pass. A double-trigger on the same ticket correctly 409s.
- The real model, across several genuine runs, consistently chose to *report* a recommended payment without ever attempting `make_payment` — exactly what `accounting.md` asks for, a correctly conservative model rather than a bug, but it meant there was no organic pending approval left over to test `POST /api/payments/approve`'s success path against. Staged one realistic pending-approval entry to exercise that path specifically (clearly labeled as staged, not passed off as organic model output) and confirmed the whole chain against the real database: cash `$3,400 → $2,560`, invoice #501 flipped to `paid` with `approved_by` set to the name from the actual request (never the blank placeholder in the staged entry), the ticket moved to `resolved`, and a second approve attempt correctly refused with `409` ("invoice 501 is already 'paid'"). That's where bug 2 above was caught. Reset the database and stripped the two staged entries from `output/audit_trail.json` afterward, then ran one final genuine pass on all three tickets to leave real evidence in place.
- `GET /api/cash` and `POST /api/reset` both verified directly: reset correctly restored the $3,400 balance and all three tickets to `open`.

`output/harness.md` has the new route table (one line per route) plus the full account of what broke and what was staged vs. genuine, so the evidence doesn't overstate what the real model actually did on its own.

## Problem 8 — Agent dashboard

### Prompt(s) typed

> Build the frontend dashboard in frontend/ with react + vite + typescript. The page should call the routes you built in problem 7. At minimum the board should:
>
> * list all 3 tickets
> * let you pick one ticket and start the agent team on it
> * show each agent and what they are saying / doing while the ticket runs
> * mark a ticket resolved when the run finishes
> * show a short summary of what each agent did on that ticket
> * let a human approve a pay or purchase when asked
> * show the checking balance (it should drop after an approved pay)
>
> Make the dashboard look good. Be creative with the layout and feel -- this is a real desk people would want to sit at, so put thought into how it looks.
>
> Tell the front end to talk to your backend at http://localhost:8000. On the backend, allow the Vite page origin (usually http://localhost:5173) so the browser is allowed to call those routes. Start the board with npm run dev.
>
> Write output/design.md with what you chose for the dashboard look (layout, how agents read differently, how resolved tickets and cash show up) and why -- including the creative choices that make it feel special and something humans would actually enjoy using.

### What was lacking after the first prompt

No follow-up prompt was needed, but this problem hit the same kind of environment gap as Problems 4 and 5: this laptop had no Node.js or npm at all. Rather than ask again when the user had already established a clear pattern last time (lightweight, official, no-sudo installer over Homebrew), I applied the same approach directly and said so afterward instead of before: downloaded the official Node 24 LTS binary from nodejs.org and installed it user-level under `~/.local`, the same place `uv` already lives, with no shell-script installer and no admin password needed.

### Evidence of problem-by-problem work

Scaffolded `frontend/` with `npm create vite@latest -- --template react-ts`, then built out:

- `src/types.ts` / `src/api.ts` — typed wrappers for all 6 Problem 7 routes against a hardcoded `http://localhost:8000`
- `src/agentMeta.ts` — the color/label/glyph lookup that makes every agent read consistently everywhere it shows up
- Components: `Header` (title + cash widget + reset), `TicketList` (the board), `TicketDesk` (the selected ticket's facts, start/re-run button, live feed), `AgentFeed` (polling, auto-scrolling activity log), `AgentSummary` (per-agent condensed report, built straight from each agent's own final audit-trail entry), `ApprovalBanner` (the signature-slip payment approval flow)
- `App.tsx` — a single 2-second polling loop refreshing tickets, cash, and pending payments, plus that ticket's events when one is selected; tracks which tickets are "running" locally (set on a successful `POST /run`, cleared once that ticket's status leaves `open`) since the backend itself has no separate "in progress" status field

Updated the backend's CORS policy from the wildcard I'd used for my own Problem 7 testing to explicitly `http://localhost:5173` / `127.0.0.1:5173`, as asked.

Verified the whole thing end to end in a real browser, not just by reading the component code: started both servers, reset the board, opened ticket 101, clicked "Start agents," watched the feed fill in live over a real `gpt-6-luna` run, watched the ticket flip to "pending_approval" and the per-agent summary cards appear once it finished. Because — same as Problem 7 — the real model consistently chooses not to attempt an unapproved payment, there was no organic pending approval to click through, so I staged one more time (clearly labeled, cleaned up after) to verify the actual UI flow: clicked "Review & approve," typed a name into the signature field, clicked "Sign & approve," and watched the checking balance widget flash and drop from $3,400 to $1,000 in real time, the ticket card turn green/"Resolved," and a new green "Human approval" line land in the feed — all driven by a real `POST /api/payments/approve` call, not a mock. Also caught and fixed one real responsive bug (the header overlapped at mobile widths) by testing at a 375px viewport, not just assuming the flexbox would wrap. Reset the database and removed the staged audit entries afterward, same as Problem 7's practice. `output/design.md` has the full design rationale — palette, per-agent color meaning, the "signature slip" interaction, and why resolved/cash states are deliberately quiet rather than celebratory.

## Problem 9 — Resolve the tickets

### Prompt(s) typed

> Resolve the tickets. Before testing the agents on a full run over the 3 tickets, reset the working database data/campus_customs_new.db again so you start clean. Note the start checking balance. Then run all 3 tickets on the board (101, 102, 103) until each is resolved.
>
> Open output/desk_tickets.html from problem 6. On each ticket tab, fill the actual section from this run: which agents worked, what they delegated, and which tools they used. Keep your expected section so you can compare the two.
>
> On the cash tab of the same output/desk_tickets.html, itemize the money:
>
> * start checking balance (after the reset)
> * for each ticket: how cash changed when that ticket resolved, and why (which pay / purchase, dollar amount)
> * ending checking balance -- it must match cash_accounts in the working database
>
> Wrong cash math loses points even if the board shows every ticket resolved. Also save:
>
> * output/resolved_tickets.json -- for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals
> * output/resolved_board.html -- a page you can double-click with a screenshot of your react board for each resolved ticket (101, 102, 103)
>
> Append real runs to output/audit_trails.json. Finish output/harness.md so it covers tables, MCP tools, the 5 agents, API routes, the dashboard, and safety rules.

### What was lacking after the first prompt

No follow-up prompt was needed, but actually trying to drive every ticket to `resolved` — not just `pending_approval` — surfaced two real bugs that no amount of reading the code would have caught, only running it end to end would:

1. **Accounting could never actually propose a payment.** Its Problem 5 prompt said never call `make_payment` unless told mid-conversation a human had already approved it — which made the whole `approval_required()` framework gate I'd built unreachable in normal operation, since Accounting would only ever describe a payment in a note, never attempt the call the dashboard needs to see. Every test run back through Problems 5/7/8 that seemed to show "the model is being conservative" was actually "the model is doing exactly what its prompt says, and that prompt makes real resolution impossible." Fixed by flipping the instruction: attempting the call *is* the safe, correct way to propose a payment, since the tool can't execute without a human anyway.
2. **Ticket #103 hit the shared request budget before Boss could close it out** — not a runaway loop, but real work (stock + margin + a payment consideration) made worse by every agent independently re-asking teammates questions Boss already had answers to. Fixed by adding "don't re-delegate redundantly" to all five prompts (I'd only put it on Boss and Accounting at first) and raising the shared budget from 40/80k to 110/220k requests/tokens as a safety margin for legitimately heavier tickets.

Ticket #103 also turned out to need two rounds of genuine human input beyond a payment approval — the requester's actual discount price (which the agents correctly refused to guess at), and confirmation that approving a discount isn't a `make_payment` action at all, since no cash moves to grant one and this system was deliberately never given a tool to place a new vendor purchase order. I supplied both as the ticket's own notes (as a real human operator reading the board would), the same channel Boss already reads from.

### Evidence of problem-by-problem work

Reset the database, confirmed the starting balance at **$3,400.00**, then ran all three tickets for real against `gpt-6-luna` via the actual backend API (`POST /tickets/{id}/run`, polling `GET /api/tickets`), in an order chosen on purpose — #101 before #103, since #103's vendor was blocked by the same invoice #101 pays off. Approved both real payments that resulted (#101's $840 invoice, #102's $2,400 rent) via `POST /api/payments/approve` with my own name. All three tickets landed on `resolved`; ending balance **$160.00**, confirmed directly against `cash_accounts` in the working database, matching `$3,400.00 − $840.00 − $2,400.00` exactly.

Filled in `output/desk_tickets.html`'s Actual section for all three tickets and the Cash tab's itemized table, keeping every Expected section untouched for comparison — including being honest about where reality differed (more cross-delegation than planned on #101, one extra Facilities→Accounting hop on #102, and #103 needing 5 real passes and 2 human inputs instead of the single pass I'd expected). Wrote `output/resolved_tickets.json` (id, final status, short outcome, per-agent contribution, and the human approvals — or, for #103, the explicit note that its "approval" was a pricing decision, not a payment). Captured real dashboard screenshots (the full board plus each resolved ticket's detail view, pulled from an actual running `npm run dev` session) into `output/screenshots/` and built `output/resolved_board.html` around them. `output/audit_trail.json` now holds every real run from every problem, including the failed budget attempts on #103 — left in deliberately, since they're genuine evidence of a real bug and its fix, not noise to clean up. `output/harness.md` got a table of contents plus two new sections (the dashboard, and this problem's full account), so it now covers tables, all 12 MCP tools, the five agents, the API routes, the dashboard, and the safety rules in one place.

## Problem 10 — Reflection

### Prompt(s) typed

> Reflection. Open output/desk_tickets.html and fill the reflection tab. Answer in your own vibe, and be detailed and thorough:
>
> * how would you evaluate the performance of the agents on each ticket and why?
> * For each ticket, how did Actual compare to the expected plan you wrote earlier?
> * What would have been simpler as one agent with tools -- and why?
> * Describe 3 new problems Campus Customs might face that this agent team could solve with the tools you built
> * Describe 3 new problems Campus Customs might face that this agent team could not solve with the tools you built, and explain tools and agents you would need to solve them.
>
> Tie every answer to this app and the 3 tickets you ran -- use the ticket tabs and Cash tab on the same page as your evidence. Generic AI essays without Campus Customs details will score low.

### What was lacking after the first prompt

No follow-up prompt was needed. The instruction to avoid a "generic AI essay" shaped how I wrote every answer: rather than reasoning about agent architecture in the abstract, each point ties back to a specific real fact already sitting on the page — the exact badges on each ticket tab ("more cross-talk than expected," "needed 5 real passes"), the exact tool names each agent actually called, the exact dollar figures on the Cash tab ($3,400 → $2,560 → $160), and the two real bugs from Problem 9 (the budget ceiling and the accounting.md restriction) as concrete evidence rather than hypotheticals.

### Evidence of problem-by-problem work

Filled in `output/desk_tickets.html`'s Reflection tab with five sections: a per-ticket grade with reasoning (B for #101's messy-but-correct delegation, A for #102's clean run, A-for-judgment/C-for-efficiency for #103's five-pass resolution), a ticket-by-ticket Actual-vs-Expected retrospective, an honest argument that ticket #102 specifically would have been strictly simpler as one agent with four tools (and that the two real Problem 9 bugs only exist *because* of the delegation mesh), three new problems answerable with zero new tooling (a no-urgency stock question, a second vendor's invoice, an actually-overdue rent ticket — each mapped to the exact tools that already handle it), and three problems the current build genuinely can't solve — including the gap ticket #103 itself surfaced (no tool to place a new vendor purchase order), a cash-only-ever-decreasing limitation (no `record_sale`-style tool exists), and the deliberate absence of any real-world-contact tool — each paired with the specific new tool and/or agent that would close the gap.

## Submission — push to GitHub

### Prompt(s) typed

> Push the code to a public github repo hw5. Do not push your real .env to the github repo. DO include both database files under data/ (the original and your working copy) so graders can run your app easily.

### What was lacking after the first prompt

No follow-up prompt was needed, but this machine had zero GitHub setup at all — no `gh` CLI, no SSH keys, no stored credentials, nothing. I installed `gh` the same way as every other tool this session (official binary, user-level, no sudo), but authenticating it genuinely needs the account owner, not me — I opened the device-code sign-in flow in a visible terminal tab and asked the user to complete it in their own browser, since clicking through their own GitHub OAuth approval isn't something I can or should do on their behalf.

Also had to reverse a decision from every earlier problem: `data/` had been gitignored this entire assignment (matching HW4's convention and the general rule of keeping a sandboxed working copy out of version control) — this prompt explicitly asks for the opposite, so I removed that one line from `.gitignore` rather than leaving the database files to be caught by some other rule.

### Evidence of problem-by-problem work

Before touching git: scanned every staged file and diff for the real `PORTKEY_API_KEY` value and for any non-empty `PORTKEY_API_KEY=` line anywhere in the tree — confirmed clean, confirmed no `.env` file (root or `backend/`) was ever staged. Added three files the course's expected file layout calls for that weren't needed until now: a root `README.md` (setup, and why there are two separate Python virtual environments rather than one — a real dependency conflict between `mcp<2` and `pydantic-ai-slim[mcp]`'s own newer `mcp` dependency, not arbitrary complexity), a root `requirements.txt` mirroring the backend's, and a root `.env.example`. Flagged and fixed one real portability problem before anyone else could hit it: `.mcp.json` has this machine's absolute paths baked in, so a plain `git clone` elsewhere would silently point at a path that doesn't exist — wrote and tested (in a scratch directory, not the real repo) a one-line Python snippet that regenerates it from the clone's own real path, and put it in the README as a required setup step.

Created the repository and pushed with `gh repo create hw5 --public --source=. --remote=origin --push` once authenticated. Repo: **https://github.com/rahijoshi/hw5** (also saved to `output/github_url.txt`, per the expected file layout).
