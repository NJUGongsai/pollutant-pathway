"""P6 MCP Service — stdio server (mcp SDK 2.x).

Exposes the 4 tools over the MCP stdio transport (JSON-RPC 2.0). The server
is stateless per-call: it validates every request against the strict schema,
resolves idempotency, and maps typed P6Error to JSON-RPC error responses so
no uncaught exception leaks to the client.

The kernel is usable without an LLM: the server can be driven by any MCP
client (or a plain JSON-RPC stdio probe) without any model in the loop.
"""
from __future__ import annotations

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as t

from reaction_agent.mcp.errors import P6Error
from reaction_agent.mcp.schemas import GOLDEN_SCHEMAS
from reaction_agent.mcp.tools import ALL_TOOLS, ReactionMCPKernel

SERVER_NAME = "reaction-agent-mcp"
SERVER_VERSION = "p6-1"


def _mcp_tool_from_schema(tool_name: str) -> t.Tool:
    golden = GOLDEN_SCHEMAS[tool_name]
    return t.Tool(
        name=tool_name,
        description=_tool_description(tool_name),
        inputSchema=golden["input_schema"],
    )


def _tool_description(tool_name: str) -> str:
    side = GOLDEN_SCHEMAS[tool_name]["side_effect"]
    return (
        f"{tool_name}. Side effect: {side}. network=False. "
        "Strict JSON schema; unknown fields and bad types are rejected. "
        "Mutation tools require idempotency_key."
    )


def build_server(kernel: ReactionMCPKernel) -> Server:
    server = Server(SERVER_NAME, version=SERVER_VERSION)

    async def _list_tools(ctx, params: t.ListToolsRequest) -> t.ListToolsResult:
        return t.ListToolsResult(tools=[_mcp_tool_from_schema(name) for name in ALL_TOOLS])

    async def _call_tool(ctx, params: t.CallToolRequestParams) -> t.CallToolResult:
        name = params.name
        arguments = params.arguments or {}
        try:
            result = kernel.handle(name, arguments)
        except P6Error as exc:
            return t.CallToolResult(
                content=[t.TextContent(type="text", text=f"{exc.code}: {exc.message}")],
                is_error=True,
            )
        return t.CallToolResult(
            content=[t.TextContent(type="text", text=str(result))],
            is_error=False,
        )

    server.add_request_handler("tools/list", t.ListToolsRequest, _list_tools)
    server.add_request_handler("tools/call", t.CallToolRequestParams, _call_tool)

    return server


async def run_stdio(kernel: ReactionMCPKernel) -> None:
    """Run the MCP stdio server loop for ``kernel``."""
    server = build_server(kernel)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Entrypoint: build a default kernel and serve over stdio."""
    import tempfile
    from pathlib import Path

    from reaction_agent.mcp.idempotency import IdempotencyStore
    from reaction_agent.mcp.runs import RunStore

    base = Path(tempfile.gettempdir()) / "reaction_agent_mcp"
    kernel = ReactionMCPKernel(
        run_store=RunStore(base / "runs"),
        idem_store=IdempotencyStore(base / "idem"),
    )
    anyio.run(run_stdio, kernel)


if __name__ == "__main__":
    main()