"""Launch support_server.py as a subprocess and speak MCP to it over stdio.

This is the CLIENT half from L09's diagram. It does exactly what Claude
Code does when it connects to a configured server: launch -> initialize
-> DISCOVER tools/resources -> call them. No model, no API spend.
"""

import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    # How the client launches the server subprocess (the stdio transport).
    # This is the in-code version of an .mcp.json "command"/"args" entry (L12).
    params = StdioServerParameters(
        command="uv",
        args=["run", "python", "lessons/scripts/support_server.py"],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()  # the MCP handshake

            # --- DISCOVERY (L09 Concept 3, made visible) ---
            tools = await session.list_tools()
            print("DISCOVERED TOOLS:    ", [t.name for t in tools.tools])
            resources = await session.list_resources()
            print("DISCOVERED RESOURCES:", [str(r.uri) for r in resources.resources])

            # --- CALL THE TOOL (an action) ---
            result = await session.call_tool("lookup_plan", {"plan_name": "Pro"})
            print("\nTOOL CALL lookup_plan('Pro') ->")
            print(result.content[0].text)

            # --- CALL THE TOOL (an action) ---
            result = await session.call_tool("cheapest_plan")
            print("\nTOOL CALL cheapest_plan ->")
            print(result.content[0].text)

            # --- READ THE RESOURCE (content, no args) ---
            catalog = await session.read_resource("catalog://plans")
            print("\nRESOURCE READ catalog://plans ->")
            print(catalog.contents[0].text)


if __name__ == "__main__":
    asyncio.run(main())
