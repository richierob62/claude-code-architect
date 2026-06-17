# Lesson 13 — SDK vs raw API: when to use which

**Time**: ~15 minutes
**Prerequisites**: Modules B and C. Specifically, you hand-rolled the agentic loop in L03 (`while stop_reason == "tool_use"`), structured errors in L07, `tool_choice` in L08, and an MCP server + `.mcp.json` wiring in L10–L12. **This lesson names what all of that becomes when you stop hand-rolling it.**
**Goal**: Draw the line between three surfaces — the **raw Messages API**, the **Claude Agent SDK**, and **Claude Code** — and know, for a given task, which one to reach for and what each costs you. By the end you'll be able to answer the exam's "which surface?" questions and explain *why* in terms of the loop you already built by hand.

## Why this matters for the exam

This opens **Module D — the Claude Agent SDK**, the advanced half of **Domain 1 (Agentic Architecture & Orchestration, 27%)** — the single heaviest domain on the exam. Every D1 task statement from here on (AgentDefinition, subagent spawning, coordinator/subagent, hooks) assumes you know *what the SDK is* and *when it's the right tool*. The guide frames the whole domain around:

> *"Building agentic applications using the Claude Agent SDK, including multi-agent orchestration, subagent delegation, tool integration, and lifecycle hooks."*

L13 is the orientation lesson: before you learn the SDK's pieces, you need the mental model of where it sits relative to the raw API you spent Modules B–C inside. **This is new to you** (your profile: "Claude Agent SDK: new — treat ground-up"), so we build it from the loop you already understand.

---

## The one-sentence version

> **The raw Messages API gives you a *model*. The Claude Agent SDK gives you the *agent harness* — the loop, the tools, the context management — that you would otherwise build on top of that model yourself.**

Everything else in this lesson is unpacking that sentence.

---

## Concept 1 — Three surfaces, one spectrum

You've now touched two of three surfaces. Here's the full picture, from most control to least:

| Surface | What you write | What runs the loop | You reach for it when… |
|---|---|---|---|
| **Raw Messages API** (`client.messages.create`) | Every turn yourself: send request, read `stop_reason`, dispatch tools, append `tool_result`, loop | **You do.** (The `while` loop from L03.) | You need a single call, or you need *total* control over each step of the loop. |
| **Claude Agent SDK** (`claude_agent_sdk`) | A prompt + an options object. Tools/loop/context are handled. | **The SDK does.** | You want an agent — model-driven multi-step work — without rebuilding the harness. |
| **Claude Code** (the CLI / IDE you use daily) | Nothing — you type at a prompt | The SDK does, under a fixed UI | You're a human doing interactive work, not building a product. |

The key realization: **these are not three different technologies. They are three altitudes over the same `POST /v1/messages` endpoint.** Claude Code is built *on* the Agent SDK; the Agent SDK is built *on* the Messages API. As you go down the table you trade control for leverage.

> **Exam framing.** The guide's Domain 1 is split: the early task statements (which you did in Module B) are about the **raw agentic loop** — `stop_reason`, appending tool results, model-driven vs pre-configured control flow. The later ones (Module D) are about the **SDK** — because once the loop is a solved, managed thing, the interesting questions move up a level to *orchestration* (subagents, hooks, delegation). L13 is the hinge between those two halves.

---

## Concept 2 — What the SDK actually does for you (mapped to what you built)

This is the heart of the lesson. Every column on the right is something you wrote by hand in Modules B–C. The SDK is the column on the left.

| The SDK gives you… | …which replaces this hand-rolled work from earlier lessons |
|---|---|
| **The agentic loop** — runs `tool_use → execute → tool_result → repeat` until `end_turn` | Your L03 `while response.stop_reason == "tool_use":` loop, including the L05 lesson that the *correct* terminator is `stop_reason`, not text-parsing |
| **Built-in tools** — `Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob`, `WebSearch`, `WebFetch`, … | The tool *implementations* you'd otherwise write and dispatch yourself (your L06 `IMPLEMENTATIONS[name](**input)` dispatch dict) |
| **MCP integration** — point it at MCP servers; their tools join the pool | Your L10–L12 work wiring `support_server.py` in via `.mcp.json` (the SDK consumes the *same* servers) |
| **Subagents** — spawn isolated sub-tasks with their own context/tools | (You haven't built this — it's genuinely new, and it's L15–L17) |
| **Hooks** — intercept tool calls (`PreToolUse`/`PostToolUse`) for deterministic guarantees | (New — L18. This is the guide's "programmatic enforcement over prompt-based" idea) |
| **Context management** — compaction, trimming, keeping the transcript in budget | (You'll meet the manual version in Module G; the SDK does a lot of it for you) |
| **Permission modes** — gate which tools can run, and whether to ask first | The "should this side-effecting tool be allowed?" judgement you'd otherwise hard-code |

Read that table top to bottom and you've just described **the arc of this whole course**: Modules B–C taught you to build the left column's first three rows by hand *specifically so that when the SDK hands them to you, you know exactly what's inside the box.* That's the "true mastery" goal — you can use the SDK *and* explain what it abstracts.

---

## Concept 3 — The decision rule (and the honest trade-offs)

The exam loves "which surface?" scenarios. Here's the rule, and it's the same four-question test the Claude API guidance uses for "should I build an agent at all":

**Use the raw Messages API when:**
- It's a **single call** — classify, summarize, extract, answer. No loop needed. (Wrapping the SDK around a one-shot classification is overkill.)
- You need **total control of the loop** — custom logging per step, human-in-the-loop approval before *every* tool, conditional execution, a bespoke stop condition the SDK doesn't expose. (This is exactly why L08's *manual* `tool_choice` loop exists.)
- You're embedding into a **non-Python/TS runtime** or have a hard constraint against the SDK's dependencies.

**Use the Claude Agent SDK when:**
- The task is **genuinely agentic** — multi-step, model decides the path, not fully specifiable up front (the L04 **Agent** pattern, not a fixed prompt-chain).
- You'd otherwise be **re-implementing the loop, tool execution, and context management** — i.e. rebuilding the harness. Don't. That's the SDK's whole job.
- You want **subagents, hooks, or built-in tools** without writing them.

**Use Claude Code when:**
- You (a human) are doing interactive engineering work. It's not a surface you *build products on* directly — but it *is* the SDK wearing a UI, which is why it's on the spectrum.

### The trade-off, stated honestly

The SDK is not free leverage. What you give up versus the raw API:

- **Control granularity.** The loop runs *for* you, so injecting custom behavior mid-loop means using the SDK's hooks/options, not just writing Python. If you need something the SDK doesn't expose, you fight the abstraction.
- **A heavier dependency.** The SDK is a bigger thing than the `anthropic` client. It manages an agent runtime under the hood (the same harness that powers Claude Code), not just HTTP calls to `/v1/messages`.
- **Less visibility into each token** unless you ask for it. The raw loop puts every `stop_reason` and `tool_result` in your hands; the SDK keeps them in the harness and surfaces messages to you.

The guide's recurring principle applies here exactly as it did for "should I build an agent": **start at the simplest tier that meets the need.** Single call → raw API. Need an agent → SDK. Don't climb the spectrum for prestige; climb it when the task demands the leverage.

---

## Concept 4 — Two ways to call the SDK: `query()` vs `ClaudeSDKClient`

When you *do* reach for the SDK (Python package: **`claude-agent-sdk`**, import **`claude_agent_sdk`**), there are two entry points. Knowing the difference is a likely exam discriminator and frames every SDK lesson after this one.

| | `query()` | `ClaudeSDKClient` |
|---|---|---|
| Shape | An async generator function | A class (async context manager) |
| State | **Stateless** — each call is a fresh session | **Stateful** — holds conversation history across turns |
| Use it for | One-shot or simple streaming: "do this task, stream me the messages" | Interactive, multi-turn: send a follow-up, react, send another; can interrupt |
| Mental model | Like a single `messages.create` but with the *whole agent loop* behind it | Like your L01 `ConversationManager`, but the SDK owns the loop and tools |

The minimal `query()` shape (you'll run a real one in L14 — this is just to anchor the names):

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    async for message in query(
        prompt="What is 2 + 2?",
        options=ClaudeAgentOptions(
            system_prompt="You are concise.",
            allowed_tools=[],          # no tools needed for arithmetic
        ),
    ):
        print(message)

asyncio.run(main())
```

Three names to lock in from that snippet, because they recur in every Module D lesson:
- **`query()`** — the stateless entry point.
- **`ClaudeAgentOptions`** — the config object. `system_prompt`, `allowed_tools`, `model`, `mcp_servers`, subagents, hooks all live here. (L14 is entirely about this object.)
- **`ClaudeSDKClient`** — the stateful alternative, for when one shot isn't enough.

> **A note on what's under the hood (worth knowing, easy to over-worry).** The Agent SDK doesn't just make HTTP calls — it runs the **same agent harness that powers Claude Code**, managing the CLI/runtime for you. Auth is the *same* `ANTHROPIC_API_KEY` you've used all course. We are **not** running a live SDK call this lesson (it's conceptual + setup-sensitive); L14 does the first real one. If install/runtime friction shows up there, that's expected for a new surface — we'll work through it.

---

## No build this lesson (deliberately)

This is an orientation lesson — the payoff is the mental model, not a script. The "build" is the exercise set below, which is pure reasoning of the kind the exam asks. L14 starts the hands-on SDK work (your first real `query()` call + `ClaudeAgentOptions`).

If you want to get ahead on setup, you *may* `uv add claude-agent-sdk` now — but **don't run anything yet**; we'll do the first call together in L14 so any environment friction is debugged in context rather than alone.

---

## Exercises (do these before moving on)

1. **Place the surface.** For each, name the surface (raw Messages API / Agent SDK / Claude Code) and justify in one line:
   (a) A nightly job that reads 500 support tickets and tags each with a category.
   (b) A "fix this failing test, then open a PR" agent that explores the repo, edits files, and runs the suite until green.
   (c) You, right now, asking your editor to refactor a function.
   (d) An agent that must pause for explicit human approval *before every single* file write, with a custom audit-log entry per step.

2. **Map it back.** Pick three rows from the Concept-2 table (SDK feature → hand-rolled equivalent). For each, name the *specific* earlier lesson where you built the right-hand side by hand, and state in one sentence what the SDK now does instead.

3. **The honest trade.** A teammate says "let's just always use the Agent SDK — it's higher-level, so it's strictly better." Give the two strongest reasons that's wrong, tied to the trade-offs in Concept 3.

4. **`query()` vs `ClaudeSDKClient`.** A chat product needs to (a) answer a one-off "summarize this file" request, and separately (b) hold a back-and-forth where the user keeps refining the result over several turns. Which entry point for each, and why — in terms of *state*?

5. **Spectrum check (L04 callback).** In L04 you learned the **Agent** pattern (single model + generic loop + model-chosen path) vs **workflow** patterns (prompt chaining, routing — *you* wire the steps). Which of those two maps naturally onto "reach for the Agent SDK," and which onto "a code-orchestrated raw-API pipeline"? Explain the correspondence.

6. **Why not Claude Code?** Claude Code *is* the Agent SDK with a UI. Give one concrete reason you'd build on the SDK directly instead of "just using Claude Code" for a production feature. (Hint: who's the operator at runtime?)

---

## What you now know

- **Three surfaces, one spectrum over `/v1/messages`:** raw Messages API (you run the loop) → Agent SDK (the harness runs it) → Claude Code (the harness + a UI for humans). Control trades for leverage as you descend.
- **The SDK is the harness you hand-rolled in Modules B–C, handed to you:** the agentic loop (L03/L05), tool execution + dispatch (L06), MCP server consumption (L10–L12) — *plus* genuinely new capabilities you'll learn next (subagents L15–L17, hooks L18, context management).
- **The decision rule:** single call → raw API; total-control loop → raw API; genuinely agentic multi-step work → SDK; interactive human work → Claude Code. **Start at the simplest tier that meets the need.**
- **The trade-offs are real:** the SDK costs you loop-level control granularity, adds a heavier runtime dependency, and keeps per-token detail inside the harness unless you ask. Higher-level ≠ strictly better.
- **Two entry points:** `query()` (stateless, one-shot/streaming) vs `ClaudeSDKClient` (stateful, interactive multi-turn), both configured via **`ClaudeAgentOptions`**. Same `ANTHROPIC_API_KEY` as the raw API.

## Up next

**Lesson 14 — AgentDefinition & `ClaudeAgentOptions`: system prompts, allowedTools, model selection.** Now that you know *what* the SDK is and *when* to use it, L14 opens the box: you'll write your first real `query()` call and learn the config object that drives every agent — how `system_prompt` becomes the agent's behaviour (the L11 description-craft skill, now at the agent level), how `allowed_tools` gates the tool surface (the L08 `tool_choice` instinct, now declarative), and how `model` selection trades cost for capability (your Haiku-for-exercises convention, made explicit). First real SDK code — treat it ground-up.

When you've worked through this lesson and the exercises, tick the box in `lessons/README.md` and tell me you're done — I'll write 14.
