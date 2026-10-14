"""Campus Customs agent team — Boss, Inventory, Accounting, Facilities, and
Customer Service — built on PydanticAI.

Full connectivity: every agent gets a delegate_to_<other> tool for every
other agent (see _register_delegate_tool / build_agent_team), generated
once instead of hand-written 20 times.

Every shop fact comes from mcp_server/server.py via .mcp.json — no agent
gets a second, bypass path to the database. Tool access is scoped per
agent (AGENT_TOOLS) on least-privilege grounds, and only Accounting's
make_payment is wrapped in approval_required(), so the one tool that moves
money cannot run at all without a human approving it first — a framework
guarantee, not just a prompt instruction.

Every agent-loop step, across every agent delegation touches, is appended
to output/audit_trail.json (see build_audit_entries / append_audit_entries).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent, DeferredToolRequests, RunContext
from pydantic_ai.mcp import load_mcp_toolsets
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.toolsets import AbstractToolset
from pydantic_ai.usage import UsageLimits

from models import AuditEntry, Deps

ROOT = Path(__file__).parent
PROMPTS_DIR = ROOT / "prompts"
MCP_CONFIG_PATH = ROOT.parent / ".mcp.json"
AUDIT_PATH = ROOT.parent / "output" / "audit_trail.json"

# This assignment requires every agent to use this model and no other.
DEFAULT_MODEL = "gpt-6-luna"

# One ticket's whole delegation tree (Boss + however many teammates it
# calls, however many times) shares this budget — a hard ceiling against
# runaway back-and-forth delegation (A asks B asks A asks B...). Raised
# from an initial 40 after a real run on ticket #103 (a price-override
# ticket touching stock, margin, *and* a payment proposal) hit that limit
# before Boss could close the ticket out — legitimate multi-step work,
# not a runaway loop, needed more room.
REQUEST_LIMIT = 110
TOTAL_TOKENS_LIMIT = 220_000

MCP_SERVER_NAME = "campus-customs"  # must match the key in .mcp.json
MCP_TOOL_PREFIX = f"{MCP_SERVER_NAME}_"

# Least-privilege tool access per agent — see output/harness.md for why
# each one needs exactly these and not the others. Only Accounting gets
# make_payment, and that call is additionally gated by approval_required.
AGENT_TOOLS: dict[str, set[str]] = {
    "boss": {
        "get_ticket",
        "update_ticket_status",
        "check_stock",
        "get_invoice_status",
        "list_open_invoices_for_vendor",
        "get_lease_status",
        "list_vendors",
        "list_leases",
        "get_pricing",
        "get_cash_balance",
    },
    "inventory": {
        "get_ticket",
        "check_stock",
        "list_vendors",
        "list_open_invoices_for_vendor",
        "get_pricing",
    },
    "accounting": {
        "get_ticket",
        "get_cash_balance",
        "get_pricing",
        "get_invoice_status",
        "list_open_invoices_for_vendor",
        "get_lease_status",
        "list_leases",
        "make_payment",
    },
    "facilities": {
        "get_ticket",
        "get_lease_status",
        "list_leases",
    },
    "customer_service": {
        "get_ticket",
    },
}


def load_model() -> OpenAIChatModel:
    """OpenAI-compatible model served through Portkey — gpt-6-luna only.

    Tries backend/.env, then the repo root's .env (each a harmless no-op if
    that file doesn't exist); PORTKEY_API_KEY can also just be a real
    environment variable.
    """
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT.parent / ".env")
    key = os.environ.get("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set — copy .env.example to .env and fill it in.")
    model_name = os.environ.get("MODEL_NAME", DEFAULT_MODEL)
    if model_name != DEFAULT_MODEL:
        raise RuntimeError(
            f"MODEL_NAME is set to {model_name!r}; this assignment requires every agent to use "
            f"{DEFAULT_MODEL!r} and nothing else."
        )
    return OpenAIChatModel(model_name, provider=OpenAIProvider(base_url="https://api.portkey.ai/v1", api_key=key))


def _load_shop_toolset() -> AbstractToolset:
    """The one connection to mcp_server/server.py, loaded straight from
    .mcp.json — the same config file the vibe coder itself connects
    through (Problem 4). This is the only place any agent touches the
    database.
    """
    toolsets = load_mcp_toolsets(str(MCP_CONFIG_PATH))
    if len(toolsets) != 1:
        raise RuntimeError(f"expected exactly one MCP server in {MCP_CONFIG_PATH}, found {len(toolsets)}")
    return toolsets[0]


def _scoped_toolset(base: AbstractToolset, role: str) -> AbstractToolset:
    """Restrict `base` to the tools `role` is allowed to call, and — for
    Accounting only — require human approval before make_payment can run.
    """
    allowed_names = {f"{MCP_TOOL_PREFIX}{name}" for name in AGENT_TOOLS[role]}

    def _filter(ctx: RunContext[Deps], tool_def) -> bool:
        return tool_def.name in allowed_names

    scoped = base.filtered(_filter)
    if role == "accounting":
        payment_tool_name = f"{MCP_TOOL_PREFIX}make_payment"

        def _requires_approval(ctx: RunContext[Deps], tool_def, args: dict) -> bool:
            return tool_def.name == payment_tool_name

        scoped = scoped.approval_required(_requires_approval)
    return scoped


def _build_one_agent(role: str, shop_toolset: AbstractToolset) -> Agent[Deps, str | DeferredToolRequests]:
    instructions = (PROMPTS_DIR / f"{role}.md").read_text(encoding="utf-8")
    return Agent(
        load_model(),
        name=role,
        deps_type=Deps,
        output_type=[str, DeferredToolRequests],
        instructions=instructions,
        toolsets=[_scoped_toolset(shop_toolset, role)],
        retries=2,
        # gpt-6-luna is served as a reasoning model on Azure OpenAI through
        # Portkey, which rejects function tools over /v1/chat/completions
        # unless reasoning_effort is explicitly turned off — every agent
        # here depends on tool calls, so this is required, not cosmetic.
        model_settings={"openai_reasoning_effort": "none"},
    )


def build_agent_team() -> dict[str, Agent[Deps, str | DeferredToolRequests]]:
    """Build all five agents and wire full connectivity: every agent gets a
    delegate_to_<other> tool for every other agent, so any of the five may
    hand work to any other, in any order, as many times as the shared
    request budget allows.
    """
    shop_toolset = _load_shop_toolset()
    agents = {role: _build_one_agent(role, shop_toolset) for role in AGENT_TOOLS}

    for name, agent in agents.items():
        for target_name, target_agent in agents.items():
            if target_name == name:
                continue
            _register_delegate_tool(agent, target_name, target_agent)

    return agents


def _register_delegate_tool(agent: Agent, target_name: str, target_agent: Agent) -> None:
    """One delegate_to_<target> tool, built the same way for every
    (agent, target) pair — this is what gives the team full connectivity
    without hand-writing 20 near-identical functions.
    """

    async def delegate(ctx: RunContext[Deps], request: str) -> str:
        result = await target_agent.run(
            request,
            deps=ctx.deps,
            usage=ctx.usage,
            usage_limits=ctx.usage_limits,
            run_id=ctx.run_id,
        )
        entries = build_audit_entries(
            run_id=ctx.run_id or "unknown-run",
            ticket_id=ctx.deps.ticket_id,
            agent=target_name,
            messages=result.new_messages(),
        )
        if isinstance(result.output, DeferredToolRequests):
            if entries:
                entries[-1].stop_reason = "awaiting_human_approval"
            append_audit_entries(entries)
            pending = ", ".join(
                f"{call.tool_name}({call.args_as_dict()})" for call in result.output.approvals
            )
            return (
                f"{target_name} drafted an action that requires human approval and did NOT "
                f"execute it: {pending}. Treat this ticket as pending_approval until a human "
                "signs off."
            )
        append_audit_entries(entries)
        return str(result.output)

    agent.tool(
        delegate,
        name=f"delegate_to_{target_name}",
        description=(
            f"Hand this request to {target_name} and wait for their answer. "
            f"Use this when the work is really {target_name}'s job, not yours."
        ),
    )


# ---------- Audit trail ----------

FINAL_RESULT_TOOL_NAME = "final_result"


def _summarize(value: object, limit: int = 300) -> str:
    """Truncate anything bound for the audit trail — short args/result, not
    a full dump. An entry you can't read at a glance isn't auditable."""
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build_audit_entries(
    run_id: str,
    ticket_id: int,
    agent: str,
    messages: list[ModelMessage],
) -> list[AuditEntry]:
    """Turn one agent's own run (not including anything a delegated
    sub-agent did — that's logged separately, tagged with its own agent
    name) into one AuditEntry per agent-loop iteration.

    An "iteration" is either a tool call the model made (one entry per
    call, including delegate_to_* calls) or, if the model answered with no
    tool call at all, the plain response itself.
    """
    tool_results: dict[str, str] = {}
    for request_message in messages:
        if request_message.kind == "request":
            for part in request_message.parts:
                if part.part_kind == "tool-return":
                    tool_results[part.tool_call_id] = _summarize(part.content)

    entries: list[AuditEntry] = []
    iteration = 0
    for response_message in messages:
        if response_message.kind != "response":
            continue
        thoughts = " ".join(
            part.content
            for part in response_message.parts
            if part.part_kind in ("text", "thinking") and part.content
        ).strip()
        tool_calls = [part for part in response_message.parts if part.part_kind == "tool-call"]
        timestamp = response_message.timestamp.isoformat()

        if not tool_calls:
            iteration += 1
            entries.append(
                AuditEntry(
                    run_id=run_id,
                    ticket_id=ticket_id,
                    agent=agent,
                    timestamp=timestamp,
                    iteration=iteration,
                    thoughts=thoughts,
                    stop_reason="completed",
                )
            )
            continue

        for call in tool_calls:
            iteration += 1
            is_final = call.tool_name == FINAL_RESULT_TOOL_NAME
            entries.append(
                AuditEntry(
                    run_id=run_id,
                    ticket_id=ticket_id,
                    agent=agent,
                    timestamp=timestamp,
                    iteration=iteration,
                    thoughts=thoughts,
                    tool_name=call.tool_name,
                    tool_args=call.args_as_dict(),
                    tool_result_summary=tool_results.get(call.tool_call_id, ""),
                    stop_reason="completed" if is_final else None,
                )
            )
    return entries


def append_audit_entries(entries: list[AuditEntry]) -> None:
    """Append to output/audit_trail.json without wiping prior runs' entries.

    Read-modify-write rather than a true append-only file format: at this
    homework's volume that's instant, and it keeps the file a single valid
    JSON array a reviewer can open directly.
    """
    if not entries:
        return
    existing: list[dict] = []
    if AUDIT_PATH.is_file():
        try:
            loaded = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            existing = loaded if isinstance(loaded, list) else [loaded]
        except json.JSONDecodeError:
            existing = []
    existing.extend(entry.model_dump() for entry in entries)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


def append_audit_failure(run_id: str, ticket_id: int, agent: str, error: Exception) -> None:
    """Logged when an agent's `run()` itself raises — a bad model response,
    a hit usage limit, a network error — so a failed run still leaves a
    trace instead of silently vanishing from the audit trail.
    """
    append_audit_entries(
        [
            AuditEntry(
                run_id=run_id,
                ticket_id=ticket_id,
                agent=agent,
                timestamp=datetime.now(timezone.utc).isoformat(),
                iteration=0,
                stop_reason=f"failed: {error}",
            )
        ]
    )


async def run_ticket(ticket_id: int) -> str:
    """Run the whole agent team against one ticket, starting with Boss.
    Appends every step, across every agent delegation touches, to the
    audit trail, and returns Boss's final report.
    """
    agents = build_agent_team()
    boss = agents["boss"]
    run_id = f"ticket-{ticket_id}"
    deps = Deps(ticket_id=ticket_id)

    try:
        result = await boss.run(
            f"Handle ticket {ticket_id}. Start by calling get_ticket to see exactly what it needs.",
            deps=deps,
            run_id=run_id,
            usage_limits=UsageLimits(request_limit=REQUEST_LIMIT, total_tokens_limit=TOTAL_TOKENS_LIMIT),
        )
    except Exception as error:
        append_audit_failure(run_id, ticket_id, "boss", error)
        raise

    entries = build_audit_entries(run_id=run_id, ticket_id=ticket_id, agent="boss", messages=result.new_messages())
    if isinstance(result.output, DeferredToolRequests) and entries:
        entries[-1].stop_reason = "awaiting_human_approval"
    append_audit_entries(entries)

    if isinstance(result.output, DeferredToolRequests):
        pending = ", ".join(f"{c.tool_name}({c.args_as_dict()})" for c in result.output.approvals)
        return f"Boss attempted an action that requires human approval and did NOT execute it: {pending}"
    return str(result.output)
