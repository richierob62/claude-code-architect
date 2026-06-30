# Lesson 18 — Hooks: intercept, normalize, and propagate across the agent boundary

**Time**: ~15–20 minutes
**Prerequisites**: L14 (`ClaudeAgentOptions`, tool gating), L15–L17 (subagents, coordinators, fan-out). You'll lean on L07 (structured errors — `isError`/`errorCategory`) and L14's `allowed_tools`-vs-`disallowed_tools` trap.
**Goal**: Add **hooks** — programmatic callbacks the SDK fires at fixed points in the agent's lifecycle — so you can **intercept a tool call before it runs** (allow/deny/modify), **normalize a tool's result after it runs**, and **observe what happens when a subagent finishes**. By the end you'll have a `PreToolUse` hook that blocks a tool with a reason, a `PostToolUse` hook that inspects/normalizes a result, and a clear model of where hooks sit relative to everything you've built.

## Why this matters for the exam

Hooks are a named **Domain 1** capability ("hooks" appears directly in the orchestration task statements), and they're the answer to a class of exam scenarios that the patterns you've learned *can't* cleanly solve:

- *"How do you guarantee an agent never runs a destructive command, regardless of what the model decides?"* → not prompt engineering, not `allowed_tools` (which, per L14, only auto-approves — it doesn't block). The deterministic answer is a **`PreToolUse` hook that denies**.
- *"A tool returns inconsistent shapes; how do you normalize before the model sees it?"* → a **`PostToolUse` hook**.
- *"A subagent in a multi-agent pipeline failed silently; how do you detect it?"* → a **`SubagentStop` hook**.

The through-line: **hooks are deterministic code in the loop.** The model is probabilistic; a hook is a guarantee. The exam rewards knowing *which* control to reach for — and hooks are the one you reach for when "ask the model nicely" isn't strong enough.

---

## The one-sentence version

> **A hook is an async callback you register on `ClaudeAgentOptions` that the SDK fires at a named lifecycle event (before a tool runs, after it runs, when a subagent stops, …); its return value can allow, deny, or modify what happens next.**

---

## Concept 1 — Where hooks sit (the deterministic layer under the model)

Everything you've built so far is *model-driven*: the agent chooses tools (L06), picks subagents (L16), decides to fan out (L17). Hooks are the opposite — **fixed points where your code runs no matter what the model wants.** The two most important fire around every tool call:

```
model decides to call a tool
        │
        ▼
   ┌─────────────┐
   │ PreToolUse  │  ← your code runs BEFORE the tool. Can ALLOW / DENY / MODIFY input.
   └─────────────┘
        │ (if allowed)
        ▼
   tool actually executes
        │
        ▼
   ┌─────────────┐
   │ PostToolUse │  ← your code runs AFTER the tool. Can OBSERVE / NORMALIZE the result.
   └─────────────┘
        │
        ▼
   result goes back to the model
```

`PreToolUse` is a **gate** (it can stop the tool). `PostToolUse` is a **filter** (the tool already ran; you can inspect or rewrite what the model sees). That asymmetry is the thing to remember: **you block *before*, you normalize *after*.**

---

## Concept 2 — How you register a hook

Hooks go on the `hooks` field of `ClaudeAgentOptions`: a **dict keyed by event name**, where each value is a list of **`HookMatcher`** objects. A `HookMatcher` pairs a **matcher** (which tools this applies to) with a list of **callbacks**:

```python
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

options = ClaudeAgentOptions(
    model="claude-haiku-4-5",
    setting_sources=[],
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[block_bash]),   # only fires for the Bash tool
        ],
        "PostToolUse": [
            HookMatcher(matcher=None, hooks=[normalize_result]),  # matcher=None → every tool
        ],
    },
)
```

- **`matcher`** — a tool-name pattern (`"Bash"`, `"Write|Edit"`, or `None` for all tools). This is how you scope a hook to just the tools you care about instead of running on every call.
- **`hooks`** — a list of async callbacks. Multiple callbacks per event are allowed.

---

## Concept 3 — The callback: signature and the return shape that controls flow

A hook callback is an **async function** taking three arguments:

```python
async def block_bash(input_data, tool_use_id, context):
    ...
    return { ... }   # the dict that tells the SDK what to do next
```

- **`input_data`** — a dict describing the event. For `PreToolUse` it carries `tool_name` and `tool_input`; for `PostToolUse` it adds the `tool_response` (the result). It also carries `hook_event_name`, which you can guard on.
- **`tool_use_id`** — correlates the `Pre` and `Post` events for the *same* tool call (so a `PostToolUse` can match the `PreToolUse` it followed).
- **`context`** — a context object (largely reserved; you usually ignore it).

**The return value is the control surface.** An empty dict `{}` means "do nothing special — proceed." To **deny** a tool call from `PreToolUse`:

```python
async def block_bash(input_data, tool_use_id, context):
    if input_data["tool_name"] == "Bash":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Bash is disabled in this session.",
            }
        }
    return {}   # everything else proceeds
```

The model sees the denial (with your reason) as the tool result and adapts — exactly the L14 finding that `disallowed_tools=["Bash"]` blocks, but now **conditional and reasoned** instead of a blanket ban. A hook can deny *some* Bash calls and allow others; a static `disallowed_tools` can't.

> **Verify the exact keys when you run it.** The return-dict spelling (`hookSpecificOutput`, `permissionDecision: "deny"`, and `PostToolUse`'s `updatedToolOutput`) is the documented shape, but these key names have drifted between the Claude Code CLI's JSON-hook format and the Python SDK's typed format across versions. The build below prints what actually flows through, so you confirm the real shape against *your* installed `claude-agent-sdk` rather than trusting the lesson. If a deny doesn't take, dump `input_data` and inspect the keys — that's the lesson-rigor move.

---

## Concept 4 — `PostToolUse`: observe and normalize, but you can't un-ring the bell

`PostToolUse` fires **after** the tool executed, so it **cannot block** — the side effect already happened. What it *can* do:

1. **Observe** — read `input_data["tool_response"]` for logging, metrics, audit.
2. **Normalize / rewrite** — return a replacement so the *model* sees a cleaned-up version (redact a secret, coerce an inconsistent shape into a stable one, truncate noise).

```python
async def normalize_result(input_data, tool_use_id, context):
    if input_data.get("hook_event_name") != "PostToolUse":
        return {}
    response = input_data.get("tool_response")
    print(f"[POST] {input_data['tool_name']} → {str(response)[:80]}")
    return {}   # observe-only here; return a replacement to actually rewrite
```

The mental split, again: **`PreToolUse` is your only chance to *prevent*; `PostToolUse` is your only chance to *clean up*.** Choosing the wrong one is the classic mistake — you can't sanitize-then-block in `PostToolUse`, because by then the `rm -rf` already ran.

---

## Concept 5 — Crossing the agent boundary: `SubagentStop` and error propagation

L15–L17 built multi-agent systems where a subagent runs in its **own isolated context** and returns one result. That isolation (the whole point of L15) has a cost: **if a subagent fails partway, the parent doesn't automatically get a structured "subagent errored" signal** — it just gets whatever the subagent returned. This is the multi-agent version of L07's problem: an error has to be *propagated* explicitly, or it's invisible.

The **`SubagentStop`** hook fires when a subagent (spawned via the `Task`/`Agent` tool) finishes — success *or* failure. Its `input_data` identifies which subagent stopped and points at the subagent's transcript, so the parent side can detect "that worker had a failure" rather than silently trusting a possibly-degraded result.

> **There is no automatic cross-agent error event beyond this.** Propagation is a discipline you implement: a `SubagentStop` hook that inspects the outcome, or — more robustly — workers that return **structured errors** (L07's `isError`/`errorCategory`) in their result so the coordinator can branch on them. Hooks give you the *interception point*; L07's structured-error shape gives you the *payload* to propagate. They compose.

---

## Your build

Create `lessons/scripts/hooks_lab.py`. Build a single agent with **two hooks** and watch them fire — a `PreToolUse` gate and a `PostToolUse` filter — on a task that wants a tool.

1. **Conventions:** `model="claude-haiku-4-5"`, `setting_sources=[]`, `permission_mode="bypassPermissions"`. Use `query()` (or `ClaudeSDKClient`) as in L14.

2. **`PreToolUse` deny hook.** Register a `HookMatcher(matcher="Bash", hooks=[block_bash])`. The callback denies any `Bash` call with a clear reason (Concept 3's shape). **Print `[PRE] saw tool=<name>` at the top of the callback** so you can see it fire and confirm the matcher scoped it to Bash.

3. **`PostToolUse` observe hook.** Register `HookMatcher(matcher=None, hooks=[log_result])` — fires for every tool. Print `[POST] <tool_name> → <first 80 chars of tool_response>`. This is your window into what the model actually got back.

4. **Drive it two ways and compare:**
   - **(a)** Ask something that tempts Bash: *"Use the Bash tool to run `ls` and tell me the files."* Watch the `PreToolUse` deny fire, and watch the model react to being blocked (it should explain it can't, or pivot).
   - **(b)** Allow a *different* tool through (e.g. don't disallow `Glob`/`Read`) on a task that uses it, so your `PostToolUse` hook actually prints a real result and you see the normalize/observe point working.

5. Print `ResultMessage.total_cost_usd`. Cheap — **don't loop it.**

> **The point of the build is to *verify the return-dict shape*, not just to see text.** If your deny doesn't take effect, add `print(input_data)` at the top of `block_bash` and inspect the real keys (`tool_name`? `tool_input`? nested?) — then fix the return dict to match what your SDK version actually expects. That mismatch (CLI-format vs SDK-format keys) is the single most likely thing to trip you, and finding it yourself is the lesson.

---

## Exercises

1. **Gate vs filter.** In one sentence each, state what `PreToolUse` can do that `PostToolUse` cannot, and vice versa. Why can't `PostToolUse` block a tool?

2. **Hook vs `disallowed_tools`.** L14 taught `disallowed_tools=["Bash"]` as the real block. When would you reach for a `PreToolUse` *hook* to deny Bash instead of just listing it in `disallowed_tools`? (Hint: think *conditional*.)

3. **Right tool for the symptom.** For each, name the hook event: (a) redact API keys from a web-fetch result before the model sees it; (b) refuse any `Write` to a path outside `/sandbox`; (c) log every time a subagent finishes so you can spot failures; (d) inject extra context whenever the user submits a prompt.

4. **Propagation design.** A coordinator fans out 3 research subagents (L17). One hits a rate-limit error mid-run. Describe two complementary mechanisms — one using a hook, one using L07 — that together ensure the coordinator *knows* that worker degraded rather than trusting its partial output.

5. **The wrong layer.** A teammate puts secret-redaction logic in a `PreToolUse` hook on a `WebFetch` tool. Why is that the wrong event, and which event should it be? What does the model see in each case?

---

## What to remember

- **Hooks are deterministic code at fixed lifecycle points** — the guarantee layer under the probabilistic model. Reach for them when "prompt the model to behave" isn't strong enough.
- **`PreToolUse` = gate** (allow/deny/modify *input*, runs *before*). **`PostToolUse` = filter** (observe/normalize *output*, runs *after*, can't block).
- **Register via `hooks={ "EventName": [HookMatcher(matcher=..., hooks=[fn])] }`**; `matcher=None` matches all tools; callbacks are `async (input_data, tool_use_id, context)`.
- **The return dict is the control surface** — `{}` to proceed, `hookSpecificOutput` with a `permissionDecision` to deny. **Verify the exact keys against your SDK version by running it.**
- **`SubagentStop` + structured errors (L07)** are how you propagate failures across the multi-agent boundary — isolation means errors don't cross automatically.
