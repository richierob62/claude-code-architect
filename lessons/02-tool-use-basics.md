# Lesson 02 — Tool use basics: the `tool_use` ↔ `tool_result` dance

**Time**: ~15–20 minutes
**Prerequisites**: Lesson 01 complete (you understand `stop_reason`, that `content` is a list of blocks, and that the API is stateless).
**Goal**: Watch Claude request a tool, execute it locally, feed the result back, and watch Claude finish. This one round-trip is the atom that every agent in Module B is built from.

## Why this matters for the exam

Tool use is the mechanism behind **Domain 1 (Agentic Architecture, 27%)** and **Domain 4's structured output (20%)**. If you understand the four-step round-trip cold, those two domains stop being mysterious. The specific things the exam probes:

- Who actually runs the tool. (You do. Claude only *requests* it.)
- The role-alternation sleight of hand: tool results come back as a **`user`** message, not an `assistant` or `system` one.
- That `tool_use_id` is the thread that ties a request to its result — drop it and the API rejects the turn.
- That `stop_reason: "tool_use"` is a *pause demanding action*, not an ending (the takeaway you locked in Lesson 01).

## What we're going to do

1. Declare a tool as a JSON-Schema contract.
2. Send it with a question that needs it, and read the `tool_use` block that comes back.
3. Execute the tool locally and package the answer as a `tool_result` block.
4. Send that back and watch Claude finish with `end_turn`.
5. Prove the negative: a question that *doesn't* need the tool skips the whole dance.

---

## Concept 1 — A tool is a contract, not code Claude runs

When you pass `tools=[...]`, you are handing Claude a **menu of function signatures** described in JSON Schema. Claude reads the menu and decides, per turn, whether calling something would help. It never executes anything — it emits a *request* (`tool_use` block) describing the call it wants, and hands control back to you.

A tool definition has exactly three top-level fields:

```python
{
    "name": "get_weather",                 # how Claude refers to it
    "description": "Get the current temperature for a city, in Celsius.",
    "input_schema": {                      # JSON Schema for the arguments
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name, e.g. 'Paris'."}
        },
        "required": ["city"],
    },
}
```

Two fields do almost all the work:

- **`description`** — this is *prompt engineering*, not documentation. It's how Claude decides *when* to reach for the tool. A vague description gets a tool that fires at the wrong times or not at all. (Lesson 10 is an entire lesson on writing these well.)
- **`input_schema`** — a standard JSON Schema object. `required` lists the must-have fields; everything else is optional. Claude shapes its arguments to fit this schema.

The `description` of the *whole tool* and the `description` of each *property* are both read by Claude. Use both.

## Concept 2 — The four-step round-trip

Here is the entire dance. Memorize the four steps; everything in Module B is a loop around them.

```
1. SEND      user message + tools  ─────────────►  Claude
2. RECEIVE   ◄──── assistant message, stop_reason="tool_use", contains tool_use block(s)
                   { id, name, input }
   ── you execute the tool locally ──
3. SEND      user message containing tool_result block(s) ──►  Claude
                   { tool_use_id, content }
4. RECEIVE   ◄──── assistant message, stop_reason="end_turn", the final text answer
```

The crucial, non-obvious points:

- **Step 2's assistant message must be appended to history verbatim** — including the `tool_use` block with its `id`. If you don't, step 3's `tool_result` has nothing to point at and the API errors.
- **Step 3 is a `user`-role message.** This is the role-alternation trick from Lesson 01: the sequence is `user → assistant(tool_use) → user(tool_result) → assistant(end_turn)`. Alternation is preserved because the tool result is *wrapped* as a user turn. It is **never** a `system` message and never an `assistant` message.
- **`tool_use_id` is the join key.** The `tool_result` block carries `tool_use_id` equal to the `id` from the `tool_use` block. With parallel tool calls (Lesson 16) you'll have several of each, and the IDs are how they pair up.

## Concept 3 — Claude decides whether to call at all

Passing `tools` doesn't force a call. For a question the model can answer directly, it just… answers — `stop_reason` comes back `"end_turn"` on the first call and there's no tool round-trip. You only do steps 3–4 when `stop_reason == "tool_use"`.

That branch — `if stop_reason == "tool_use": …` — is the seed of the agentic loop. In Lesson 03 we turn the single `if` into a `while` so Claude can chain several tool calls before finishing. (And in Lesson 07 you'll learn `tool_choice` to *force* or *forbid* tool use when you need to override Claude's judgment.)

---

## Build — the full dance, verified

Create `lessons/scripts/tool_use.py`:

```python
import json

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# 1. Declare the tool. This is a JSON-Schema contract Claude reads to decide
#    WHEN to call and HOW to shape the arguments. Claude never runs it — you do.
TOOLS = [
    {
        "name": "get_weather",
        "description": "Get the current temperature for a city, in Celsius.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name, e.g. 'Paris' or 'Tokyo'.",
                }
            },
            "required": ["city"],
        },
    }
]


# 2. The actual implementation. Hard-coded fake data — the point is the
#    protocol, not a real weather API.
def get_weather(city: str) -> str:
    fake = {"paris": 14, "tokyo": 21, "lagos": 31}
    temp = fake.get(city.lower())
    if temp is None:
        return json.dumps({"error": f"no data for {city}"})
    return json.dumps({"city": city, "temp_c": temp})


def run(user_text: str) -> None:
    messages = [{"role": "user", "content": user_text}]

    # --- First call: Claude sees the tools and decides to use one. ---
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=400,
        tools=TOOLS,
        messages=messages,
    )
    print(f"\n=== Q: {user_text}")
    print(f"[call 1] stop_reason={response.stop_reason!r}")
    for block in response.content:
        print(f"  block: type={block.type!r} → {block!r}")

    # If Claude didn't ask for a tool, we're already done.
    if response.stop_reason != "tool_use":
        print("Claude answered without a tool. Done.")
        return

    # 3. Append the assistant turn VERBATIM. The tool_use block (with its id)
    #    must be in the history so the tool_result can reference it.
    messages.append({"role": "assistant", "content": response.content})

    # 4. Execute every tool_use block and collect tool_result blocks.
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            output = get_weather(**block.input)
            print(f"  [local exec] get_weather({block.input}) → {output}")
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,  # ties result to the request
                    "content": output,
                }
            )

    # 5. The tool results go back as a USER-role message. This is why tool use
    #    doesn't break role alternation: user → assistant(tool_use) → user(tool_result).
    messages.append({"role": "user", "content": tool_results})

    # --- Second call: Claude reads the result and finishes the turn. ---
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=400,
        tools=TOOLS,
        messages=messages,
    )
    print(f"[call 2] stop_reason={response.stop_reason!r}")
    final_text = "".join(b.text for b in response.content if b.type == "text")
    print(f"  final answer: {final_text}")


if __name__ == "__main__":
    # A: needs the tool → stop_reason 'tool_use' on call 1, 'end_turn' on call 2.
    run("What's the weather in Tokyo right now?")
    # B: no tool needed → stop_reason 'end_turn' on call 1, no second call.
    run("What is 2 + 2?")
```

Run it:

```bash
uv run python lessons/scripts/tool_use.py
```

### What you should see (this is real output, not aspirational)

```
=== Q: What's the weather in Tokyo right now?
[call 1] stop_reason='tool_use'
  block: type='tool_use' → ToolUseBlock(id='toolu_01H3uQ...', input={'city': 'Tokyo'}, name='get_weather', type='tool_use')
  [local exec] get_weather({'city': 'Tokyo'}) → {"city": "Tokyo", "temp_c": 21}
[call 2] stop_reason='end_turn'
  final answer: The current temperature in Tokyo is **21°C** (approximately 70°F).

=== Q: What is 2 + 2?
[call 1] stop_reason='end_turn'
  block: type='text' → TextBlock(... text="2 + 2 = 4 ...", type='text')
Claude answered without a tool. Done.
```

Read across the two cases:

- **Weather query** runs the full four-step dance. Call 1 stops with `tool_use` and carries a `ToolUseBlock` whose `input` is the arguments Claude chose (`{'city': 'Tokyo'}`). You execute locally, get `temp_c: 21`, send it back, and call 2 finishes with `end_turn` — and notice the final answer *uses your data* (21°C), proving the result actually reached Claude.
- **Arithmetic query** never touches the tool. Call 1 returns `end_turn` directly. The `if stop_reason != "tool_use"` branch short-circuits and there's no second call. Passing `tools` is an *offer*, not a *command*.

---

## Exercises (do these before moving on)

1. **Break the join.** Change `"tool_use_id": block.id` to a bogus string like `"tool_use_id": "nope"`. Re-run. You should get an API error — the `tool_result` can't be matched to any `tool_use`. This is *why* you append the assistant turn verbatim. Put it back when you've seen the error.

2. **Force a different branch.** Ask `run("What's the weather in Reykjavik?")`. Reykjavik isn't in the fake dict, so `get_weather` returns `{"error": ...}`. Watch what Claude does on call 2 with an error payload — it still finishes with `end_turn`, but the answer changes. (This previews Lesson 06: *structured* errors so Claude can react intelligently instead of guessing.)

3. **Drop the verbatim append.** Comment out `messages.append({"role": "assistant", "content": response.content})` and re-run the weather case. Observe the failure mode. This isolates exactly why step 2's append is mandatory — analogous to the statelessness trap from Lesson 01, where the variable you remove has to be the *right* one for the demo to mean anything.

Then answer in one sentence each:

1. Who executes the tool — Claude or your code?
2. What role does the `tool_result` message carry, and why doesn't that break alternation?
3. What field ties a `tool_result` to the `tool_use` that requested it?
4. If you pass `tools` but ask a question Claude can answer directly, what `stop_reason` do you get and how many API calls happen?

---

## What you now know

- A tool is a JSON-Schema **contract** (`name`, `description`, `input_schema`); Claude requests, you execute.
- The four-step round-trip: send+tools → `tool_use` → execute+`tool_result` → `end_turn`.
- `tool_result` is a **`user`**-role message; alternation is preserved by wrapping.
- `tool_use_id` is the join key; the assistant `tool_use` turn must be appended verbatim.
- Passing `tools` is an offer — Claude answers directly (and returns `end_turn`) when no tool is needed.

## Up next

**Lesson 03 — Anatomy of the agentic loop.** We turn today's single `if stop_reason == "tool_use"` into a `while`, so Claude can chain multiple tool calls — look something up, use the result to decide the next call, and only then finish. That loop, with `stop_reason` as its condition, is the spine of every agent in Module B.

When you've worked through this lesson and the exercises, tick the box in `lessons/README.md` and tell me you're done — I'll write 03.
