"""Call the local MCP server and print a short proof that its tool responded."""

from __future__ import annotations

import asyncio

from mcp import Client

MCP_URL = "http://127.0.0.1:8001/mcp"


async def main() -> None:
    async with Client(MCP_URL) as client:
        result = await client.call_tool("get_vm1_diagnostic_snapshot", {})

    text_parts = [item.text for item in result.content if hasattr(item, "text")]
    snapshot = "\n".join(text_parts)
    if not snapshot:
        raise RuntimeError("MCP tool returned no text content")

    print("MCP tool call: SUCCESS")
    print(f"Snapshot length: {len(snapshot)} characters")
    print("Snapshot preview:")
    print(snapshot[:500])


if __name__ == "__main__":
    asyncio.run(main())
