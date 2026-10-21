"""Check the MCP handshake and tool listing, without invoking a model or mutation."""
import asyncio
import sys

from fastmcp import Client


async def check(url):
    async with Client(url) as client:
        if not await client.list_tools():
            raise RuntimeError("MCP server returned no tools")


if __name__ == "__main__":
    asyncio.run(check(sys.argv[1]))
