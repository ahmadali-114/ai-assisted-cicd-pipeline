"""Local MCP server that exposes one least-privilege VM1 diagnostic tool."""

import argparse

from mcp.server import MCPServer

from vm1_snapshot import get_vm1_snapshot

mcp = MCPServer("VM1 Operations Diagnostics")


@mcp.tool()
def get_vm1_diagnostic_snapshot() -> str:
    """Return a bounded, redacted, read-only health and log snapshot from VM1."""
    return get_vm1_snapshot()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--http",
        action="store_true",
        help="serve Streamable HTTP on localhost:8001 instead of the stdio transport",
    )
    arguments = parser.parse_args()
    if arguments.http:
        mcp.run(
            transport="streamable-http",
            host="127.0.0.1",
            port=8001,
            streamable_http_path="/mcp",
            json_response=True,
            stateless_http=True,
        )
    else:
        mcp.run()
