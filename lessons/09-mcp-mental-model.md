# Lesson 09 — The MCP mental model: tools vs resources, and the protocol underneath

**Time**: ~15 minutes
**Prerequisites**: Lesson 02 (the `tool_use` content block — `name`/`input`). Lesson 07 (structured tool results + the `isError` flag). Lesson 08 (`tool_choice`). You've spent Module B writing tools as Python dicts passed inline to `messages.create`. This lesson reframes all of that as **a protocol**.
**Goal**: Build the mental model for **MCP (Model Context Protocol)** before you write a server in L10. Three things to walk away with: (1) what problem MCP solves and the **client ↔ server** shape, (2) the **tools-vs-resources** distinction — the single highest-value new concept in this module, and (3) that **tools from every configured server are discovered at connection time** and pooled for the agent. No new Python deps; the "build" inspects the MCP servers **already attached to your live Claude Code session.**

## Why this matters for the exam

This opens **Domain 2 (Tool Design & MCP Integration, 18%)** — and MCP is the single most-mentioned topic in the whole guide. Two task statements live here that you'll meet directly:

- **Task 2.4 — Integrate MCP servers.** The guide explicitly tests:
  - **MCP resources as a mechanism for exposing content catalogs** (issue summaries, documentation hierarchies, database schemas) *"to reduce exploratory tool calls."*
  - **That tools from all configured MCP servers are discovered at connection time and available simultaneously to the agent.**
  - Tools = **actions**; resources = **content the agent can read**. (This is *the* distinction the exam draws.)
- **Task 2.1 — Tool interface design** and **Task 2.2 — structured errors** (your L07 `isError`) both turn out to be *MCP* concepts — they're written against MCP tools. So everything you already learned about tool shape and structured errors **was MCP all along**; you just hadn't met the protocol that standardises it.

What's **out of scope** (the guide says so explicitly, line ~1143): *deploying or hosting MCP servers — infrastructure, networking, container orchestration.* So this lesson — and this whole module — is about **designing and integrating** MCP, never about ops/hosting. Good news: that keeps it conceptual and cheap.

---

## Concept 1 — What problem does MCP solve?

In Module B you defined tools like this, inline, every time:

```python
TOOLS = [{"name": "get_customer", "description": "...", "input_schema": {...}}]
response = client.messages.create(..., tools=TOOLS)
```

That works, but notice what it *is*: **the tool's definition and its implementation live inside your one application.** If a teammate writes a different app — or you switch from the raw API to Claude Code — they can't reuse your `get_customer` tool. They'd re-implement it. Every app re-wires every integration from scratch. That's the **N×M problem**: N applications each separately integrating M data sources/tools.

**MCP is a standard protocol that decouples the two.** Instead of baking tools into each app, you put them behind a **server** that speaks MCP, and any MCP-aware **client** can connect and use them. Write `get_customer` once as an MCP server; Claude Code, your Python agent, and your teammate's app all consume it the same way.

> The exam's framing (line ~92): an application *"integrates with Model Context Protocol (MCP) servers."* The mental model: **MCP is to LLM tools what a USB port is to peripherals** — one standard socket, any compliant device plugs in.

### The client ↔ server shape

```
┌─────────────────┐         MCP          ┌──────────────────┐
│   MCP CLIENT     │  ◄───protocol───►    │   MCP SERVER     │
│  (the host app)  │                      │ (exposes tools/  │
│                  │                      │  resources)      │
│ • Claude Code    │   "what do you       │ • get_customer   │
│ • Your agent     │    offer?" (discover)│ • search_orders  │
│ • Claude Desktop │   "call get_customer"│ • db-schema      │
└─────────────────┘                       │   (a resource)   │
                                          └──────────────────┘
```

- The **client** is the host that *has the model in the loop* (Claude Code, your agent app). It connects to one or more servers.
- The **server** is a separate process that *exposes capabilities* — tools, resources, (and prompts). It has no model; it just answers "here's what I offer" and "here's the result of calling X."
- They talk over a **transport**. The two you'll see: **stdio** (the client launches the server as a subprocess and pipes JSON back and forth — local, default for things like `npx some-mcp-server`) and **HTTP** (the server is a remote URL). You don't need the wire details (JSON-RPC under the hood) for Foundations — *out of scope is the hosting; in scope is the shape.*

**A client connects to many servers at once.** That's the part the exam hammers (next concept).

---

## Concept 2 — Tools vs Resources (the distinction the exam draws)

An MCP server can expose three kinds of capability. Two matter for Foundations:

| Capability | What it is | Who initiates | Mental model | Exam phrase |
|---|---|---|---|---|
| **Tool** | An **action** the model can invoke — runs code, has effects, returns a result | **The model decides** to call it (your L08 `tool_choice` world) | a **verb** — `get_customer`, `create_issue`, `search_orders` | "tools for actions" |
| **Resource** | **Content the client can read** — a document, a catalog, a schema, exposed at a URI | **The application** reads it (often surfaced to the model as context) | a **noun** — `db://schema`, `docs://api/v2`, `issues://open` | "resources for content catalogs" |
| *(Prompt)* | A reusable prompt template the server offers | user/app picks it | a saved prompt | *(minor for Foundations)* |

The line to memorise, almost verbatim from the guide:

> **Tools are for *actions*. Resources are for *content catalogs* — and they exist to *reduce exploratory tool calls.*"**

### Why resources matter — the "reduce exploratory tool calls" point

Picture an agent that needs to query a database. Without resources, it gropes around: call `list_tables`, then `describe_table('customers')`, then `describe_table('orders')`… that's three *tool* round-trips burning context and latency, just to learn the **shape** of the data before it can do real work.

Expose the **schema as a resource** (`db://schema`) instead, and the client can hand that catalog to the model **up front** — no exploratory calls. The exam's examples of good resources are exactly these *"content catalogs"*:

- **issue summaries** (so the agent sees what issues exist without calling `list_issues`)
- **documentation hierarchies** (so it knows what docs exist before searching)
- **database schemas** (so it knows the tables before querying)

So the design heuristic the exam wants:

> If the agent needs to **read a body of content to orient itself** → expose it as a **resource**.
> If the agent needs to **take an action / fetch a specific computed answer** → expose it as a **tool**.

A resource is browse-able reference material; a tool is a function call. Get this wrong (everything-as-a-tool) and your agent wastes turns on exploratory discovery the exam specifically flags.

---

## Concept 3 — Discovery at connection time, tools pooled across servers

The third exam fact, stated plainly in the guide:

> *"Tools from all configured MCP servers are discovered at connection time and available simultaneously to the agent."*

Unpack that:

1. **You don't list tools by hand to the model.** When the client connects to a server, it asks the server *"what do you offer?"* and the server replies with its tool/resource list. That's **discovery** — automatic, at connection time.
2. **Multiple servers pool together.** Connect to a Gmail server, a Calendar server, and a database server, and the agent sees **one merged toolset** — Gmail's tools *and* Calendar's tools *and* the DB's tools, all at once. It doesn't know or care which server each came from.
3. **Consequence (forward-link to L11 and Task 2.1):** more connected servers → more tools in the pool → **harder tool selection.** The guide's "18 tools instead of 4-5 degrades selection" warning is the direct cost of over-pooling. This is *why* tool descriptions (L11) and tool distribution across subagents (Module D) matter — they're how you keep the discovered pool from becoming an undifferentiated mush.

You're about to **see this discovery live**, because your Claude Code session is itself an MCP client with servers attached.

---

## Build — inspect the MCP servers attached to your live session

No Python, no new deps. Claude Code (the app you're talking to me through) **is an MCP client.** It already has servers connected. We'll introspect them with the `claude mcp` CLI to make the three concepts concrete.

> **Note**: your servers will differ from mine — that's the point. You're looking at *your* client's *discovered* server list, not memorising mine.

### Step 1 — list the connected servers (the client's view)

```bash
claude mcp list
```

What I see on my machine (yours will differ):

```
Checking MCP server health…

claude.ai Gmail: https://gmailmcp.googleapis.com/mcp/v1 - ✔ Connected
claude.ai Google Calendar: https://calendarmcp.googleapis.com/mcp/v1 - ✔ Connected
claude.ai Google Drive: https://drivemcp.googleapis.com/mcp/v1 - ! Needs authentication
chrome-devtools: npx -y chrome-devtools-mcp@latest --isolated - ✔ Connected
```

**Read this against the concepts:**

- **Four servers, one client.** This *is* Concept 3 — the client connects to many servers, and their capabilities pool into one toolset the agent sees. (When I call a Gmail action and a browser action in the same task, I'm using two different servers transparently.)
- **Two transports are visible.** Gmail/Calendar/Drive are **`https://…` URLs** — remote HTTP servers. `chrome-devtools` is **`npx -y chrome-devtools-mcp@latest`** — a local **stdio** server the client launches as a subprocess. Same protocol, two transports (Concept 1).
- **`! Needs authentication`** on Drive — a server can be *configured* but not *usable* until you authenticate. Configured ≠ connected. (You'll meet this again in L12 with `.mcp.json` env-var credentials.)

### Step 2 — inspect one server (the protocol details)

```bash
claude mcp get chrome-devtools
```

What I see:

```
chrome-devtools:
  Scope: User config (available in all your projects)
  Status: ✔ Connected
  Type: stdio
  Command: npx
  Args: -y chrome-devtools-mcp@latest --isolated
  Environment:

To remove this server, run: claude mcp remove "chrome-devtools" -s user
```

Every line is a concept made concrete:

- **`Type: stdio`** + **`Command: npx … Args: …`** — the client starts this server *as a local subprocess* and pipes MCP over stdin/stdout. That's the stdio transport, named.
- **`Scope: User config (available in all your projects)`** — this is the **user-level** scope (`~/.claude.json`), the personal/experimental tier. The *other* tier is **project-level `.mcp.json`** for shared team servers. **That project-vs-user scope split is Task 2.4 and the whole subject of L12** — note it here, master it there.
- **`Environment:`** — where credentials/config get injected (empty here). L12 is where `${GITHUB_TOKEN}`-style env-var expansion lands.

### Step 3 — connect tool names you've already used back to their servers

You've watched me, in this very session, have tools available like `mcp__chrome-devtools__take_screenshot` and `mcp__claude_ai_Gmail__search_threads`. Look at the naming: `mcp__<server>__<tool>`. That prefix **is the discovery-and-pooling from Concept 3** made visible — the client namespaces each discovered tool by the server it came from, then offers the whole pool to the model under one flat list. The model picks `mcp__chrome-devtools__take_screenshot` without knowing or caring that a `chrome-devtools` subprocess is what fulfils it.

> If `claude mcp list` shows **no servers** on your machine, that's fine — it just means none are configured yet. You'll add one in L12. The concepts still hold; you'll create your own server to inspect in **L10**.

---

## The throughline — what Module B was, restated as MCP

Here's the reframe that makes the rest of the module click. Everything you built in Module B has an MCP name:

| Module B (inline, raw API) | MCP equivalent (this module) |
|---|---|
| `{"name": ..., "input_schema": ...}` dict in `tools=` | a **tool** exposed by an MCP **server** |
| The `tool_use` → `tool_result` dance (L02) | the **client** calling a server's tool and getting its result |
| `is_error` flag + structured payload (L07) | the MCP **`isError`** flag (Task 2.2 — *literally the same concept*) |
| `tool_choice` over the inline toolset (L08) | `tool_choice` over the **discovered, pooled** toolset |
| *(no equivalent — new)* | **resources**: read-only content catalogs to cut exploratory calls |

You didn't learn tools and *then* MCP. **You learned MCP's tool half inline, and now you're meeting the protocol that standardises it** — plus the genuinely new piece, **resources.**

---

## Exercises (do these before moving on)

Most are conceptual — this is a mental-model lesson. Answer in a sentence or two each.

1. **Run the build on your own machine.** `claude mcp list`, then `claude mcp get <one-server>` (pick any server it lists; if none, say so). Tell me: how many servers, and for one of them — what **transport** (stdio vs http) and what **scope** (user vs project)?

2. **Tool or resource?** For each, decide and give the one-line reason:
   - (a) `create_github_issue(title, body)`
   - (b) a list of all open issues with their titles and IDs, so the agent knows what exists
   - (c) `send_email(to, subject, body)`
   - (d) the database table schema the agent needs before it can write a query
   - (e) `run_sql(query)`

3. **The exploratory-calls problem.** An agent connected to a database MCP server makes these calls in order: `list_tables()`, `describe_table('users')`, `describe_table('orders')`, *then* `run_sql(...)`. Which **one** of those four should arguably have been a **resource** instead of a tool, and what does the guide say that buys you?

4. **Discovery & the cost of pooling.** A teammate connects 6 MCP servers, each exposing ~3 tools, to their agent. (a) How many tools does the agent "see," and how did they get there — did the teammate list them to the model by hand? (b) Name one reliability risk of that pooled toolset, and which *later* lesson addresses it.

5. **Spot the out-of-scope.** One of these is something the Foundations exam **explicitly does not test**. Which, and how do you know? — *(i)* choosing a resource vs a tool; *(ii)* setting up a Kubernetes deployment to host your MCP server; *(iii)* the project-vs-user scope of a configured server.

---

## What you now know

- **MCP is a standard protocol** that decouples tool/resource *definitions* from the *apps* that use them — solving the N×M re-integration problem. One server, many clients (Claude Code, your agent, Claude Desktop).
- **Client ↔ server shape**: the client hosts the model and connects to one or more servers; servers expose capabilities and run no model. They talk over a **transport** (stdio = local subprocess; http = remote URL). Hosting/deployment is **out of scope**.
- **Tools vs resources** — the key distinction: **tools are actions the model invokes** (verbs); **resources are read-only content catalogs the app exposes** (nouns) to **reduce exploratory tool calls**. Schemas, issue lists, doc hierarchies → resources.
- **Discovery at connection time**: tools from *all* configured servers are discovered automatically and **pooled** into one toolset the agent sees simultaneously — which is also why over-pooling degrades tool selection (the L11/Module-D problem).
- **Module B was MCP's tool half inline.** `isError` (L07), the tool_use/tool_result dance (L02), `tool_choice` (L08) are all MCP concepts; resources are the new piece.

## Up next

**Lesson 10 — Build your first MCP server (FastMCP).** You stop *consuming* MCP and start *producing* it: a real Python server, written with `FastMCP`, exposing a tool **and** a resource — so the tools-vs-resources distinction from this lesson becomes something you author, run, and inspect (this is where we'll `uv add` the `mcp` package). Then L11 makes its tool descriptions exam-grade (ACI), and L12 wires it into `.mcp.json` with project-vs-user scope and env-var credentials — the two config tiers you just saw in `claude mcp get`.

When you've worked through this lesson and the exercises, tick the box in `lessons/README.md` and tell me you're done — I'll write 10.
