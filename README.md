# Campus Customs — Multi-Agent Ops Board (HW 5, MGT 409)

Three pieces: an MCP server (`mcp_server/`) that owns all database access, a FastAPI backend
(`backend/`) running a 5-agent PydanticAI team on top of it, and a React dashboard (`frontend/`) a
human uses to watch the agents work and approve anything that touches cash.

See [`output/harness.md`](output/harness.md) for the full system writeup (tables, all 12 MCP
tools, the five agents, the API routes, the dashboard, the safety rules) and
[`AI_prompts.md`](AI_prompts.md) for the problem-by-problem build log.

## Setup

### 1. Get the code

```bash
git clone https://github.com/rahijoshi/hw5.git
cd hw5
```

Both `data/campus_customs.db` (the original, untouched) and `data/campus_customs_new.db` (the
working copy) are included in this repo — no separate data pack to unzip.

### 2. Fix `.mcp.json` for your machine

`.mcp.json` points the MCP server at an absolute Python path from the machine this was built on.
Regenerate it for your own clone:

```bash
python3 - <<'EOF'
import json, pathlib
p = pathlib.Path(".mcp.json")
data = json.loads(p.read_text())
data["mcpServers"]["campus-customs"]["command"] = str(pathlib.Path("mcp_server/.venv/bin/python").resolve())
data["mcpServers"]["campus-customs"]["args"] = [str(pathlib.Path("mcp_server/server.py").resolve())]
p.write_text(json.dumps(data, indent=2) + "\n")
EOF
```

(Run this *after* step 3 creates `mcp_server/.venv`.)

### 3. Python environments — two of them, on purpose

The MCP server and the backend need **separate virtual environments**. This isn't accidental
complexity — `pydantic-ai-slim[mcp]`'s own MCP client dependency is on the `mcp` package's newer
2.x line, which renamed `FastMCP` to `MCPServer`; the server in this repo is written against the
1.x `FastMCP` API the assignment specifies. Pinning one shared environment to satisfy both breaks
one of them. They only ever talk to each other over the MCP protocol as client/subprocess, so
mismatched versions between the two are a non-issue in practice (confirmed working — see
`output/harness.md`'s Problem 5 section).

Needs Python 3.10+. If your system Python is older, [uv](https://docs.astral.sh/uv/) is the
easiest way to get one without touching your system install: `curl -LsSf https://astral.sh/uv/install.sh | sh`,
then `uv python install 3.12`.

```bash
# Backend + agent team
python3 -m venv .venv          # or: uv venv .venv --python 3.12
.venv/bin/pip install -r requirements.txt   # or: uv pip install --python .venv/bin/python -r requirements.txt

# MCP server (separate env, separate requirements file)
python3 -m venv mcp_server/.venv
mcp_server/.venv/bin/pip install -r mcp_server/requirements.txt
```

### 4. Frontend (Node 20+)

```bash
npm install --prefix frontend
```

### 5. API key

```bash
cp .env.example .env
```

Open `.env` and fill in a real `PORTKEY_API_KEY`. Leave `MODEL_NAME` unset (defaults to
`gpt-6-luna`, which this assignment requires for every agent) or set it to `gpt-6-luna` explicitly.

## Running it

**The MCP server doesn't need to be started separately** — it's launched on demand, as a
subprocess, by anything that connects to it via `.mcp.json` (the backend's agent team, the
backend's plain REST routes, or an MCP-aware IDE). There's no standalone process to leave running.

**Backend** (FastAPI):

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

**Frontend** (React dashboard), in a second terminal from the repo root:

```bash
npm run dev --prefix frontend
```

Open `http://localhost:5173`. Pick a ticket, click Start agents, watch the feed, sign off on any
payment that comes up for approval.

**Reset the board** before a full three-ticket run (also available as a button on the dashboard
itself, or `POST /api/reset` once the backend is running):

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

**Command-line alternative** to the dashboard — runs every open ticket once, end to end, no UI:

```bash
.venv/bin/python backend/run_tickets.py
```

## Repo layout

```
hw5/
├── AI_prompts.md          prompt-by-problem build log
├── requirements.txt       backend + agent team deps (see Setup — mcp_server has its own)
├── .env.example
├── .mcp.json              MCP server registration (fix absolute paths — see Setup step 2)
├── data/
│   ├── campus_customs.db       original seed, never written to
│   └── campus_customs_new.db   working copy every tool reads/writes
├── mcp_server/
│   ├── server.py          FastMCP server, 12 tools
│   ├── requirements.txt   mcp<2 — see Setup step 3 for why
│   └── README.md
├── backend/
│   ├── main.py            FastAPI routes (see output/harness.md for the full list)
│   ├── agent_team.py      the 5-agent PydanticAI team, full connectivity, audit trail
│   ├── mcp_client.py      thin MCP client the plain REST routes use directly
│   ├── models.py
│   ├── run_tickets.py     CLI alternative to the dashboard
│   └── prompts/           one system prompt per agent
├── frontend/              React + Vite + TypeScript dashboard
└── output/
    ├── harness.md          full system writeup
    ├── mcp_smoke.json      Problem 4 MCP tool smoke test
    ├── desk_tickets.html   Problem 6 plan vs. Problem 9 actual, per ticket, plus cash itemization
    ├── design.md           dashboard design rationale
    ├── resolved_tickets.json
    ├── resolved_board.html screenshots of the real dashboard, all 3 tickets resolved
    ├── screenshots/
    └── audit_trail.json    every real agent-loop step, every run, appended
```
