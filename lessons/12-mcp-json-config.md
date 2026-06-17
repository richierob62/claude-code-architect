# Lesson 12 — Wiring your server into Claude Code: `.mcp.json`, scope, and env-var credentials

**Time**: ~15 minutes
**Prerequisites**: Lesson 10 (you built `support_server.py` — a FastMCP server speaking stdio) and Lesson 11 (you made its tool descriptions exam-grade). This lesson takes that server out of the in-process client harness and makes it **live inside Claude Code**.
**Goal**: Know the three configuration **scopes** that register an MCP server with Claude Code, where each one physically lives, how they take **precedence**, and how `${ENV_VAR}` expansion lets a committed config reference a secret without committing the secret. By the end you'll have your L10 server answering questions inside a real Claude Code session.

## Why this matters for the exam

This is **Domain 2, Task 2.4** ("Integrate MCP servers into Claude Code and agent workflows"). D2 is **18%** of the exam, and this task is the one that turns everything you built in L09–L11 into something an agent actually runs. The guide tests four facts plus a set of configuration skills:

> *"MCP server scoping: project-level (`.mcp.json`) for shared team tooling vs user-level (`~/.claude.json`) for personal/experimental servers."*
> *"Environment variable expansion in `.mcp.json` (e.g., `${GITHUB_TOKEN}`) for credential management without committing secrets."*
> *"Tools from all configured MCP servers are discovered at connection time and available simultaneously to the agent."*

You already half-discovered the scope question back in L09 ("is `.mcp.json` per-repo or global?"). This lesson is the full answer.

---

## Concept 1 — Three scopes, three files, one precedence order

Claude Code reads MCP server definitions from **three** places. They are not three copies of the same thing — they answer three different questions ("who should get this server?"), and they live in different files with different commit semantics.

| Scope | Flag | Where it's stored | Committed? | Who gets the server |
|---|---|---|---|---|
| **local** (default) | `-s local` | `~/.claude.json`, **keyed to this project's path** | No (it's in your home dir) | Just you, just in this one project |
| **project** | `-s project` | `.mcp.json` at the **repo root** | **Yes — you commit it** | Everyone who clones the repo |
| **user** | `-s user` | `~/.claude.json`, **not** project-keyed | No | You, across **all** your projects |

The two distinctions that trip people up:

- **`.mcp.json` is ALWAYS the project scope, and it is the *only* scope that is a committed, repo-root file.** There is no global `.mcp.json`. The "global-ish" tiers (local and user) both live inside `~/.claude.json` in your home directory — local is keyed to a project path, user is not. (This is the precise version of the answer you got in L09.)
- **local vs user** both sit in `~/.claude.json` and are both uncommitted — the difference is *project-keyed* (local: this repo only) vs *global to you* (user: every repo you open).

**Mental model:** *project* = "the team needs this tool to work on this repo" (commit it). *user* = "I personally want this everywhere" (my Sentry, my personal scratch server). *local* = "I'm experimenting in this one repo and don't want to commit anything yet."

### Precedence

When the same server **name** is defined in more than one scope, the more specific scope wins:

> **local  >  project  >  user**

So a `local`-scope `support-desk` overrides a `project`-scope `support-desk` of the same name — which is exactly what you want when you're locally testing a patched version of a server the whole team shares. Servers with *different* names from all scopes are simply **unioned together** — you get all of them at once (that's Concept 3).

> The exam phrases the project-vs-user split as *"`.mcp.json` for shared team tooling vs `~/.claude.json` for personal/experimental servers."* If you remember nothing else: **committed repo file = project = team; home-dir file = local/user = you.**

---

## Concept 2 — `${ENV_VAR}` expansion: commit the config, not the secret

A `project`-scope `.mcp.json` is committed to the repo. That creates an obvious problem: most real servers need a credential (a GitHub token, a Jira API key, a database URL), and you must **never** commit a secret. The resolution is **environment-variable expansion**: the committed file holds a *reference*, and Claude Code substitutes the value from the environment at launch time.

```jsonc
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

What gets committed is the literal string `${GITHUB_TOKEN}`. The real token lives in your shell environment (or `.env`, or your secrets manager) and never enters git. Each teammate supplies their **own** token from their **own** environment, and the same committed config works for everyone.

Two expansion forms the exam expects you to recognise:

- `${VAR}` — expand `VAR`; error/empty if unset.
- `${VAR:-default}` — expand `VAR`, or fall back to `default` if `VAR` is unset (handy for an optional host/port).

Expansion is valid in the `command`, `args`, `env`, and (for HTTP servers) `headers`/`url` fields — i.e. anywhere a value would otherwise be a hardcoded string.

> This is the *"credential management without committing secrets"* knowledge item, verbatim. The pairing is the whole point: **project scope makes the config shared; `${ENV_VAR}` keeps the secret personal.**

---

## Concept 3 — All servers' tools are discovered at connection time, simultaneously

When Claude Code starts a session, it connects to **every** configured server (across all three scopes), runs the `list_tools`/`list_resources` discovery handshake you saw on the wire in L10, and pools **all** the resulting tools into one flat set the agent can choose from — alongside the built-ins (`Read`, `Grep`, `Edit`, …).

Consequences worth internalising:

- **There is no per-request tool loading.** The agent doesn't "go fetch the GitHub tools when it needs GitHub." Everything is present from turn one. (This is why L11's *descriptions* matter so much: with 40 tools pooled from 5 servers plus built-ins, the description text is the only thing routing the model to the right one.)
- **Name collisions across servers are disambiguated by server.** Two servers each exposing a `search` tool don't clash; Claude Code namespaces them so the agent sees both.
- **More servers = bigger tool surface = more context spent on tool definitions and more routing ambiguity.** This is the cost side of "everything available at once," and it's why the guide pairs this task with the L11 advice to write differentiating descriptions and to *prefer existing community servers over custom ones* (fewer bespoke tools to describe and maintain).
- **Resources are pooled too** — your `catalog://plans` resource from L10 is exactly the *"content catalog to reduce exploratory tool calls"* the guide calls out: the agent can read what plans exist up front instead of guessing names through `lookup_plan`.

---

## Build — wire `support_server.py` into Claude Code (project scope)

You'll register your L10 server as a **project-scoped** server, confirm it connects, and see its tools pooled into a live session. No API spend beyond a single trivial query (and you can skip even that — the `claude mcp` inspection commands cost nothing).

### Step 0 — confirm your server still runs standalone

```bash
uv run python lessons/scripts/support_server.py
```

It should *hang* (waiting on stdin) — that's the stdio server from L10, not a crash. Kill it with `Ctrl-C`. If it errors instead, fix that before wiring it in; a server that can't start standalone can't start under Claude Code either.

### Step 1 — add it at project scope via the CLI

From the repo root:

```bash
claude mcp add support-desk \
  --scope project \
  -- uv run python lessons/scripts/support_server.py
```

Everything after `--` is the command Claude Code will launch to start the server (stdio is the default transport, so no `--transport` needed). The `--scope project` flag is what makes this write to a committed `.mcp.json` rather than your home-dir `~/.claude.json`.

### Step 2 — read the file it wrote

```bash
cat .mcp.json
```

You should see roughly (the CLI fills in `"type": "stdio"` and an empty `"env": {}` for you):

```json
{
  "mcpServers": {
    "support-desk": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "lessons/scripts/support_server.py"],
      "env": {}
    }
  }
}
```

This is the committed, team-shared artifact. Note what is **not** here: no secret, no absolute home-dir path. (If your server needed a token, that empty `"env": {}` is where `"SUPPORT_TOKEN": "${SUPPORT_TOKEN}"` would go — see Exercise 3.)

### Step 3 — confirm it connects and discovers tools

```bash
claude mcp list
```

On a **freshly added project-scoped** server you'll likely see `⏸ Pending approval (run \`claude\` to approve)` rather than an immediate ✓. That is deliberate: because `.mcp.json` is committed and may have arrived from a teammate (or a repo you cloned), Claude Code does **not** auto-trust project-scoped servers — it asks you to approve them on first use. Start `claude` in the repo, approve `support-desk` when prompted, and it flips to ✓ connected. (local- and user-scope servers you added yourself don't need this — you authored them.)

To inspect the **configuration** (scope, transport, launch command, liveness):

```bash
claude mcp get support-desk
```

```
support-desk:
  Scope: Project config (shared via .mcp.json)
  Status: ✔ Connected
  Type: stdio
  Command: uv
  Args: run python lessons/scripts/support_server.py
  Environment:
```

Read this carefully, because it's a common trap: **`claude mcp get` is a static config inspector, not a discovery dump.** It reports what's in `.mcp.json` plus a liveness check (`✔ Connected`). It does **not** run `list_tools`/`list_resources` and print `lookup_plan`, `cheapest_plan`, or `catalog://plans`. Seeing no tools here is the *correct, expected* output — it does not mean discovery failed.

So where *does* the discovery surface? **In the running session's tool registry.** When Claude Code connects to the server, it runs the same `list_tools`/`list_resources` handshake you drove by hand in L10, then namespaces each result as `mcp__<server>__<tool>`. Inside a live session you'll find:

```
mcp__support-desk__lookup_plan
mcp__support-desk__cheapest_plan
```

registered as callable tools — and `catalog://plans` reachable via the `ListMcpResourcesTool` / `ReadMcpResourceTool` pair (resources aren't callable tools, so they don't appear in the tool list; they're read through that pair). *That* is Concept 3 happening for real: discovery at connection time, pooled into the agent's tool set — just surfaced in the session registry, not in `claude mcp get`.

> **The distinction the exam (and this lesson) cares about:** *config inspection* (`claude mcp get` → scope/transport/status) vs *runtime discovery* (the `mcp__server__tool` entries the client registers on connect). They're different stages. `get` tells you the server is wired up and alive; the namespaced tools in the session prove its surface was discovered and pooled.

### Step 4 — use it in a session (optional, ~1 trivial query)

Start Claude Code in this repo and ask:

> "Using the support-desk tools, what's the cheapest paid plan?"

The agent should route to your `cheapest_plan` tool (this is L11's description work paying off — the tool's docstring is what wins it the call) and answer `pro`. That round-trip — your code, your description, the model's routing, a real answer — is the whole arc of Module C closing.

### Step 5 — see the precedence rule with your own eyes (no API spend)

Add the *same name* at local scope, then list:

```bash
claude mcp add support-desk --scope local -- uv run python lessons/scripts/support_server.py
claude mcp get support-desk
```

`get` will report `Scope: Local config (private to you in this project)` — the `local` definition shadows the `project` one for *you* (precedence: local > project > user), while the committed `.mcp.json` is unchanged for everyone else. Remove it again to leave a clean tree:

```bash
claude mcp remove support-desk --scope local
```

> **Verification note (do this before trusting the lesson):** the flags above are from the live `claude mcp add --help` on the version in this repo's session (`claude 2.1.177`): `--scope <local|user|project>` default `local`, `-e KEY=value` for env, stdio default, command after `--`. If your `claude --version` differs and a flag has moved, run `claude mcp add --help` and adjust — don't guess.

---

## Exercises (do these before moving on)

1. **Scope routing.** For each, name the scope (local / project / user) and the file it lands in: (a) a Jira server your whole team needs to triage issues in this repo; (b) your personal Sentry server you want in *every* project; (c) a half-broken server you're patching and don't want to commit yet. State the commit semantics of each.

2. **Precedence.** A repo's committed `.mcp.json` defines `db-tools`. You add a `db-tools` at **local** scope pointing at a patched build. Which one does *your* session use, which one do your teammates get, and why is this the exact behaviour you'd want while debugging?

3. **Credentials without committing.** Your `support-desk` server is rewritten to require a `SUPPORT_API_KEY`. Write the `.mcp.json` `mcpServers` entry (project scope) that references the key via expansion, and say where the *actual* key value should live so it never enters git. Then: what does Claude Code substitute, and *when*?

4. **Why descriptions, restated (L11 callback).** You now have `support-desk`'s two tools pooled alongside Claude Code's built-in tools and any other servers' tools, all available from turn one. Explain — in Concept-3 terms — why this pooling is precisely what makes L11's differentiating-description work load-bearing rather than cosmetic.

5. **Community vs custom (guide skill).** The guide says to *"choose existing community MCP servers over custom implementations for standard integrations (e.g., Jira), reserving custom servers for team-specific workflows."* Give one integration where you'd take a community server and one where you'd build custom — and tie the reason back to the Concept-3 cost ("more servers = bigger tool surface").

6. **Resource as catalog (L09/L10 callback).** Your `catalog://plans` resource is now pooled into the session. Name one agent behaviour it *prevents* (relative to a world with only `lookup_plan`), and map it to the guide's exact phrase about resources.

---

## What you now know

- **Three scopes, three files, one precedence order.** *project* = committed `.mcp.json` at repo root (team-shared); *local* and *user* both live in `~/.claude.json` (uncommitted) — local is project-keyed, user is global-to-you. **Precedence: local > project > user**; different-named servers from all scopes are unioned.
- **`.mcp.json` is always the project scope** — the only committed, repo-root config. There is no global `.mcp.json`. (The full version of your L09 question.)
- **`${ENV_VAR}` expansion** lets a committed config reference a secret without committing it — `${VAR}` or `${VAR:-default}`, valid in `command`/`args`/`env`/`headers`. Project scope shares the config; expansion keeps the secret personal.
- **All servers' tools are discovered at connection time and pooled simultaneously** alongside built-ins — no per-request loading, names disambiguated by server. This is *why* L11's differentiating descriptions are load-bearing, and why the guide nudges toward community servers over a sprawl of custom ones.
- **You wired your own L10 server into a live Claude Code session** at project scope, watched it connect and discover its tools, and saw the precedence rule shadow it locally. **Module C (MCP Deep Dive) is complete.**

## Up next

**Module D — the Claude Agent SDK.** You've spent Modules B and C inside the raw Claude API and the MCP protocol. **Lesson 13 — SDK vs raw API: when to use which** steps up a level: the Agent SDK gives you the agentic loop, subagents, hooks, and tool plumbing as a managed runtime instead of the hand-rolled loop you built in L03–L08. L13 draws the line — what the SDK buys you, what it costs in control, and when the raw API is still the right call. Treat all SDK lessons as ground-up (it's new to you).

When you've worked through this lesson and the exercises, tick the box in `lessons/README.md` and tell me you're done — I'll write 13.
