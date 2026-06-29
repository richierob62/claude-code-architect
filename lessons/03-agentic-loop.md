# Lesson 03 — Anatomy of the agentic loop

**Time**: ~15–20 minutes
**Prerequisites**: Lesson 02 complete. You can describe the four-step `tool_use` ↔ `tool_result` round-trip and explain why `tool_result` is a *user*-role message.
**Goal**: Turn Lesson 02's single `if stop_reason == "tool_use"` into a `while`, and watch Claude chain multiple tool calls — using the result of one to shape the next — before finishing with `end_turn`. This loop is the spine of every agent you'll build for the rest of the course.

## Why this matters for the exam

Lesson 02 was the *atom*. This is the *molecule*. Domain 1 (Agentic Architecture, 27%) leans hardest here, and the exam guide is unusually explicit about both the right answer and the wrong ones:

- **Right**: `stop_reason` is the loop condition. Continue while `"tool_use"`, terminate when `"end_turn"`.
- **Wrong** (the exam will tempt you with all three):
  - Parsing the assistant's natural-language text for completion signals ("looks like it said 'done'…").
  - Treating an iteration cap as the *primary* stopping mechanism (caps are safety nets, not termination logic).
  - Checking whether the assistant produced any text content as a "is it done?" heuristic.

Lock the `stop_reason`-as-condition framing now. Lesson 05 is a dedicated tour of the anti-patterns; this lesson is the positive case. (Lesson 04 sits between them — it names the broader catalog of agentic-system patterns the exam draws its vocabulary from.)

## What we're going to do

1. Build a two-tool world where one question genuinely *requires* a chain — Claude must use the output of the first tool to pick the input of the second.
2. Wrap Lesson 02's round-trip in a `while`/`for` driven by `stop_reason`.
3. Watch a multi-iteration chain unfold: `tool_use → tool_use → end_turn`.
4. Verify the negative case still works: a question that needs no tool exits on iteration 1.
5. Be explicit about the safety-net role of `max_iters` — and why it must not be the *reason* the loop ends.

---

## Concept 1 — The loop is just one condition: `stop_reason`

Here's the entire control flow, in pseudocode:

```
messages = [user question]
while True:
    response = claude(messages, tools)

    if response.stop_reason == "end_turn":
        return final text          # ← the ONLY clean exit

    if response.stop_reason == "tool_use":
        append assistant turn to messages
        for each tool_use block:
            run the tool, collect tool_result blocks
        append user(tool_results) to messages
        continue                    # ← keep looping

    # anything else: max_tokens, stop_sequence — handle explicitly
```

Two things to internalize:

- **The loop has exactly one *normal* exit:** `stop_reason == "end_turn"`. Every iteration either exits there or appends results and goes again. That's it. No text inspection, no "did it produce content?" check, no "did it say 'finished'?".
- **`tool_use` is a pause demanding action, not an ending.** This was the takeaway you locked in Lesson 01. The loop's job is to *unblock* that pause by running the tool and feeding the result back, then call again.

## Concept 2 — Why "chain" is the interesting case, not "one call"

Lesson 02's weather example only needed one round-trip. That looks like an agent but isn't really one — it's a single function call wrapped in protocol. The agentic loop earns its name when **Claude has to use the output of an earlier tool to decide what to do next.**

The build below sets up exactly that. Two tools:

- `find_employee_id(name)` → returns an internal id like `"E-1042"`.
- `get_employee_details(employee_id)` → returns role/team/start date, but only accepts an id, not a name.

If you ask "what team does Ada Lovelace work on?", Claude can't skip to `get_employee_details` — it doesn't know Ada's id. It must call `find_employee_id` first, read the result, then call `get_employee_details` with the id it just learned. Three iterations: `tool_use`, `tool_use`, `end_turn`. That's a real loop.

This is the shape of most production agents. A customer-support agent looks up a user, then fetches their orders, then checks shipping status. A code agent reads a file, greps for a symbol, then opens the file the grep pointed at. Same loop, different tools.

## Concept 3 — `max_iters` is a smoke alarm, not a thermostat

Every loop in this lesson and the rest of the course has a `max_iters` ceiling. **It is not how the loop is supposed to end.** It exists because:

- A bug in your tool dispatcher could make Claude retry forever.
- A poorly-described tool could cause Claude to call it, get junk, call it again with slightly different inputs, and never converge.
- A truly stuck model could keep emitting `tool_use` indefinitely.

You want a circuit-breaker, not a clock. If `max_iters` ever *fires*, that's a signal to investigate — log loudly, surface to a human, do not silently return a half-answer. Treat it the way you'd treat the smoke alarm going off: not as a normal end-of-cooking signal, but as evidence something went wrong.

The exam will offer answer choices that frame `max_iters` as the primary termination mechanism. They're wrong. `stop_reason == "end_turn"` is the primary termination mechanism. `max_iters` is the safety net.

---

## Build — multi-step agentic loop, verified

Create `lessons/scripts/agentic_loop.py`:

```python
import json

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# Two tools that force a CHAIN: you must look up an employee's id by name
# before you can fetch their details. One round-trip isn't enough — Claude
# has to use the output of call 1 to shape the input of call 2.
TOOLS = [
    {
        "name": "find_employee_id",
        "description": (
            "Look up an employee's internal ID by their full or partial name. "
            "Returns the id and the full name on file. Use this first when you "
            "have a name but not an id."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Full or partial employee name, e.g. 'Ada' or 'Ada Lovelace'.",
                }
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_employee_details",
        "description": (
            "Fetch role, team, and start date for an employee by their internal ID. "
            "Requires the id from find_employee_id; does not accept names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Internal employee id like 'E-1042'.",
                }
            },
            "required": ["employee_id"],
        },
    },
]

DIRECTORY = {
    "E-1042": {"name": "Ada Lovelace", "role": "Staff Engineer", "team": "Platform", "start": "2021-03-15"},
    "E-2087": {"name": "Alan Turing", "role": "Principal Researcher", "team": "Cryptography", "start": "2019-09-01"},
    "E-3120": {"name": "Grace Hopper", "role": "Director of Compilers", "team": "Languages", "start": "2018-01-08"},
}


def find_employee_id(name: str) -> str:
    needle = name.lower()
    for emp_id, rec in DIRECTORY.items():
        if needle in rec["name"].lower():
            return json.dumps({"id": emp_id, "name": rec["name"]})
    return json.dumps({"error": f"no employee matching {name!r}"})


def get_employee_details(employee_id: str) -> str:
    rec = DIRECTORY.get(employee_id)
    if rec is None:
        return json.dumps({"error": f"unknown employee_id {employee_id!r}"})
    return json.dumps(rec)


# Dispatch table. New tools just go in here.
IMPLEMENTATIONS = {
    "find_employee_id": find_employee_id,
    "get_employee_details": get_employee_details,
}


def run(user_text: str, max_iters: int = 10) -> None:
    """Drive the agentic loop. stop_reason is the loop condition; max_iters
    is a SAFETY NET against runaway behavior, not the primary termination."""
    messages = [{"role": "user", "content": user_text}]
    print(f"\n=== Q: {user_text}")

    for i in range(1, max_iters + 1):
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=600,
            tools=TOOLS,
            messages=messages,
        )
        print(f"[iter {i}] stop_reason={response.stop_reason!r}")

        # End condition: Claude is done. This is the ONLY clean exit.
        if response.stop_reason == "end_turn":
            final = "".join(b.text for b in response.content if b.type == "text")
            print(f"  final: {final}")
            return

        # Anything other than 'tool_use' at this point is unexpected (max_tokens,
        # stop_sequence, etc.). In a real agent you'd handle each explicitly.
        if response.stop_reason != "tool_use":
            print(f"  unexpected stop_reason; aborting")
            return

        # Append the assistant turn verbatim (Lesson 02: tool_use blocks must
        # be in history so tool_result can point at them via tool_use_id).
        messages.append({"role": "assistant", "content": response.content})

        # Execute every tool_use block this turn produced. (Claude can request
        # several at once — a later Module D lesson explores parallel calls in depth.)
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                impl = IMPLEMENTATIONS[block.name]
                output = impl(**block.input)
                print(f"  [exec] {block.name}({block.input}) → {output}")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    }
                )

        # All tool_results for this turn go back in a single user-role message.
        messages.append({"role": "user", "content": tool_results})

    # We only reach here if max_iters fired. This is a BUG SIGNAL, not a
    # normal exit. In production: log loudly, surface to a human.
    print(f"  !! hit max_iters={max_iters} without end_turn — runaway loop")


if __name__ == "__main__":
    run("What team does Ada Lovelace work on, and when did she start?")
    run("Tell me Grace Hopper's role and team.")
    run("What does the acronym 'API' stand for?")
```

Run it:

```bash
uv run python lessons/scripts/agentic_loop.py
```

### What you should see (real output, captured from a live run)

```
=== Q: What team does Ada Lovelace work on, and when did she start?
[iter 1] stop_reason='tool_use'
  [exec] find_employee_id({'name': 'Ada Lovelace'}) → {"id": "E-1042", "name": "Ada Lovelace"}
[iter 2] stop_reason='tool_use'
  [exec] get_employee_details({'employee_id': 'E-1042'}) → {"name": "Ada Lovelace", "role": "Staff Engineer", "team": "Platform", "start": "2021-03-15"}
[iter 3] stop_reason='end_turn'
  final: Based on the information I found:
  - **Team**: Ada Lovelace works on the **Platform** team
  - **Start Date**: She started on **March 15, 2021**

=== Q: Tell me Grace Hopper's role and team.
[iter 1] stop_reason='tool_use'
  [exec] find_employee_id({'name': 'Grace Hopper'}) → {"id": "E-3120", "name": "Grace Hopper"}
[iter 2] stop_reason='tool_use'
  [exec] get_employee_details({'employee_id': 'E-3120'}) → {"name": "Grace Hopper", "role": "Director of Compilers", "team": "Languages", "start": "2018-01-08"}
[iter 3] stop_reason='end_turn'
  final: Grace Hopper's role is **Director of Compilers** and she is on the **Languages** team.

=== Q: What does the acronym 'API' stand for?
[iter 1] stop_reason='end_turn'
  final: The acronym 'API' stands for **Application Programming Interface**. ...
```

Look closely at the first case. Three iterations:

- **iter 1**: Claude doesn't know Ada's id, so it calls `find_employee_id`. `stop_reason='tool_use'`. We run it locally; it returns `E-1042`.
- **iter 2**: Now Claude has the id. It calls `get_employee_details(employee_id='E-1042')` — **the input to call 2 came from the output of call 1.** That's the chain. `stop_reason='tool_use'` again.
- **iter 3**: Claude has everything it needs. It writes the answer using the team and start date from iter 2's result. `stop_reason='end_turn'`. Loop exits.

And the third case — "what does API stand for?" — never enters the tool path at all. `stop_reason='end_turn'` on iter 1. Same loop, zero iterations of tool execution. The control flow handles both shapes without special-casing.

---

## Exercises (do these before moving on)

1. **Watch the chain stretch.** Add a third tool, `list_team_members(team)`, that returns the names on a team. Then ask `run("Who else is on the same team as Ada Lovelace?")`. You should see a three-tool chain: `find_employee_id(Ada)` → `get_employee_details(E-1042)` → `list_team_members(Platform)` → `end_turn`. Four iterations total. The loop body doesn't change — only the dispatch table grows.

2. **Trip the safety net deliberately.** Set `max_iters=1` and re-run the Ada query. You'll see iter 1 ask for a tool, you'll run it, append the result… and then the loop exits without a second iteration. Notice that the function prints the `!! hit max_iters` message — **the user gets no answer**. This is the failure mode the exam wants you to recognize: an iteration cap that fires is a *bug*, not a graceful exit.

3. **Break the anti-pattern intuitively.** In the loop body, comment out the `if response.stop_reason == "end_turn": return` block and replace it with: `if any(b.type == "text" for b in response.content): return`. Run the Ada query. What happens, and *why* is that a wrong way to detect completion? (Hint: assistant turns with `tool_use` often *also* contain a short text block — "Let me look that up." — so the "did it produce text?" heuristic exits the loop before any tools run.)

Then answer in one sentence each:

1. What's the only condition that should normally end the loop?
2. Why is `max_iters` *necessary* but not *sufficient* as a stopping mechanism?
3. Give one reason text-content inspection ("did the assistant write anything?") is a bad completion check.
4. In the chain `find_employee_id → get_employee_details → end_turn`, what specifically did Claude do between iter 1 and iter 2 that justifies calling this a *loop* and not just two independent calls?

---

## What you now know

- The agentic loop has exactly one normal exit: `stop_reason == "end_turn"`.
- `stop_reason == "tool_use"` is the *continue* condition: append the assistant turn, run every `tool_use` block, append the `tool_result`s, call again.
- The interesting work happens when **call N's input depends on call N-1's output** — that's why this is a loop, not a chain of independent functions.
- `max_iters` is a safety net for runaway behavior. If it fires, treat that as a bug to investigate, not a normal termination.
- Anti-patterns to refuse on the exam: text-parsing for completion, iteration caps as the *primary* stopper, checking for any text content as an "is it done?" heuristic.

## Up next

**Lesson 04 — Workflow patterns: the agentic-systems catalog.** You've built one agent. Before we tour the loop anti-patterns (that's Lesson 05), we step back and learn the Anthropic-canonical vocabulary for *every* agentic-system shape: workflow vs. agent, and the five workflow patterns (prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer). Naming the patterns now turns the rest of the course into recognition rather than discovery — and the exam will use these names directly.

When you've worked through this lesson and the exercises, tick the box in `lessons/README.md` and tell me you're done — I'll write 04.
