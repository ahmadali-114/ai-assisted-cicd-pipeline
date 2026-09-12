"""Local stdio MCP server that exposes one least-privilege VM1 diagnostic tool."""

from mcp.server import MCPServer

from vm1_snapshot import get_vm1_snapshot

mcp = MCPServer("VM1 Operations Diagnostics")


@mcp.tool()
def get_vm1_diagnostic_snapshot() -> str:
    """Return a bounded, redacted, read-only health and log snapshot from VM1."""
    return get_vm1_snapshot()


if __name__ == "__main__":
    mcp.run()
