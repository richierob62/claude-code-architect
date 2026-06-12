# Lesson 10 — Build your first MCP server (FastMCP)

**Time**: ~15 minutes
**Prerequisites**: Lesson 09 (the MCP mental model — client ↔ server, **tools vs resources**, discovery at connection time). This lesson turns every concept from L09 into code you write, run, and watch a real MCP client talk to.
**Goal**: Write a tiny MCP **server** in Python with `FastMCP` that exposes **one tool** (`lookup_plan` — an action) **and one resource** (`catalog://plans` — a content catalog). Then drive it with a real MCP **client** over **stdio** and watch discovery + calls happen on the wire. This is where you stop *consuming* MCP and start *producing* it — and where the L09 tools-vs-resources line becomes something you author.

## Why this matters for the exam

L09 gave you the vocabulary; this lesson makes it muscle memory. The Foundations guide tests that you can tell a **tool** (action/verb) from a **resource** (content catalog/noun) and know *why* you'd reach for each (Task 2.4: *"resources for content catalogs … to reduce exploratory tool calls"*; *"tools for actions"*). You don't get exam questions asking you to write FastMCP syntax — but building one server cements the distinction far better than re-reading it, and it makes L11 (writing exam-grade tool descriptions) and L12 (`.mcp.json` config) concrete instead of abstract.

**Still out of scope** (guide line ~1143): deploying/hosting the server — networking, containers, orchestration. We run it locally as a subprocess (stdio), exactly the in-scope shape. Nothing here touches ops.

---

## Step 0 — the dependency (already done for you, but know what it is)

The package is **`mcp`** — Anthropic's official Python SDK for the Model Context Protocol. It ships **`FastMCP`**, a decorator-based high-level API (think Flask/FastAPI, but for MCP servers). It's already installed in this project:

```bash
uv add mcp        # ← this was run when L10 was written; you don't need to repeat it
uv run python -c "import importlib.metadata as m; print(m.version('mcp'))"   # confirm: 1.27.x or later
```

> The `mcp` package has **no** `mcp.__version__` attribute (`import mcp; print(mcp.__version__)` raises `AttributeError`). Read the installed version from distribution metadata instead — `importlib.metadata.version('mcp')`, or `uv pip show mcp`.

> `FastMCP` is the *high-level* server API in the `mcp` package. (There's also a separate standalone project confusingly also called "FastMCP"; we use the one bundled in the official `mcp` SDK — `from mcp.server.fastmcp import FastMCP`. Same idea, and it's what `uv add mcp` gives you.)

---

## Concept — what a FastMCP server *is*

A FastMCP server is a normal Python process with three moving parts:

1. **An app object**: `mcp = FastMCP("name")`. The name is how the client labels the server.
2. **Decorated functions** that become MCP capabilities:
   - `@mcp.tool()` turns a function into a **tool** (an action the model can call). Its **docstring becomes the tool description** the model reads (this is your L11 lever — keep it in mind), and its **type hints become the input schema** automatically.
   - `@mcp.resource("some://uri")` turns a function into a **resource** (read-only content the client fetches by URI). No arguments from the model — the client just *reads* it.
3. **`mcp.run()`** at the bottom — starts the server and speaks MCP over a transport. **Default transport is `stdio`**: the server reads MCP messages on stdin and writes replies on stdout, so a client can launch it as a subprocess (exactly the `npx … chrome-devtools-mcp` shape you saw in L09's `claude mcp list`).

That's the whole model: decorate functions, call `run()`. FastMCP handles the JSON-RPC wire format, the discovery handshake, schema generation from type hints — all the protocol plumbing L09 said you don't need to hand-write.

---

## Build, part 1 — write the server

Create **`lessons/scripts/support_server.py`**:

```python
"""A tiny MCP server: one tool (action) + one resource (content catalog).

Run directly (`uv run python lessons/scripts/support_server.py`) and it
waits on stdin for MCP messages — that's a server speaking stdio, not a
hang. A client (part 2) is what drives it.
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("support-desk")

# Pretend this is a backend. In a real server the catalog would be built
# from a live DB/API; here it's a hand-written dict so the lesson is cheap.
PLANS = {
    "free":     {"price": 0,  "seats": 1,  "support": "community"},
    "pro":      {"price": 20, "seats": 5,  "support": "email"},
    "business": {"price": 60, "seats": 25, "support": "priority"},
}


@mcp.tool()
def lookup_plan(plan_name: str) -> dict:
    """Look up the price, seat limit, and support tier for ONE plan by name.

    Use this when the customer names a specific plan. Returns a dict with
    price (USD/month), seats, and support tier. Unknown name -> an error
    payload listing the known plans.
    """
    plan = PLANS.get(plan_name.lower())
    if plan is None:
        return {"error": f"unknown plan: {plan_name}", "known": list(PLANS)}
    return {"plan": plan_name.lower(), **plan}


@mcp.resource("catalog://plans")
def plan_catalog() -> str:
    """The full catalog of available plans, so an agent knows what exists
    up front WITHOUT calling lookup_plan once per guess."""
    lines = ["Available plans (name: $price/mo, seats, support):"]
    for name, p in PLANS.items():
        lines.append(f"- {name}: ${p['price']}/mo, {p['seats']} seats, {p['support']} support")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()  # defaults to stdio transport
```

Read it against L09 before running anything:

- **`lookup_plan` is a tool** — a **verb**, an action. The *model* decides to call it, passing a `plan_name`. This is the L08 `tool_use` world, now living behind a server.
- **`catalog://plans` is a resource** — a **noun**, content. Nobody "calls" it with arguments; the client *reads* it by URI and can hand the whole catalog to the model **up front**. That's the L09 *"reduce exploratory tool calls"* payoff in code: instead of the agent calling `lookup_plan("free")`, `lookup_plan("pro")`, `lookup_plan("business")` just to discover what exists, it reads `catalog://plans` once.
- **The docstrings are not decoration.** `lookup_plan`'s docstring is the description the model uses to decide when to call it. (L11 is entirely about making that text exam-grade.)
- **The type hints `plan_name: str` are the schema.** FastMCP generates the `input_schema` (the same `{"type": "object", "properties": {...}}` shape you wrote by hand in Module B) from them. You stopped hand-writing JSON schemas.

### Run it on its own (and understand why it "hangs")

```bash
uv run python lessons/scripts/support_server.py
```

Nothing prints, and it doesn't exit. **That's correct** — a stdio server is now sitting on stdin waiting for a client to send it MCP messages. There's no model and no client here, so there's nothing to answer. Press **Ctrl-C** to stop it. (A server with no client attached looks exactly like a hang; that's the nature of stdio.)

---

## Build, part 2 — drive it with a real MCP client

A server is only meaningful when a client talks to it. The `mcp` SDK ships a client too, so we can do the full handshake **in one script, no model, no API cost** — and watch discovery happen.

Create **`lessons/scripts/support_client.py`**:

```python
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

            # --- READ THE RESOURCE (content, no args) ---
            catalog = await session.read_resource("catalog://plans")
            print("\nRESOURCE READ catalog://plans ->")
            print(catalog.contents[0].text)


if __name__ == "__main__":
    asyncio.run(main())
```

Run the **client** (it launches the server itself — you do *not* run the server separately this time):

```bash
uv run python lessons/scripts/support_client.py
```

### Expected output (verbatim from a real run)

```
Processing request of type ListToolsRequest
Processing request of type ListResourcesRequest
Processing request of type CallToolRequest
Processing request of type ReadResourceRequest
DISCOVERED TOOLS:     ['lookup_plan']
DISCOVERED RESOURCES: ['catalog://plans']

TOOL CALL lookup_plan('Pro') ->
{
  "plan": "pro",
  "price": 20,
  "seats": 5,
  "support": "email"
}

RESOURCE READ catalog://plans ->
Available plans (name: $price/mo, seats, support):
- free: $0/mo, 1 seats, community support
- pro: $20/mo, 5 seats, email support
- business: $60/mo, 25 seats, priority support
```

> The four `Processing request of type …Request` lines are **the server logging each MCP message it receives** — they print on stderr, interleaved before the client's stdout. They are the protocol made literal: `ListTools` and `ListResources` are **discovery**; `CallTool` and `ReadResource` are the two ways a client uses a server. You're watching the L09 client↔server conversation happen line by line.

Trace it against L09:

1. `stdio_client(params)` **launches the server as a subprocess** — the stdio transport, the same mechanism behind `npx … chrome-devtools-mcp`.
2. `session.initialize()` is the **handshake**.
3. `list_tools()` / `list_resources()` are **discovery at connection time** — the client asks "what do you offer?" and the server answers. You never told the client the tool's name or schema; it *discovered* them.
4. `call_tool(...)` invokes the **action**; `read_resource(...)` fetches the **content** by URI — no arguments, because a resource is a noun you read, not a verb you call.

You just built and exercised both halves of the L09 diagram.

---

## The tool-vs-resource decision, now that you've built both

You now have a working example of each, so the heuristic from L09 has teeth:

- `lookup_plan("pro")` answers **one specific question** the model formed → **tool**. It takes an argument, runs logic, returns a computed answer.
- `catalog://plans` is the **whole body of reference content** the model reads to *orient itself* before it even knows which plan to ask about → **resource**. No argument; the client can inject it up front so the model never has to guess-and-call.

If you'd modelled the catalog as a tool (`list_all_plans()`), it would *work* — but it forces a tool round-trip into the loop just to learn what exists, which is precisely the *exploratory call* the exam says resources exist to eliminate. **Reference content the agent reads to orient → resource. A specific computed answer or effect → tool.**

---

## Exercises (do these before moving on)

1. **Run both scripts.** Confirm the server "hangs" on its own (and why), then run the client and confirm your output matches. Tell me: in the client's output, which two of the four `…Request` log lines are *discovery* and which two are *usage*?

2. **Break the schema deliberately.** In `lookup_plan`, change the signature to `def lookup_plan(plan_name):` (drop the `: str` type hint) and re-run the client. Does it still work? What do you predict happens to the **input schema** FastMCP generates without the hint — and why does that connect to L11 (tool description craft)? (Put the hint back after.)

3. **Add a second tool.** Add `@mcp.tool() def cheapest_paid_plan() -> dict:` that returns the lowest-priced plan with `price > 0`. Re-run the client — does it appear in `DISCOVERED TOOLS` without you registering it anywhere by hand? Which L09 concept does that demonstrate?

4. **Tool or resource — and now justify with mechanics.** You're adding "the current ticket queue (list of open ticket IDs + subjects) so the agent knows what's waiting." Tool or resource? Give the answer *and* say which client method (`call_tool` vs `read_resource`) the agent path would use, and whether the model passes any arguments.

5. **Connect it back.** In one sentence each: (a) where did the `input_schema` you used to hand-write in Module B come from in this server? (b) where does the tool *description* the model reads come from? (c) which transport did `mcp.run()` use by default, and how do you know from the client code?

---

## What you now know

- **A FastMCP server is decorated functions + `mcp.run()`.** `@mcp.tool()` exposes an **action** (docstring → description, type hints → input schema); `@mcp.resource("uri://…")` exposes **read-only content** fetched by URI with no model-supplied arguments.
- **You stopped hand-writing tool plumbing.** The `input_schema` you wrote by hand in Module B is now generated from type hints; the JSON-RPC wire format and discovery handshake are handled by the SDK.
- **The client↔server loop is real and observable**: `initialize` → `list_tools`/`list_resources` (**discovery at connection time**) → `call_tool` (action) / `read_resource` (content). The `…Request` log lines are the protocol on the wire.
- **stdio is the default transport** — the client launches the server as a subprocess and pipes MCP over stdin/stdout, the same shape as the `npx`-launched servers in L09's `claude mcp list`.
- **The tool-vs-resource line is now mechanical, not just verbal**: a tool takes args and computes an answer; a resource is reference content the client reads to orient the model up front — eliminating exploratory tool calls.

## Up next

**Lesson 11 — Agent-Computer Interface (ACI): tool description craft, format choice, poka-yoke.** You have a working tool with a docstring — L11 makes that docstring *exam-grade*: how to describe a tool so the model reaches for it over a built-in (the guide's "prefer your MCP tool over Grep" point), how output **format** is a design choice (callback to your own Lesson-03 Ada's-team experiment — thin tool → more chains, fat tool → bigger context), and poka-yoke (designing tools that are hard to misuse). Then L12 wires this exact server into `.mcp.json` with project-vs-user scope and env-var credentials — the two config tiers you saw in L09's `claude mcp get`.

When you've worked through this lesson and the exercises, tick the box in `lessons/README.md` and tell me you're done — I'll write 11.
