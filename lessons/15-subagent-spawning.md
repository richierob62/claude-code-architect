# Lesson 15 — Subagent spawning: explicit context passing

**Time**: ~15 minutes
**Prerequisites**: L14 (you can write a `query()` call and configure `ClaudeAgentOptions`). You'll also lean on L04 (the orchestrator-workers pattern — "remember Charlie ran parallel to the orchestra") and L14's tool-gating semantics (`allowed_tools` vs `disallowed_tools`).
**Goal**: Spawn your first **subagent** — an isolated sub-task with its own system prompt, tools, and **its own fresh context** — and internalize the single most important discipline in multi-agent work: **a subagent starts with none of the parent's knowledge unless you pass it explicitly.** By the end you'll have run a live delegation, watched the parent hand work down, and *proven to yourself* that the subagent can't see what you didn't give it.

## Why this matters for the exam

This is where **Domain 1's "multi-agent orchestration / subagent delegation" (the 27% domain)** actually begins. L04 gave you the *vocabulary* (orchestrator-workers); L14 gave you *one* configured agent; L15 connects them — one agent spawning others. The guide repeatedly frames the key risk as **context isolation**: subagents are powerful *because* they have clean, separate context (no pollution from the parent's transcript), which is also exactly why you must hand them what they need. Exam scenarios test whether you understand that a subagent that "doesn't know X" is a *design choice you made*, not a bug.

> **This is genuinely new** (L13 flagged subagents as "you haven't built this"). We go ground-up and — per how you learn — we *run it and prove the isolation*, not just assert it.

---

## The one-sentence version

> **A subagent is a second agent the first one can call as a tool. It runs in a clean context window with its own system prompt and tools, and it only knows what the parent puts in the prompt it hands down.**

Everything below unpacks that.

---

## Concept 1 — What a subagent *is* (and why isolation is the point)

In L14 you ran one agent: one system prompt, one context window, one loop. A **subagent** is a *named second agent* that your main agent can invoke mid-loop, the way it invokes any other tool. When it does:

- The subagent gets a **fresh, empty context window** — it does **not** inherit the parent's conversation, system prompt, or tool results.
- It runs its **own** mini agent-loop (its own system prompt, its own tools, possibly its own model) until it finishes.
- It returns **one result** back to the parent, which lands in the parent's context as a tool result — exactly like the `tool_result` blocks you hand-rolled in L02/L06.

**The isolation is the feature, not a limitation.** Two reasons it's valuable, both straight from Domain 1:

1. **Context hygiene.** A research subagent might read 50 files and burn 80k tokens doing it. If that all landed in the parent's context, the parent would be drowning in noise. Instead the subagent does the messy work in *its own* window and returns a clean 200-token summary. The parent's context stays lean. (This is the L13 "context management" row, now concrete.)
2. **Focused behaviour.** Each subagent has a tight, single-purpose system prompt ("you are a haiku poet, output exactly one haiku"), so it behaves more reliably than one mega-agent juggling everything — the same L11 "sharp description → reliable behaviour" idea, applied to a whole agent.

> **L04 callback.** This *is* the **orchestrator-workers** pattern from "Charlie ran parallel to the orchestra." The parent is the orchestrator; subagents are the workers it dispatches. L15 is you building the worker-dispatch machinery for the first time.

---

## Concept 2 — How you define a subagent: `AgentDefinition` + the `agents` field

You declare subagents on the **`agents`** field of `ClaudeAgentOptions` — a dict mapping a **name** to an **`AgentDefinition`**:

```python
from claude_agent_sdk import ClaudeAgentOptions, AgentDefinition

options = ClaudeAgentOptions(
    model="claude-haiku-4-5",
    setting_sources=[],
    allowed_tools=["Task"],          # ← enables the parent to spawn subagents (see Concept 3)
    permission_mode="bypassPermissions",
    agents={
        "haiku-poet": AgentDefinition(
            description="Writes a single haiku on a given topic. Use when the user wants a haiku.",
            prompt="You are a haiku poet. Given a topic, respond with exactly one haiku (5-7-5). Nothing else.",
            tools=[],                # this subagent needs no tools
            model="haiku",
        ),
    },
)
```

Two fields are required and carry all the weight:

- **`description`** — *when should the parent reach for this subagent?* This is the **L11 tool-description skill, one level up.** It's what the parent reads to decide whether to delegate. Vague description → the parent delegates at the wrong times (or never). Sharp, bounded description → reliable delegation. (Yes — the description is to a *subagent* exactly what a tool description is to a *tool*: the selection signal.)
- **`prompt`** — the subagent's **system prompt**, i.e. its identity and behaviour once spawned. This is the L14 `system_prompt` lever, scoped to the worker.

Optional fields you'll use: `tools` (the subagent's tool surface — defaults to inheriting), `model` (give a worker a cheaper or pricier model than the parent), `disallowedTools`, `maxTurns`. (More in later lessons — `mcpServers`, `memory`, `background`.)

---

## Concept 3 — How the parent *spawns* it: the Task / Agent tool

The parent doesn't call your subagent by magic — it calls a **built-in tool** to do delegation. Here's the wrinkle that's worth getting exactly right (and that the exam can probe):

- You **enable** delegation by putting **`"Task"`** in `allowed_tools` (or otherwise permitting it). That's the tool name you grant.
- When the parent actually delegates, the tool call that appears in the message stream is named **`Agent`**, and its input looks like:
  ```python
  {'subagent_type': 'haiku-poet', 'description': '...', 'prompt': 'Write a haiku about the ocean.'}
  ```

So: **you grant `Task`, you observe `Agent`** — same mechanism, and `subagent_type` is how the parent names *which* of your defined subagents to spawn. Don't be thrown by seeing `Agent` in the stream when you allowed `Task`; they're the two faces of subagent delegation.

The single most important field in that tool call is **`prompt`** — the message the parent composes *for* the subagent. **That is the entire bridge between the two context windows.** Which brings us to the discipline this whole lesson exists to teach.

---

## Concept 4 — Explicit context passing (the discipline — proven, not asserted)

Here is the rule, and it is the thing to walk out of L15 knowing cold:

> **The subagent knows ONLY what the parent writes into the `prompt` it hands down. Nothing from the parent's own conversation crosses over automatically.**

This is easy to nod along to and easy to get wrong under exam pressure, so let's **prove it** rather than trust it. Set up a parent that knows a secret, and tell it to delegate *without* passing the secret:

```python
options = ClaudeAgentOptions(
    model="claude-haiku-4-5", setting_sources=[],
    allowed_tools=["Task"], permission_mode="bypassPermissions",
    agents={
        "secret-keeper": AgentDefinition(
            description="Reports what secret word it was told. Use to test context passing.",
            prompt="You are a subagent. State verbatim any secret word you were given in YOUR prompt. "
                   "If you were given no secret, say 'I was given no secret.'",
            tools=[], model="haiku",
        ),
    },
)
# Parent learns the secret in ITS OWN conversation, then is told to delegate without sharing it:
prompt = ("The secret word is BANANA. Now use the secret-keeper subagent to ask it what secret "
          "word it knows. Do NOT tell the subagent the secret yourself.")
```

**Verified output** (real run, `claude-haiku-4-5`):

```
TOOLUSE name=Agent  subagent_prompt='What secret word do you know?'
TEXT: The secret-keeper agent reports that it was given no secret. This is expected—
      the secret "BANANA" was passed to you (in the initial context), not to the agent.
```

Read that carefully. The parent *knew* "BANANA." It spawned the subagent with the prompt `"What secret word do you know?"` — no secret in it. The subagent, in its clean context window, **had no way to know BANANA** and correctly reported it was given no secret. The parent even narrated the reason: *the secret was passed to you, not to the agent.*

**That gap is the entire lesson.** If the subagent needs a fact, an instruction, a file path, a prior result — the parent must put it *in the prompt*. There is no shared memory, no ambient context, no "it'll figure it out." This is what "explicit context passing" means, and it's the discipline that separates working multi-agent systems from ones that mysteriously "forget" things.

> **Why isolation is still the right default.** You might think "wouldn't it be easier if subagents just inherited everything?" No — that's exactly the context-pollution problem from Concept 1. Inheritance would mean every subagent drags the parent's entire (possibly huge) transcript into its window, defeating the purpose. The SDK makes you pass context *on purpose* so that you pass *only what's needed* — keeping each context window lean. The friction is the feature.

---

## Your build

Create `lessons/scripts/subagent_lab.py`. Build a parent agent with **one** subagent and run **two** delegations to feel both sides of the context boundary. Use `model="claude-haiku-4-5"`, `setting_sources=[]`, `allowed_tools=["Task"]`, `permission_mode="bypassPermissions"` throughout (keeps it cheap and lets it run headless).

1. **Define a `summarizer` subagent** via `AgentDefinition`: `description` = "Summarizes a block of text into one sentence. Use when text needs condensing." `prompt` = "You are a summarizer. Given text, return exactly one sentence capturing its core point. Nothing else." `tools=[]`, `model="haiku"`.

2. **Delegation A — pass the context.** Parent prompt: paste a 3–4 sentence paragraph *into the prompt* and say "use the summarizer subagent to condense this." Print the `ToolUseBlock` so you can **see the parent copy your paragraph into the subagent's `prompt`** — that's explicit context passing happening in front of you.

3. **Delegation B — withhold the context (the proof).** Parent prompt: "Earlier I read an article about deep-sea anglerfish. Use the summarizer subagent to summarize that article." — but *don't include the article*. Observe that the subagent can't summarize what it was never given (it'll ask for the text or summarize nothing). This reproduces the Concept-4 result with your own subagent.

4. Print each call's `ResultMessage.total_cost_usd`. Expect a few cents total (each delegation is *two* agent loops — parent + child — so it costs more than a single L14 call; don't loop it).

> Stream-reading helper (you'll want to see tool calls, not just text):
> ```python
> for block in message.content:
>     if isinstance(block, TextBlock):
>         print("TEXT:", block.text)
>     elif type(block).__name__ == "ToolUseBlock":
>         print("DELEGATE →", block.input.get("subagent_type"), "| prompt:", block.input.get("prompt"))
> ```

---

## Exercises

1. **The isolation rule in one sentence.** State precisely what a subagent does and does not have access to from its parent. What is the *single* channel through which the parent gives it information?

2. **Diagnose the bug.** A teammate's research subagent keeps "forgetting" which repository it's supposed to analyze, even though the parent agent clearly knows. The parent's delegation prompt just says "analyze the repo for security issues." What's wrong, and what's the one-line fix?

3. **`description` vs `prompt`.** In an `AgentDefinition`, what question does `description` answer, and what question does `prompt` answer? Map each to the L11 / L14 skill it's the same as, one level up.

4. **Task vs Agent.** You put `"Task"` in `allowed_tools` but in the message stream you see a tool call named `Agent` with a `subagent_type` field. Explain the relationship in one sentence — are these two different tools?

5. **Why not one mega-agent? (L04 callback).** Give two concrete reasons to split a job across a parent + focused subagents instead of cramming everything into one agent with a giant system prompt and every tool. Tie one reason to *context* and one to *behaviour reliability*. Which L04 pattern is this?

6. **Cost intuition.** Why does a single delegation cost more than a single L14 `query()` call, even on the same model? (Hint: count the agent loops that run.)

---

## What you now know

- **A subagent is a second agent invoked as a tool**, running in a **clean, isolated context window** with its own system prompt, tools, and (optionally) model. Isolation is the *feature* — it keeps the parent's context lean (L13 context-management) and each worker focused (L11 sharpness).
- **You define subagents** via the `agents` dict on `ClaudeAgentOptions`, each an **`AgentDefinition(description=..., prompt=...)`**. `description` = *when to delegate* (L11 selection signal); `prompt` = *the worker's system prompt* (L14 identity).
- **You enable delegation** with `"Task"` in `allowed_tools`; the call surfaces in the stream as the **`Agent`** tool with a `subagent_type` naming which subagent to spawn.
- **Explicit context passing is the discipline:** the subagent knows *only* what the parent writes into the handed-down `prompt`. Proven live — a parent that knew "BANANA" but didn't pass it spawned a subagent that genuinely couldn't see it. If the worker needs it, put it in the prompt.
- **This is orchestrator-workers** ("Charlie ran parallel to the orchestra") — parent orchestrates, subagents are the workers.

## Up next

**Lesson 16 — Coordinator/subagent build (orchestrator-workers).** You can now spawn *one* subagent. L16 builds the full pattern: a coordinator that routes different kinds of work to *different specialized* subagents and synthesizes their results — the canonical multi-agent architecture the exam centers Domain 1 on. You'll wire two or three workers (each a focused `AgentDefinition`) under one coordinator and watch it dispatch by task type — explicit context passing, now at scale.

When you've worked through this lesson and the build, tick the box in `lessons/README.md` and tell me you're done — I'll write 16.
