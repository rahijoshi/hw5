"""Run the Campus Customs agent team against one or more tickets.

Usage:
    .venv/bin/python backend/run_tickets.py 101 102 103
    .venv/bin/python backend/run_tickets.py   # defaults to every open ticket
"""

from __future__ import annotations

import asyncio
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent_team import run_ticket  # noqa: E402  (needs the path insert above)

DB_PATH = Path(__file__).parent.parent / "data" / "campus_customs_new.db"


def _open_ticket_ids() -> list[int]:
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute("SELECT id FROM tickets WHERE status = 'open' ORDER BY id").fetchall()
    finally:
        conn.close()
    return [row[0] for row in rows]


async def main(ticket_ids: list[int]) -> None:
    for ticket_id in ticket_ids:
        print(f"\n=== Ticket {ticket_id} ===")
        report = await run_ticket(ticket_id)
        print(report)


if __name__ == "__main__":
    ids = [int(arg) for arg in sys.argv[1:]] or _open_ticket_ids()
    asyncio.run(main(ids))
