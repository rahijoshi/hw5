"""Shared data types for the Campus Customs agent team."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class Deps:
    """Per-run context threaded to every agent and every delegated sub-agent.

    `ticket_id` is the one piece of state the whole delegation tree shares —
    which ticket on the board this run is working. Everything else (stock,
    cash, lease terms...) comes from the MCP server, not from deps.
    """

    ticket_id: int


class AuditEntry(BaseModel):
    """One step of one agent's run, appended to `output/audit_trail.json` —
    never overwritten in place, so the file is a running history across
    every ticket run, not just the most recent one.

    `run_id` groups every entry for one ticket's whole delegation tree —
    Boss delegating to Inventory delegating to Accounting all share one
    run_id but are three different agents' steps, told apart by `agent`.
    `iteration` numbers the steps within one agent's own run, not across
    the whole tree. `tool_args` / `tool_result_summary` are truncated by
    the caller (see agent_team.py's `_summarize`) — an audit trail you
    can't read at a glance isn't auditable.
    """

    run_id: str
    ticket_id: int
    agent: str
    timestamp: str
    iteration: int
    thoughts: str = ""
    tool_name: str | None = None
    tool_args: dict | None = None
    tool_result_summary: str | None = None
    stop_reason: str | None = None
