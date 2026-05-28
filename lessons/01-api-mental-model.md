# Lesson 01 — The Claude API mental model

**Time**: ~15–20 minutes
**Prerequisites**: Lesson 00 complete (`hello.py` runs and returns a response)
**Goal**: Build an accurate mental model of what you're sending to Claude and what comes back — so that every later lesson (tool use, agentic loops, structured output, batches) slots onto a foundation that's actually correct rather than vibes.

## Why this matters for the exam

Most exam mistakes at the Foundations level aren't about exotic features — they're about misunderstanding the shape of the request/response. Specifically:

- Thinking the API is "stateful" (it isn't — every turn you re-send the whole history).
- Thinking `content` is a string (it's a list of typed blocks).
- Thinking `stop_reason` is informational (it isn't — it's the **control signal** that drives every agentic loop you'll build).
- Forgetting that `system` is its own parameter, not a message with `role: "system"`.

Get these four things wired correctly and you've removed ~30% of the cognitive load for the rest of the course.

## What we're going to do

1. Read the shape of a `messages.create()` request — every parameter that matters.
2. Read the shape of the response — `content` blocks, `stop_reason`, `usage`.
3. Run three short scripts that demonstrate each: multi-turn replay, content-block inspection, stop-reason variation.
4. Lock in the mental model with a one-page summary you can re-read before the exam.

---

## Concept 1 — The API is stateless. You replay history every turn.

There is no `conversation_id` on the Claude API. The server keeps no memory of your previous calls. Every time you call `client.messages.create()`, you send the **entire conversation so far** as a flat list of messages.

A multi-turn conversation, from the API's point of view, is just one bigger list:

```python
# Turn 1
messages = [
    {"role": "user", "content": "What's the capital of France?"},
]
# → response: "Paris."

# Turn 2 — you append BOTH the assistant's reply AND the new user message
messages = [
    {"role": "user", "content": "What's the capital of France?"},
    {"role": "assistant", "content": "Paris."},
    {"role": "user", "content": "And of Germany?"},
]
# → response: "Berlin."
```

Two consequences worth internalizing:

- **You own the memory.** If you don't append the assistant's reply to `messages`, Claude has no idea what it just said. Most "Claude forgot what we were talking about" bugs are forgotten-append bugs.
- **Cost scales with history.** Every token in `messages` is re-tokenized and re-billed every turn (modulo prompt caching, which we'll meet in Module G).

### Role alternation rule

Messages must alternate `user` → `assistant` → `user` → `assistant`. You cannot send two `user` messages in a row, and you cannot start with `assistant`. The first message must be `user`.

(Tool use will look like it violates this — it doesn't, because the tool result is wrapped as a `user`-role message containing a `tool_result` block. We'll meet that in Lesson 02.)

## Concept 2 — `system` is a separate top-level parameter

The system prompt is **not** a message. It's its own argument:

```python
client.messages.create(
    model="claude-haiku-4-5",
    system="You are a terse assistant. Reply in five words or fewer.",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=100,
)
```

This trips people up because OpenAI's API uses `{"role": "system", "content": "..."}` inside the messages list. Anthropic's doesn't. If you try the OpenAI shape against Claude, you'll get an error.

Why does it matter? Because `system` is also where prompt caching's biggest wins live — large system prompts can be cached and reused across calls. (We'll cover caching in Module G; remember now that `system` is structurally distinct from `messages`.)

## Concept 3 — `content` is a list of typed blocks, not a string

The shorthand `content: "Hello!"` you've been using is sugar. The full shape is:

```python
{"role": "user", "content": [
    {"type": "text", "text": "Hello!"},
]}
```

On the response side, `message.content` is **always** a list. The block types you'll see this course:

| Block type    | Where it appears                    | What it carries                                         |
| ------------- | ----------------------------------- | ------------------------------------------------------- |
| `text`        | request + response                  | Plain text                                              |
| `image`       | request (user msg)                  | Base64 or URL-referenced image                          |
| `tool_use`    | response                            | Claude wants to call a tool — has `id`, `name`, `input` |
| `tool_result` | request (user msg)                  | Your tool's output — references the `tool_use_id`       |
| `thinking`    | response (extended thinking models) | Reasoning trace                                         |

A single assistant response can contain **multiple blocks** — e.g., a `text` block followed by a `tool_use` block ("I'll look that up. <calls search>"). You have to iterate the list; you can't assume `content[0]` is what you want.

The SDK returns these as typed Python objects (`TextBlock`, `ToolUseBlock`, etc.), so you can `isinstance()` check them.

## Concept 4 — `stop_reason` is the control signal for everything that comes after

When a response comes back, `message.stop_reason` tells you **why Claude stopped generating**. In an agentic loop, this is the value you branch on to decide what to do next. Memorize this table — it appears (in disguise) on the exam.

| `stop_reason`     | What it means                                                                          | What you do next                                                                                                                                   |
| ----------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `"end_turn"`      | Claude is done with this turn. Natural finish.                                         | Return the response to the user. The conversation is at rest.                                                                                      |
| `"max_tokens"`    | Hit the `max_tokens` limit you passed in. Output is **truncated mid-token**.           | Either accept truncation, retry with higher `max_tokens`, or (advanced) continue with a follow-up "please continue" turn.                          |
| `"stop_sequence"` | Hit one of the strings in `stop_sequences=[...]`.                                      | Custom-flow specific — you set the stop sequence, so you know what to do.                                                                          |
| `"tool_use"`      | Claude wants to call one or more tools. The `content` list contains `tool_use` blocks. | Execute the tool(s), append a `user` message with `tool_result` blocks, call the API again. **This is the heart of the agentic loop** (Lesson 03). |
| `"pause_turn"`    | Long-running operation (server tools, code execution) needs to be resumed.             | Re-call the API with the same messages list to resume.                                                                                             |
| `"refusal"`       | Claude declined for safety reasons.                                                    | Surface the refusal; do not retry-on-loop blindly.                                                                                                 |

The single most important takeaway: **`stop_reason: "tool_use"` is not the end of the response — it's a mid-flight pause that demands action from you before continuing.** Every agent you build is a `while stop_reason == "tool_use": …` loop in disguise.

## Concept 5 — `usage` is how you know what you spent

Every response includes a `usage` block:

```python
{
  "input_tokens": 42,
  "output_tokens": 17,
  "cache_creation_input_tokens": 0,
  "cache_read_input_tokens": 0,
}
```

You should look at this once per script during the course so cost stays concrete. Haiku 4.5 input is ~$1/MTok, output ~$5/MTok — your $3 budget is roughly **3M input + 600K output tokens**. You will not come close to that. But knowing where the numbers come from matters.

---

## Build 1 — Multi-turn replay

Create `lessons/scripts/multi_turn.py`:

```python
import json

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

messages = []

def ask(user_text: str) -> str:
    messages.append({"role": "user", "content": user_text})
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        messages=messages,
    )
    # Extract the assistant's reply text and append it as the next turn.
    reply_text = response.content[0].text
    messages.append({"role": "assistant", "content": reply_text})
    return reply_text

print("Turn 1:", ask("My name is Rich. Remember it."))
print("Turn 2:", ask("What's 2 + 2?"))
print("Turn 3:", ask("What's my name?"))

print(f"\nFinal messages list has {len(messages)} entries.")
print("\nFull messages list:")
print(json.dumps(messages, indent=2))

```

Run it:

```bash
uv run python lessons/scripts/multi_turn.py
```

You should see Claude correctly recall "Rich" on turn 3 — because every prior turn is in the `messages` list you replay on each call.

Now prove the opposite. Add a second function that sends **only the current turn**, with no accumulated history:

```python
def ask_stateless(user_text: str) -> str:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": user_text}],
    )
    return response.content[0].text

print("\n--- Stateless (no replay) ---")
print("Turn 1:", ask_stateless("My name is Rich. Remember it."))
print("Turn 3:", ask_stateless("What's my name?"))
```

This time Claude has no idea who you are on the second call — each request is a blank slate. The only thing that made the first version "remember" was *you* feeding the history back.

> A common trap: commenting out only the `messages.append({"role": "assistant", ...})` line does **not** make Claude forget — the `user` turns are still appended at the top of `ask()`, so "My name is Rich" remains in the replayed history. Dropping just the assistant side gives you a malformed transcript (user/user/user), not statelessness. To actually erase memory you must stop replaying *all* prior turns, as `ask_stateless` does.

**That's statelessness in action.** The API holds nothing between calls; the context is whatever you send. Internalize it.

## Build 2 — Inspect content blocks

Create `lessons/scripts/inspect_blocks.py`:

```python
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=300,
    messages=[{"role": "user", "content": "Say hi in one short sentence."}],
)

print(f"stop_reason: {response.stop_reason}")
print(f"usage: {response.usage}")
print(f"content is a {type(response.content).__name__} with {len(response.content)} block(s):")
for i, block in enumerate(response.content):
    print(f"  [{i}] type={type(block).__name__} → {block!r}")
```

Run it. Notice:

- `content` is a `list`, not a string.
- `content[0]` is a `TextBlock`, which has a `.text` attribute.
- `stop_reason` is `"end_turn"` — natural finish.
- `usage` shows input + output tokens (single-digit and tens, respectively).

## Build 3 — Force every `stop_reason` you can without tools

Create `lessons/scripts/stop_reasons.py`:

```python
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

def show(label: str, **kwargs):
    response = client.messages.create(model="claude-haiku-4-5", **kwargs)
    print(f"{label}: stop_reason={response.stop_reason!r}, output_tokens={response.usage.output_tokens}")

# 1. Natural finish → "end_turn"
show(
    "end_turn",
    max_tokens=500,
    messages=[{"role": "user", "content": "Reply with exactly: OK"}],
)

# 2. Truncation → "max_tokens"
show(
    "max_tokens",
    max_tokens=5,  # absurdly low, will truncate
    messages=[{"role": "user", "content": "Write a 200-word essay about clouds."}],
)

# 3. Custom stop sequence → "stop_sequence"
show(
    "stop_sequence",
    max_tokens=500,
    stop_sequences=["STOP_HERE"],
    messages=[{"role": "user", "content": "Count: 1, 2, 3, STOP_HERE, 4, 5."}],
)
```

Run it. You should see three different `stop_reason` values. The `"tool_use"` and `"pause_turn"` values require tool definitions (Lesson 02) and server tools (later) — but the three above are enough to prove the mechanism.

---

## Exercise (do this before moving on)

Modify `multi_turn.py` so that **after the third turn**, it prints `response.stop_reason` and `response.usage.input_tokens`. Watch how `input_tokens` grows turn over turn — that's you paying to re-send the whole history every time.

Write down (on paper, in `scratch-pad.md`, wherever) a one-sentence answer to each:

1. Why isn't there a `conversation_id` on the Claude API?
2. What's the difference between `"end_turn"` and `"tool_use"` in an agentic-loop context?
3. Where does the system prompt go — and where does it _not_ go?
4. If `response.content` has length 2, what's the most likely reason?

If any of those four feel shaky, re-read the matching concept block above before going on.

---

## What you now know

- The Claude API is stateless; you own the conversation history.
- `system` is a top-level parameter, not a `messages` entry.
- `content` is always a list of typed blocks (`text`, `tool_use`, `tool_result`, …).
- `stop_reason` is the control signal that drives every agentic loop.
- `usage` tells you what you spent; Haiku at this scale is essentially free.

## Up next

**Lesson 02 — Tool use basics: the `tool_use` ↔ `tool_result` dance.** You'll define a tool, watch Claude emit a `tool_use` block with `stop_reason: "tool_use"`, execute it locally, send the result back as a `tool_result` block in a `user` message, and observe Claude finishing the turn with `stop_reason: "end_turn"`. That's the loop. Everything in Module B is variations on that pattern.

When you've worked through this lesson and finished the exercise, tick the box in `lessons/README.md` and tell me you're done — I'll write 02.
