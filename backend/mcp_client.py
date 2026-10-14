"""Thin async MCP client for the backend's plain REST routes.

Connects to the exact same server as the agent team (mcp_server/server.py,
command/args read straight from .mcp.json) — so a route like GET
/api/tickets or GET /api/cash goes through the same single data layer an
agent would, never a second bypass path to the database.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).parent
MCP_CONFIG_PATH = ROOT.parent / ".mcp.json"
MCP_SERVER_NAME = "campus-customs"


def _server_params() -> StdioServerParameters:
    config = json.loads(MCP_CONFIG_PATH.read_text(encoding="utf-8"))
    server = config["mcpServers"][MCP_SERVER_NAME]
    return StdioServerParameters(command=server["command"], args=server["args"])


@asynccontextmanager
async def mcp_session():
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_tool(name: str, **kwargs) -> dict:
    """Call a single-row tool (check_stock, get_ticket, make_payment, ...)
    and return its parsed JSON dict.
    """
    async with mcp_session() as session:
        result = await session.call_tool(name, kwargs)
        return json.loads(result.content[0].text)


async def call_list_tool(name: str, **kwargs) -> list[dict]:
    """Call a list_* tool (list_tickets, list_vendors, ...) and return its
    rows as a list of dicts.

    FastMCP (the mcp_server's v1 API) serializes a `list[dict]` return as
    one content block *per item*, not one block holding a JSON array — so
    this parses every block, unlike call_tool above which only reads the
    first. Robust to 0, 1, or many rows.
    """
    async with mcp_session() as session:
        result = await session.call_tool(name, kwargs)
        return [json.loads(block.text) for block in result.content]
