# Lesson 14 — `ClaudeAgentOptions`: your first real `query()`

**Time**: ~15 minutes
**Prerequisites**: L13 (you know *what* the SDK is and *when* to reach for it). You'll also lean on L08 (`tool_choice`), L11 (description craft as behaviour-shaping), and the L03 loop.
**Goal**: Write and run your **first real Claude Agent SDK call**. Learn the config object — `ClaudeAgentOptions` — that drives every agent in Module D: how `system_prompt` sets behaviour, how `allowed_tools` / `disallowed_tools` shape the tool surface (and the surprising truth about which one actually *blocks*), and how `model` trades cost for capability. By the end you'll have run a live `query()`, read the messages it streams back, and seen the real per-call cost — which is itself a lesson.

## Why this matters for the exam

This is the first hands-on lesson of **Module D — the Claude Agent SDK**, the advanced half of **Domain 1 (27%)**. Every later D1 task (subagents, coordinator/worker, hooks) is configured through this same object. The guide's Domain 1 outcomes include *"Configure agents using the Claude Agent SDK — system prompts, tool access, model selection."* That sentence is literally the three fields this lesson teaches. Lock these names and their **real** semantics now and the rest of Module D is variations on a theme.

> **This is new to you** (profile: "Claude Agent SDK: new — treat ground-up"). We go slowly and we *run everything*, because — as you'll see — the SDK behaves in ways the field names don't fully advertise.

---

## Step 0 — Install the SDK

It's already a project dependency (added on `main`), so it's in your venv. Confirm:

```bash
uv run python -c "import importlib.metadata as m; print('claude-agent-sdk', m.version('claude-agent-sdk'))"
```

You should see something like `claude-agent-sdk 0.2.109`. If you get `ModuleNotFoundError`, run `uv sync` first.

> **Why a 60 MB download?** The Python SDK bundles the Claude Code CLI inside the wheel (recall L13's "the SDK manages the CLI/runtime for you" — this is that, literally). No separate Node install. Auth is the **same `ANTHROPIC_API_KEY`** you've used all course.

---

## Concept 1 — The shape of a `query()` call

Here is the whole anatomy. Three imports, one options object, one `async for`:

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock, ResultMessage

async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are a terse assistant. Answer in one short sentence.",
        allowed_tools=[],            # see Concept 3 — this does NOT mean what you think
        model="claude-haiku-4-5",
    )
    async for message in query(prompt="What is the capital of France?", options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print("ASSISTANT:", block.text)
        elif isinstance(message, ResultMessage):
            print("COST: $", message.total_cost_usd)

asyncio.run(main())
```

Compare this to your L03 raw loop. **The entire `while response.stop_reason == "tool_use":` machinery is gone.** You don't read `stop_reason`, you don't append `tool_result`, you don't dispatch tools. `query()` runs that loop *for you* and **streams you the messages it produces along the way**. That streaming is the key shift: the raw API returns one `Message` per `create()` call; `query()` yields a *sequence* of messages as the agent works.

### The four things to notice

1. **It's async.** `query()` is an async generator — you must `async for` it, inside an `async def`, launched with `asyncio.run(...)`. (Your raw-API calls were synchronous. The SDK is async-first because an agent loop is inherently I/O-bound — it's waiting on the model and on tools.)
2. **`prompt` and `options` are separate.** The user's request goes in `prompt`. *Everything about the agent's identity and capabilities* goes in `options`. That separation is the mental model: **prompt = the task, options = the agent.**
3. **You filter the message stream by type.** Not every yielded message is the answer. You `isinstance`-check for the type you care about — exactly the discriminated-union / content-block polymorphism you met in L02, now one level up at the *message* level instead of the *block* level.
4. **`ClaudeAgentOptions` is the spine.** It's the only configuration surface. `system_prompt`, `allowed_tools`, `model`, plus `mcp_servers`, `max_turns`, `agents` (L15+), `hooks` (L18) — all of Module D is fields on this one dataclass.

---

## Step 1 — Run it for real

Save the Concept-1 snippet as `lessons/scripts/first_query.py`. Then, from the repo root (so `.env` loads):

```bash
set -a && . ./.env && set +a
uv run python lessons/scripts/first_query.py
```

**Verified output** (real run, `claude-haiku-4-5`):

```
ASSISTANT: Paris is the capital of France.
COST: $ 0.0300075
```

Read that cost again. **Three cents.** To answer "capital of France." On Haiku.

That number is not a bug — it's the most important thing in this lesson, so it gets its own concept.

---

## Concept 2 — The message stream (and why "capital of France" cost 3¢)

If you print `type(message).__name__` for *every* message (not just the ones you filter for), a single `query()` call yields this sequence:

```
SystemMessage          ← init / config / available-tools announcements
SystemMessage
SystemMessage
SystemMessage
SystemMessage
SystemMessage
AssistantMessage       ← the actual answer (one or more TextBlock / ToolUseBlock)
ResultMessage          ← final: cost, usage, num_turns, the result text
```

Two takeaways:

- **`AssistantMessage` is where the answer lives** — and its `.content` is a *list of blocks* (`TextBlock` with `.text`, or `ToolUseBlock` with `.name`/`.input`), the same block polymorphism from L02. You loop the blocks and pull text out.
- **`ResultMessage` is the receipt.** It carries `total_cost_usd`, `usage` (token counts), `num_turns`, and `result` (the final answer as a plain string — a shortcut when you don't want to reassemble it from blocks).

### Why the cost is so high

Print `message.usage` on the `ResultMessage` and you'll see the culprit:

```
usage: {'input_tokens': 10, 'cache_creation_input_tokens': 23658, 'output_tokens': 85, ...}
```

Your prompt was ~10 tokens. But the SDK fed the model **23,658 additional tokens** — the Claude Code agent harness: its system prompt, every built-in tool's full definition (`Read`, `Bash`, `Grep`, `Glob`, `WebSearch`, …), and your project's `CLAUDE.md`. That's the harness L13 told you the SDK runs under the hood — and now you're *paying for it on every call*.

**This makes L13's trade-off literal and measured.** The same question on the raw Messages API would cost ~$0.0001 — because the raw API sends only your messages, no harness. So the SDK one-shot is **roughly 200–300× more expensive** (≈300× at the ~3¢ default, ≈200× even after trimming to the ~2¢ floor below). The SDK's leverage (loop + tools + context, all free of hand-rolling) has a real token price. The exam's "start at the simplest tier" principle isn't just architectural tidiness: **wrapping the SDK around a one-shot classification is, concretely, a 200–300× cost multiplier.** This is exactly why L13 said "single call → raw API."

### You can cut the overhead (somewhat)

One big token-eater is optional. Add `setting_sources=[]` to stop loading the project `CLAUDE.md` and settings files:

```python
options = ClaudeAgentOptions(
    system_prompt="You are terse.",
    allowed_tools=[],
    model="claude-haiku-4-5",
    setting_sources=[],   # don't load project CLAUDE.md / settings
)
```

**Verified, same prompt, running the script cold from the shell** (i.e. what you'll actually see):

| Config | harness tokens (`cache_creation`) | Cost |
|---|---|---|
| default | ~23,000 | ~$0.03 |
| `setting_sources=[]` | ~16,900 | ~$0.022 |

`setting_sources=[]` removes your `CLAUDE.md` + settings (~6k tokens). What remains is the **Claude Code base system prompt (~10k, irremovable — it *is* the harness)** plus the **built-in tool definitions (~6.7k)**. So the floor for a one-shot SDK call on Haiku is roughly **2¢**, not a fraction of a cent. The harness is never *zero* — that's the price of the loop running for you.

> **Why you won't see "half a cent" — the cache trap (worth understanding).** You may find blog posts or examples quoting *much* lower SDK costs (~$0.005). Those are **warm-cache** numbers. The SDK uses prompt caching: the **first** call in a process pays the **cache-creation** premium (~25% over normal input) to store the harness; **later calls in the same process** hit it at the **cache-read** rate (~10% of input — a 90% discount). Print `usage` and you'll see `cache_creation_input_tokens` high and `cache_read_input_tokens: 0` — that zero means you paid full creation price. **A one-shot script that starts, asks once, and exits can never benefit:** the cache dies with the process (and only lives ~5 minutes anyway). So running `first_query.py` repeatedly always pays the cold price. The cheap warm-cache rate only materializes inside a **long-lived agent making many calls** — which is the SDK's actual use case, and the opposite of a one-shot.

**For the rest of Module D, set `setting_sources=[]` and `model="claude-haiku-4-5"` on every exercise.** At ~1–2¢ per cold call that keeps the whole module well inside your $3–5 budget — but don't put `query()` calls in a loop without thinking, because each one pays the cold harness price again.

---

## Concept 3 — `system_prompt`: the agent's identity

`system_prompt` is the same lever you've used all course, now naming the *agent's* persistent behaviour rather than a single message's. It accepts:

- a **plain string** — `"You are a terse assistant."` (what you'll use 95% of the time), or
- a **preset form** — `{"type": "preset", "preset": "claude_code"}` to inherit Claude Code's own system prompt, optionally with `"append": "...your additions..."` to extend it.

**This is L11's description-craft skill, lifted to the agent level.** In L11 you learned that a tool's *description* is what makes the model select it correctly; here, the *system prompt* is what makes the agent behave correctly across the whole loop. Same skill — purpose, boundaries, "do X, don't do Y" — one altitude up. A vague system prompt produces a vague agent the same way a vague tool description produced unreliable selection.

> If you omit `system_prompt` entirely, you get the SDK's default (Claude Code's) — which is verbose and tool-happy. For a focused agent, always set one.

---

## Concept 4 — `allowed_tools` does NOT block tools (the trap)

L13's "Up next" promised that `allowed_tools` is "the L08 `tool_choice` instinct, now declarative." That's the *intuition* — but the literal behaviour has a trap, and it's the kind of thing the exam tests and that you'd only learn by **running it**. So let's run it.

Give the agent a task that needs a tool, but pass `allowed_tools=[]`:

```python
options = ClaudeAgentOptions(
    system_prompt="You are a helpful assistant.",
    allowed_tools=[],                 # "no tools" ... right?
    model="claude-haiku-4-5",
    setting_sources=[],
    # cwd defaults to where you launch the script. Run this from the repo root
    # so the agent's Bash/Glob sees `lessons/`. (To be explicit/portable instead
    # of relying on that default, pass cwd=str(Path(__file__).resolve().parents[2]).)
)
# prompt: "How many .md files are in the lessons/ directory? Use the Bash tool to check."
```

**Verified output:**

```
TOOL_USE: Bash
ASSISTANT: There are 15 .md files in the lessons/ directory.
```

**Bash ran. With `allowed_tools=[]`.** That is *not* what the name suggests, and it would be easy to ship a lesson asserting the wrong thing here. Here's the real model:

- **`allowed_tools` is an *auto-approve* list, not an *allow-list-and-block-the-rest*.** It names the tools that run *without prompting for permission*. In a headless `query()` run (no human at a permission prompt), a tool that's *not* in `allowed_tools` doesn't get blocked — there's no one to deny it, so the SDK proceeds. The list controls *whether you're asked*, not *whether it can run*.
- **`disallowed_tools` is the real block lever.** To actually prevent a tool, name it here.

**Verified** — same task, `disallowed_tools=["Bash"]`:

```
TOOL_USE: Glob          ← model fell back to a different tool
ASSISTANT: There are 15 .md files in the lessons/ directory:
1. 00-setup.md ...
```

Bash was genuinely blocked; the model routed around it to `Glob`. **That's** the hard gate.

### The honest mental model

| Field | What it actually does |
|---|---|
| `allowed_tools=["Read","Bash"]` | These run **without a permission prompt** (auto-approved). |
| `disallowed_tools=["Bash"]` | This tool is **blocked** — the model cannot use it at all. |
| `permission_mode` | Governs the *prompting* behaviour for tools not on either list (`"default"`, `"acceptEdits"`, `"bypassPermissions"`). In headless runs with no prompt handler, un-listed tools effectively proceed. |

So the L08 analogy holds *in spirit* — you're declaring the tool surface — but the precise lever for "this tool must not run" is **`disallowed_tools`**, and `allowed_tools` is about *friction* (prompt or not), not *capability*. Get this wrong on the exam and you'll mis-answer a "how do I prevent the agent from writing files?" question (answer: `disallowed_tools=["Write","Edit"]`, **not** `allowed_tools=[]`).

---

## Concept 5 — `model`: cost vs capability, made explicit

`model` takes a model id — use the full alias form `"claude-haiku-4-5"` (the safe, documented choice; bare aliases like `"haiku"` are a CLI convenience but not guaranteed in the SDK's typed field). Omit it and you inherit the CLI's default model — which may be Sonnet or Opus, i.e. **much more expensive than you intended.** For Module D exercises, **always set `model="claude-haiku-4-5"` explicitly** — your Haiku-for-exercises convention, now a field instead of a habit.

This is the same cost/capability trade as the raw API, with one SDK wrinkle: because every call also pays the harness-overhead tokens from Concept 2, the model choice multiplies against a *larger* base. A pricier model on the SDK is pricier *per harness-laden call*, so "right-size the model" matters even more here than on the raw API.

---

## Your build (this lesson has a real one)

In `lessons/scripts/`, build `agent_options_lab.py` that runs **three** `query()` calls and prints the assistant text + cost for each. All three use `model="claude-haiku-4-5"` and `setting_sources=[]` to stay cheap.

1. **Identity.** `system_prompt="You answer only in haiku (5-7-5)."`, `allowed_tools=[]`, prompt `"Describe the ocean."` — confirm the system prompt shapes behaviour.
2. **The `allowed_tools` trap.** Prompt `"List the .md files in lessons/ using the Bash tool."` with `allowed_tools=[]` and `cwd` set to the repo. Confirm — by printing `ToolUseBlock` names — that **Bash runs anyway**. (This is the trap from Concept 4; prove it to yourself.)
3. **The real block.** Same as (2) but add `disallowed_tools=["Bash"]`. Confirm the model either refuses or falls back to another tool (`Glob`/`Read`).

Print each call's `ResultMessage.total_cost_usd` and add them up. Expect a total well under 5¢. **Keep it to these three runs** — each SDK call costs more than a raw Haiku call, so don't loop them.

> Helper for pulling tool names out of the stream:
> ```python
> for block in message.content:
>     if isinstance(block, TextBlock):
>         print("TEXT:", block.text)
>     elif type(block).__name__ == "ToolUseBlock":
>         print("TOOL:", block.name)
> ```

---

## Exercises

1. **prompt vs options.** In one sentence each: what belongs in `prompt`, and what belongs in `options`? Why is that separation the right design (think about reusing one agent across many tasks)?

2. **The cost trap.** Your teammate wraps `query()` around a function that classifies 10,000 tickets, one `query()` call each, because "the SDK is nicer." Using the verified numbers from Concept 2, estimate the cost delta versus the raw Messages API, and name the L13 principle they violated.

3. **The `allowed_tools` trap, in words.** A colleague writes `allowed_tools=[]` and says "good, now the agent can't touch the filesystem." Why are they wrong, and what should they have written instead to actually prevent file writes?

4. **`allowed_tools` vs `disallowed_tools`.** Fill in the field(s) for each goal: (a) let `Read` and `Grep` run without prompting, (b) make it impossible for the agent to run shell commands, (c) prompt-free reads but hard-blocked writes.

5. **Message-stream filtering (L02 callback).** Why do you `isinstance`-check messages instead of taking "the last one"? Tie this to the content-block discriminated-union shape you learned in L02 — what's the relationship between *message* types here and *block* types there?

6. **system_prompt = description craft (L11 callback).** In L11, differentiating two tools' descriptions fixed unreliable selection. State the analogous claim one level up: what does a sharp vs. vague `system_prompt` change about an *agent's* behaviour across the loop?

7. **Model sizing.** Why does "right-size the model" bite harder on the SDK than on the raw API? (Hint: what does every SDK call pay *before* your prompt's tokens?)

---

## What you now know

- **The `query()` shape:** async generator, `async for message in query(prompt=..., options=...)`, filter the streamed messages by type. The whole L03 loop is now inside the SDK.
- **`ClaudeAgentOptions` is the agent's whole identity:** `prompt` = the task, `options` = the agent. `system_prompt`, `allowed_tools`, `disallowed_tools`, `model`, plus `mcp_servers`/`max_turns`/`agents`/`hooks` for later lessons.
- **The message stream:** `SystemMessage`×N → `AssistantMessage` (answer, in `.content` blocks) → `ResultMessage` (cost/usage/result receipt).
- **The cost reality:** every SDK call pays for the agent harness (≈2.5k–23k extra tokens). "Capital of France" cost 3¢ vs ~$0.0001 raw — L13's trade-off, measured. Cut it with `setting_sources=[]`; set `model` explicitly.
- **The `allowed_tools` trap:** it's an *auto-approve* list (controls prompting), **not** a hard block. The real block lever is **`disallowed_tools`**. Getting this backwards is a classic exam mis-answer.

## Up next

**Lesson 15 — Subagent spawning: explicit context passing.** You now have one agent configured. L15 introduces the genuinely new capability L13 flagged: spawning *isolated subagents* with their own system prompt, tools, and context — and the critical discipline that a subagent starts with **none of the parent's context** unless you pass it explicitly. This is where the `agents` field on `ClaudeAgentOptions` (which you saw listed today) comes alive, and where Domain 1's "multi-agent orchestration" actually begins.

When you've worked through this lesson and the build, tick the box in `lessons/README.md` and tell me you're done — I'll write 15.
