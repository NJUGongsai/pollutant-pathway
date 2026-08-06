"""P6 server integration — MCP stdio transport (usable without LLM).

Launches the actual MCP stdio server as a subprocess and drives it with the
official MCP client. Proves the 4 tools are exposed and callable end-to-end
over the JSON-RPC 2.0 stdio transport, and that typed errors are returned as
is_error results (no uncaught exception leak).
"""
from __future__ import annotations

import os
import sys

import pytest

pytest.importorskip("mcp")

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

DEMO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVER_PATH = os.path.join(DEMO, "reaction_agent", "mcp", "server.py")


def _params():
    env = dict(os.environ)
    env["PYTHONPATH"] = DEMO + ":" + env.get("PYTHONPATH", "")
    return StdioServerParameters(command=sys.executable, args=[SERVER_PATH], env=env)


class TestStdioServer:
    def test_list_tools_exposes_four(self):
        import asyncio

        async def run():
            async with stdio_client(_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    return [t.name for t in tools.tools]

        names = asyncio.run(run())
        assert len(names) == 4
        assert "reaction.predict_analogical_products_v1" in names
        assert "reaction.expand_evidence_v1" in names

    def test_predict_and_idempotent_repeat_over_transport(self):
        import asyncio
        import shutil
        import tempfile

        # The stdio server (server.py main()) persists runs/idem under
        # /tmp/reaction_agent_mcp across sessions. Clear it so the FIRST call
        # is a genuine create (reused=False), not a hit on stale state —
        # otherwise the G3 reused flag is non-deterministic over transport.
        shutil.rmtree(
            os.path.join(tempfile.gettempdir(), "reaction_agent_mcp"),
            ignore_errors=True,
        )

        async def run():
            async with stdio_client(_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    payload = {
                        "substrate_smiles": "CCO",
                        "idempotency_key": "it-p1",
                        "snapshot_id": "s1",
                    }
                    a = await session.call_tool("reaction.predict_analogical_products_v1", payload)
                    b = await session.call_tool("reaction.predict_analogical_products_v1", payload)
                    return a.content[0].text, b.content[0].text

        a, b = asyncio.run(run())
        import ast
        da, db = ast.literal_eval(a), ast.literal_eval(b)
        assert da["run_id"] == db["run_id"]  # idempotent reuse → same run
        assert da["reused"] is False and db["reused"] is True  # G3: reused flag

    def test_typed_error_no_uncaught_leak(self):
        import asyncio

        async def run():
            async with stdio_client(_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    res = await session.call_tool(
                        "reaction.predict_analogical_products_v1",
                        {
                            "substrate_smiles": "CCO",
                            "idempotency_key": "it-bad",
                            "snapshot_id": "s1",
                            "bogus": 1,
                        },
                    )
                    return res.is_error, res.content[0].text

        is_error, text = asyncio.run(run())
        assert is_error is True
        assert "SCHEMA_VALIDATION_ERROR" in text