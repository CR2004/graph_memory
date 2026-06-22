"""MCP bridge that makes Parcle and the code graph available to Enter Code."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from enter_integration import (
    check_architectural_memory,
    get_architecture_graph,
    plan_architectural_change,
    sync_architectural_changes,
)


mcp = FastMCP(
    "Architectural Memory",
    instructions=(
        "In architectural mode, combine Parcle intent with a focused dependency "
        "neighborhood before generation. Then sync changed Python files."
    ),
)


mcp.tool()(check_architectural_memory)
mcp.tool()(plan_architectural_change)
mcp.tool()(sync_architectural_changes)
mcp.tool()(get_architecture_graph)


if __name__ == "__main__":
    mcp.run()
