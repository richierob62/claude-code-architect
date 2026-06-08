# Lesson 08 — `tool_choice`: `auto` vs `any` vs forced

**Time**: ~15 minutes
**Prerequisites**: Lesson 03 (the agentic loop — you know `stop_reason` is `tool_use` or `end_turn`). Lesson 07 (structured tool results). Lesson 02 (the `tool_use` content block — `id` / `name` / `input`).
**Goal**: Learn the **fourth knob** on `client.messages.create` that you've been letting default this whole time: `tool_choice`. It has three modes — `auto`, `any`, and forced — and the choice between them is the difference between "the model is an agent that decides" and "the model is a structured-output function I'm calling." This closes Module B and is the bridge into Module F (structured extraction).

## Why this matters for the exam

`tool_choice` shows up in **two** domains, which is why it gets its own lesson:

- **Domain 2 (Tool Design & MCP, 18%)** — Task Statement 2.3, *"Distribute tools appropriately across agents and configure tool choice."* The exam lists, almost verbatim:
  - **`tool_choice` configuration options**: `"auto"`, `"any"`, and forced selection (`{"type": "tool", "name": "..."}`).
  - **Forced selection to ensure a specific tool is called first** — e.g. forcing `extract_metadata` before enrichment tools run, then handling the rest in follow-up turns.
  - **`"any"` to guarantee the model calls a tool** rather than returning conversational text.
- **Domain 4 (Prompt Engineering & Structured Output, 20%)** — Task Statement 4.3, *"Enforce structured output using tool use and JSON schemas."* The exam draws the line precisely:
  - **`"auto"`**: the model *may* return text instead of calling a tool.
  - **`"any"`**: the model *must* call a tool, but can choose which.
  - **forced**: the model *must* call a *specific named* tool.
  - **`"any"` to guarantee structured output** when several extraction schemas exist and you don't yet know the document type.
  - **forced** `{"type": "tool", "name": "extract_metadata"}` to ensure a particular extraction runs.

If a scenario asks *"how do you guarantee the model returns JSON and never prose?"* the answer is **`tool_choice: "any"` (or forced) with the schema as a tool** — not "ask nicely in the prompt." This lesson makes you watch the three modes diverge on the *same* input.

---

## Concept — the three modes

`tool_choice` is an optional field on `messages.create`. It controls **whether** and **which** tool the model must call. When you omit it, you get `auto`. That's why your L03–L07 loops "just worked" — `auto` is the agentic default.

| Mode | Shape | Model's freedom | `stop_reason` you'll see |
|---|---|---|---|
| **auto** (default) | `{"type": "auto"}` or omit | call any tool, **or** none (return text) | `tool_use` *or* `end_turn` |
| **any** | `{"type": "any"}` | **must** call a tool — its choice which | always `tool_use` (first turn) |
| **forced** | `{"type": "tool", "name": "X"}` | **must** call tool `X`, no choice | always `tool_use`, always `X` |

Three things to nail down, because the exam tests each:

1. **`auto` permits text.** The model looks at the request and *decides* whether a tool is even needed. "Hi, how are you?" → it answers in prose, `stop_reason="end_turn"`, no tool call. This is what you want for an **agent**: it should be free to just talk when no tool applies.

2. **`any` forbids text on that turn.** The model is *compelled* to emit a `tool_use` block. It still picks which tool — useful when you have several extraction schemas and want "use whichever fits," but you never want a chatty "Sure, here's the data:" preamble. `stop_reason` is `tool_use`, guaranteed.

3. **forced removes even the which-tool choice.** `{"type": "tool", "name": "extract_invoice"}` means *that* tool runs, this turn, period. Use it when exactly one structured shape is correct and you want to guarantee it — or to force a *specific first step* (extract before enrich) and handle the rest in later turns.

> **The mental flip**: with `auto` you're running an **agent** (it decides). With `any`/forced you're calling the model as a **function** that is guaranteed to return structured output. Same API, two completely different use-cases — and the exam wants you to know which knob picks which.

### The gotcha: forced/any + a one-shot loop

There's a trap worth seeing now so it doesn't bite you in Module F. If you set `tool_choice` to `any` or forced and then run your **normal agentic loop**, the model is compelled to call a tool **every turn** — including the turn *after* you hand back the tool result. It can loop forever calling the tool again and again, because "stop and summarise in prose" (which needs an `end_turn` text turn) is exactly what `any`/forced forbids.

So the rule: **forced/`any` is for a single structured extraction, not for driving a multi-step agent loop.** You call once, read the `tool_use.input` (that *is* your structured data), and you're done — you don't feed the result back and continue. If you genuinely need "force the first tool, then let the agent run free," you set forced on the **first** call only, then switch back to `auto` for the follow-ups. We'll demonstrate both halves.

---

## Build — watch the three modes diverge on one input

We'll use a single extraction tool, `record_sentiment`, and send the **same** user message under all three `tool_choice` settings, plus a neutral "just chatting" message to show what `auto` does that `any` won't.

Create `lessons/scripts/tool_choice.py`:

```python
"""Lesson 08 — tool_choice: auto vs any vs forced, on one input.

We send the SAME message under each mode and watch stop_reason + whether a
tool was called. Then we show the forced-first-step-then-auto pattern.
"""

import json

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# One extraction tool. Its input_schema IS the structured-output shape we want.
TOOLS = [
    {
        "name": "record_sentiment",
        "description": "Record the sentiment of a customer message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "negative", "neutral"],
                },
                "intensity": {
                    "type": "integer",
                    "description": "1 (mild) to 5 (strong).",
                },
            },
            "required": ["sentiment", "intensity"],
        },
    }
]


def ask(user_text: str, tool_choice: dict, label: str) -> None:
    """One single-turn call. Print stop_reason and whether a tool was called.
    We do NOT loop or feed results back — this lesson is about the FIRST turn."""
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        tools=TOOLS,
        tool_choice=tool_choice,
        messages=[{"role": "user", "content": user_text}],
    )
    tool_calls = [b for b in response.content if b.type == "tool_use"]
    text = "".join(b.text for b in response.content if b.type == "text")
    print(f"\n--- {label}: tool_choice={tool_choice}")
    print(f"    user: {user_text!r}")
    print(f"    stop_reason={response.stop_reason!r}  tools_called={len(tool_calls)}")
    if tool_calls:
        print(f"    -> {tool_calls[0].name}({json.dumps(tool_calls[0].input)})")
    if text:
        print(f"    text: {text!r}")


if __name__ == "__main__":
    angry = "This is the third time my order arrived broken. I am furious."
    chitchat = "Hey, thanks so much, you've been really helpful today!"
    neutral_q = "What time do you close on Saturdays?"

    # 1. auto on a clearly-extractable message: model CHOOSES to call the tool.
    ask(angry, {"type": "auto"}, "AUTO + extractable")

    # 2. auto on a question the tool can't answer: model returns TEXT, no tool.
    ask(neutral_q, {"type": "auto"}, "AUTO + non-extractable")

    # 3. any: model MUST call a tool (it has only one, so it calls that one).
    ask(chitchat, {"type": "any"}, "ANY")

    # 4. forced: model MUST call record_sentiment by name, this turn.
    ask(neutral_q, {"type": "tool", "name": "record_sentiment"}, "FORCED")
```

Run it:

```bash
uv run python lessons/scripts/tool_choice.py
```

### What you should see (real output, captured from a live run)

```
--- AUTO + extractable: tool_choice={'type': 'auto'}
    user: 'This is the third time my order arrived broken. I am furious.'
    stop_reason='tool_use'  tools_called=1
    -> record_sentiment({"sentiment": "negative", "intensity": 5})
    text: 'I can hear your frustration, and rightfully so. Having items arrive broken multiple times is incredibly aggravating.'

--- AUTO + non-extractable: tool_choice={'type': 'auto'}
    user: 'What time do you close on Saturdays?'
    stop_reason='end_turn'  tools_called=0
    text: "I don't have access to information about your store's Saturday hours. To get accurate hours, I'd recommend checking the store's website, calling them directly, or looking at their listing on Google or another directory."

--- ANY: tool_choice={'type': 'any'}
    user: 'Hey, thanks so much, you've been really helpful today!'
    stop_reason='tool_use'  tools_called=1
    -> record_sentiment({"sentiment": "positive", "intensity": 4})

--- FORCED: tool_choice={'type': 'tool', 'name': 'record_sentiment'}
    user: 'What time do you close on Saturdays?'
    stop_reason='tool_use'  tools_called=1
    -> record_sentiment({"sentiment": "neutral", "intensity": 1})
```

*(The `stop_reason` and `tools_called` columns are deterministic per mode — that's the whole point. The exact `sentiment`/`intensity` values and the free-text are model output and will vary run-to-run. Note row 1: under `auto`, the model emitted a `text` block **and** a `tool_use` block in the same turn — it narrated while calling the tool. That's normal: a turn can hold multiple content blocks (your L02 discriminated-union insight). `stop_reason` is still `tool_use` because at least one tool was called; if your run omits the chatty text, that's fine too.)*

### Read what happened — line by line

This output **is** the lesson. Walk the four rows against the table:

- **AUTO + extractable** → `stop_reason='tool_use'`. The model *chose* to call the tool because the message was obviously sentiment-bearing. Nobody forced it; `auto` let it decide, and it decided correctly.

- **AUTO + non-extractable** → `stop_reason='end_turn'`, **zero tools called**, prose instead. This is the row that defines `auto`: faced with a question the sentiment tool can't answer, the model **declined to call any tool** and answered in text. *This is the behaviour you want in an agent* — and it's exactly the behaviour `any`/forced would have destroyed.

- **ANY** → `stop_reason='tool_use'`, one tool call — *even though the message was just a thank-you*. Under `auto` the model might well have just said "you're welcome!" in prose. `any` **forbade** that: it had to call a tool, so it recorded the (positive) sentiment. You guaranteed structured output at the cost of the model's freedom to stay silent.

- **FORCED** → `stop_reason='tool_use'`, `record_sentiment` called **on a message about store hours**. This is the most revealing row: the input has *no real sentiment*, but forced gave the model no out — it had to call `record_sentiment`, so it did, landing on `neutral / 1`. **That's the double edge of forcing**: you get a guaranteed `record_sentiment` call, but you also forced a square peg into a round hole. Force a tool only when you're *sure* the tool applies.

The single takeaway: **`auto` can end in `end_turn` with no tool; `any` and forced cannot.** That one fact answers most exam questions on this topic.

---

## The forced-first-then-auto pattern (the exam's "extract before enrich")

The exam specifically calls out *"forcing `extract_metadata` before enrichment tools, then processing subsequent steps in follow-up turns."* That's a **two-phase** shape:

1. **Turn 1**: `tool_choice={"type": "tool", "name": "extract_metadata"}` — guarantee the extraction runs *first*, before anything else.
2. **Turn 2+**: switch `tool_choice` back to `{"type": "auto"}` — now the agent is free to call enrichment tools, or stop and summarise.

The key insight: **`tool_choice` is per-call, not per-conversation.** You can change it between turns. Forcing the first step doesn't lock you into forcing every step. This is how you reconcile "I need a guaranteed first action" with "but then I want a real agent loop" — and it sidesteps the infinite-loop gotcha from the concept section, because only turn 1 is forced.

You don't need to build the full two-phase loop now (Module F does), but hold the shape: **force turn 1, `auto` after.**

---

## Exercises (do these before moving on)

1. **Reproduce the infinite-loop gotcha (then stop it).** Take your L07 `agent` loop (the multi-turn one) and add `tool_choice={"type": "any"}` to the `messages.create` call. Run any scenario. Watch it call a tool every single turn and never reach `end_turn` — it'll hit `max_iters`. Write one sentence explaining *why* `any` + a feed-the-result-back loop can't terminate normally. Then revert.

2. **Force the wrong tool.** Add a second tool to `tool_choice.py` — say `record_topic` (enum of `billing`/`shipping`/`technical`). Send the angry-order message with `tool_choice={"type": "tool", "name": "record_topic"}`. Confirm the model calls `record_topic` (not `record_sentiment`) even though sentiment was the more obvious read. One sentence: what does this prove about forced vs `any`?

3. **`any` with two tools.** Same two tools, but `tool_choice={"type": "any"}`, on the angry-order message. Which tool does the model pick? Run it twice. (This is the "several extraction schemas, let the model choose which fits" case from Domain 4.)

Then answer in one sentence each:

1. Under which mode(s) can `stop_reason` come back as `end_turn` on the first turn — and why does that single fact matter for choosing a mode?
2. You have three extraction schemas (`extract_invoice`, `extract_receipt`, `extract_statement`) and an unknown document. Which `tool_choice` mode, and why not the other two?
3. Why is `any`/forced a poor fit for driving a multi-step agent loop, and what's the one-line fix when you *do* need to force the first step of such a loop?
4. The forced row in the build called `record_sentiment` on a store-hours question and got `neutral / 1`. In one phrase, what's the risk of forcing a tool that may not apply to the input?

---

## What you now know

- **`tool_choice` has three modes**: `auto` (model decides whether to call a tool, *may* return text → can end in `end_turn`), `any` (must call *some* tool → always `tool_use`), forced `{"type": "tool", "name": "X"}` (must call *that* tool).
- **The agent-vs-function flip**: `auto` runs an agent that decides; `any`/forced call the model as a guaranteed structured-output function. The exam's "guarantee structured output / never return prose" answer is `any` or forced **with the schema as a tool**.
- **`any` for "must extract, model picks which schema"; forced for "must run this exact schema."** Both eliminate the chatty-preamble failure mode.
- **`tool_choice` is per-call.** Force the first step (`extract before enrich`), then switch to `auto` — that's the exam's two-phase pattern and the fix for the forced-loop-never-terminates gotcha.
- **The cost of forcing**: a forced tool runs even when it doesn't fit the input (square peg, round hole). Force only when you're confident the tool applies.

## Up next

That closes **Module B — Agentic Loops**. You can now build a real agentic loop end to end: the loop skeleton (L03), the right way to terminate it (L05), a working multi-tool agent (L06), structured errors it can recover from (L07), and the `tool_choice` knob that switches it between "agent" and "guaranteed structured output" (L08).

**Module C — MCP Deep Dive** is next: **Lesson 09 — the MCP mental model** (tools vs resources, and the protocol underneath the `.mcp.json` you already use as a consumer). Everything you've learned about tool *shape* (L02), *output* (L07), and *choice* (L08) now gets repackaged as an MCP server you author yourself.

When you've worked through this lesson and the exercises, tick the box in `lessons/README.md` and tell me you're done — I'll write 09.
