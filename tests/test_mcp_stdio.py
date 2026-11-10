from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "mcp" / "server.py"


async def _list_tools():
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
        cwd=str(ROOT),
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return {tool.name for tool in result.tools}


def test_mcp_server_starts_over_stdio_and_lists_tools():
    names = asyncio.run(_list_tools())

    assert "get_dashboard" in names
    assert "resolve_project" in names
    assert "query_sql" in names
    assert "execute_sql" in names
    assert "clean_all_orphaned_secrets" in names
    assert len(names) >= 29
