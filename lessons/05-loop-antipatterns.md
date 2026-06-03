# Lesson 05 — Loop anti-patterns: the three wrong ways to end an agent

**Time**: ~15 minutes
**Prerequisites**: Lesson 03 (you built the `stop_reason`-driven loop) and Lesson 04 (you can name workflow vs. agent and the five patterns).
**Goal**: Prove — with real captured output, not assertion — *why* the three tempting loop-termination shortcuts fail. Lesson 03 told you `stop_reason == "end_turn"` is the only clean exit; this lesson makes each alternative break in front of you so the exam's distractor answers become physically obvious.

## Why this matters for the exam

Domain 1 (27%) reliably offers a question of the form: *"An agent loop should terminate when ___?"* with four plausible-sounding answers. Three of them are the anti-patterns below. The exam guide calls them out by name, and they're seductive because each one *looks* like it works on the happy path and only fails on the cases you didn't test. You lock the right answer by having watched the wrong ones fail.

The one correct answer, every time: **the loop continues while `stop_reason == "tool_use"` and terminates on `stop_reason == "end_turn"`.** Everything else is a smoke alarm or a bug.

## What we're going to do

Reuse Lesson 03's two-tool employee world (one query, `find_employee_id → get_employee_details → end_turn`, a genuine 3-iteration chain). Run the **same** question through four loop variants — the correct one plus the three anti-patterns — and read the output side by side. Only one returns the team and start date.

---

## The three anti-patterns (and why each is tempting)

| # | The shortcut | Why it looks reasonable | How it actually fails |
|---|---|---|---|
| 1 | **"Did the assistant produce any text?"** → done | "If it wrote prose, it must be answering." | A `tool_use` turn frequently *also* carries a short text preamble ("Let me look that up."). The check fires on iteration 1 and returns the preamble — **before any tool runs**. |
| 2 | **Parse the text for a completion phrase** ("in summary…", "the answer is…") | "I'll just detect when it's wrapping up." | Brittle in both directions: the model often finishes *without* your magic phrase (false negative — you loop past a real `end_turn`), or says a phrase mid-reasoning while tools are still pending (false positive — you exit early). |
| 3 | **Iteration cap as the *primary* stop** | "I'll just loop N times; that's bounded and safe." | A cap is a circuit-breaker, not a termination condition. Set low, it severs the chain mid-flight and returns a half-answer. Set high, it's irrelevant on the happy path and only ever fires on bugs. Either way it isn't *deciding* anything. |

The through-line: **all three inspect the wrong signal.** `tool_use` vs. `end_turn` is a structured, model-emitted control signal. Text content and iteration counts are *side effects* you're trying to reverse-engineer the control signal from. Don't. The API already tells you.

---

## Build — make all three fail on the same query

Create `lessons/scripts/loop_antipatterns.py`. It reuses the Lesson 03 tools (trimmed to one employee — we only need the chain, not the directory) and defines four loops: `correct_loop`, then one function per anti-pattern. The single shared question is *"What team does Ada Lovelace work on, and when did she start?"* — which **requires** the two-step chain.

```python
"""Lesson 05 — Loop anti-patterns, demonstrated by making each one FAIL.

We reuse Lesson 03's two-tool employee world (find_employee_id ->
get_employee_details) because it forces a real chain: Claude must call
tool 1, read the result, then call tool 2 with what it learned. A correct
loop takes 3 iterations and ends on stop_reason == "end_turn".
"""

import json

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

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
                "name": {"type": "string", "description": "Full or partial name."}
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
                "employee_id": {"type": "string", "description": "Id like 'E-1042'."}
            },
            "required": ["employee_id"],
        },
    },
]

DIRECTORY = {
    "E-1042": {"name": "Ada Lovelace", "role": "Staff Engineer",
               "team": "Platform", "start": "2021-03-15"},
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


IMPLEMENTATIONS = {
    "find_employee_id": find_employee_id,
    "get_employee_details": get_employee_details,
}

QUESTION = "What team does Ada Lovelace work on, and when did she start?"


def call(messages):
    return client.messages.create(
        model="claude-haiku-4-5", max_tokens=600, tools=TOOLS, messages=messages
    )


def text_of(response) -> str:
    return "".join(b.text for b in response.content if b.type == "text")


def run_tools(response, messages):
    """Append the assistant turn, execute its tool_use blocks, append results."""
    messages.append({"role": "assistant", "content": response.content})
    results = []
    for block in response.content:
        if block.type == "tool_use":
            output = IMPLEMENTATIONS[block.name](**block.input)
            print(f"  [exec] {block.name}({block.input}) -> {output}")
            results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": output}
            )
    messages.append({"role": "user", "content": results})


# CORRECT: stop_reason == "end_turn" is the loop condition.
def correct_loop(max_iters: int = 10) -> str:
    print("\n### CORRECT — terminate on stop_reason == 'end_turn'")
    messages = [{"role": "user", "content": QUESTION}]
    for i in range(1, max_iters + 1):
        response = call(messages)
        print(f"[iter {i}] stop_reason={response.stop_reason!r}")
        if response.stop_reason == "end_turn":
            answer = text_of(response)
            print(f"  RETURNED: {answer!r}")
            return answer
        if response.stop_reason != "tool_use":
            return ""
        run_tools(response, messages)
    print(f"  !! hit max_iters={max_iters} — runaway")
    return ""


# ANTI-PATTERN 1: "did the assistant produce any text?" as the done-check.
def antipattern_text_present(max_iters: int = 10) -> str:
    print("\n### ANTI-PATTERN 1 — return as soon as any text block appears")
    messages = [{"role": "user", "content": QUESTION}]
    for i in range(1, max_iters + 1):
        response = call(messages)
        any_text = any(b.type == "text" for b in response.content)
        has_tool = any(b.type == "tool_use" for b in response.content)
        print(f"[iter {i}] stop_reason={response.stop_reason!r} "
              f"has_text={any_text} has_tool={has_tool}")
        if any_text:  # <-- THE BUG
            print(f"  RETURNED: {text_of(response)!r}")
            return text_of(response)
        if response.stop_reason != "tool_use":
            return ""
        run_tools(response, messages)
    return ""


# ANTI-PATTERN 2: parse the assistant's text for a "done" phrase.
DONE_MARKERS = ("here's what i found", "to summarize", "in summary", "the answer is")


def antipattern_text_parse(max_iters: int = 10) -> str:
    print("\n### ANTI-PATTERN 2 — parse the text for a completion phrase")
    messages = [{"role": "user", "content": QUESTION}]
    for i in range(1, max_iters + 1):
        response = call(messages)
        txt = text_of(response).lower()
        looks_done = any(m in txt for m in DONE_MARKERS)
        print(f"[iter {i}] stop_reason={response.stop_reason!r} "
              f"looks_done={looks_done} text={text_of(response)[:60]!r}")
        if looks_done:  # <-- THE BUG
            print(f"  RETURNED (matched a marker): {text_of(response)!r}")
            return text_of(response)
        if response.stop_reason == "end_turn":
            print("  reached real end_turn but NO marker matched — parser missed it")
            return text_of(response)
        if response.stop_reason != "tool_use":
            return ""
        run_tools(response, messages)
    return ""


# ANTI-PATTERN 3: iteration cap as the PRIMARY terminator (cap = 1).
def antipattern_cap_as_stop(max_iters: int = 1) -> str:
    print(f"\n### ANTI-PATTERN 3 — iteration cap (={max_iters}) as the primary stop")
    messages = [{"role": "user", "content": QUESTION}]
    last_text = ""
    for i in range(1, max_iters + 1):
        response = call(messages)
        print(f"[iter {i}] stop_reason={response.stop_reason!r}")
        if response.stop_reason == "end_turn":
            return text_of(response)
        if response.stop_reason != "tool_use":
            return ""
        run_tools(response, messages)
        last_text = text_of(response)
    print(f"  cap reached. best we can return: {last_text!r}")
    return last_text


if __name__ == "__main__":
    print(f"Q: {QUESTION}")
    correct = correct_loop()
    antipattern_text_present()
    antipattern_text_parse()
    antipattern_cap_as_stop()
    print(f"\ncorrect answer contained 'Platform': {'Platform' in correct}")
```

Run it:

```bash
uv run python lessons/scripts/loop_antipatterns.py
```

### What you should see (real output, captured from a live run)

```
Q: What team does Ada Lovelace work on, and when did she start?

### CORRECT — terminate on stop_reason == 'end_turn'
[iter 1] stop_reason='tool_use'
  [exec] find_employee_id({'name': 'Ada Lovelace'}) -> {"id": "E-1042", "name": "Ada Lovelace"}
[iter 2] stop_reason='tool_use'
  [exec] get_employee_details({'employee_id': 'E-1042'}) -> {"name": "Ada Lovelace", "role": "Staff Engineer", "team": "Platform", "start": "2021-03-15"}
[iter 3] stop_reason='end_turn'
  RETURNED: 'Ada Lovelace works on the **Platform** team and started on **March 15, 2021**. She is a Staff Engineer.'

### ANTI-PATTERN 1 — return as soon as any text block appears
[iter 1] stop_reason='tool_use' has_text=True has_tool=True
  RETURNED: "I'll look up Ada Lovelace's information for you."

### ANTI-PATTERN 2 — parse the text for a completion phrase
[iter 1] stop_reason='tool_use' looks_done=False text=''
  [exec] find_employee_id({'name': 'Ada Lovelace'}) -> {"id": "E-1042", "name": "Ada Lovelace"}
[iter 2] stop_reason='tool_use' looks_done=False text='Now let me fetch her employee details:'
  [exec] get_employee_details({'employee_id': 'E-1042'}) -> {"name": "Ada Lovelace", "role": "Staff Engineer", "team": "Platform", "start": "2021-03-15"}
[iter 3] stop_reason='end_turn' looks_done=False text='Ada Lovelace works on the **Platform** team and started on *'
  reached real end_turn but NO marker matched — parser missed it

### ANTI-PATTERN 3 — iteration cap (=1) as the primary stop
[iter 1] stop_reason='tool_use'
  [exec] find_employee_id({'name': 'Ada Lovelace'}) -> {"id": "E-1042", "name": "Ada Lovelace"}
  cap reached. best we can return: "I'll help you find that information about Ada Lovelace. Let me first look up her employee ID, and then get her details."

correct answer contained 'Platform': True
```

### Read each failure

- **Anti-pattern 1 (text-present)** returned `"I'll look up Ada Lovelace's information for you."` on **iteration 1**. Look at that iter-1 line: `has_text=True has_tool=True`. The assistant requested a tool *and* wrote a one-line preamble in the same turn. The "any text?" check sees the preamble, declares victory, and returns it. **No tool ever ran.** The user gets a promise, not an answer. This is the exact failure Lesson 03's exercise 3 predicted — now you've seen it.

- **Anti-pattern 2 (text-parse)** is the subtle one: it failed by a **false negative**. The chain ran correctly through both tools, and on iter 3 the model produced the real answer at `stop_reason='end_turn'` — but its phrasing ("Ada Lovelace works on the Platform team…") matched none of our `DONE_MARKERS`. A parser keyed on completion phrases would have *missed a genuine completion* and either looped forever or fallen through to undefined behavior. (Run it a few times and you'll also see the false-positive direction: the model drops a phrase like "the answer is" mid-reasoning while a tool call is still pending.) Either way, you're trying to detect a structured event by grepping prose. The structured event already exists: `end_turn`.

- **Anti-pattern 3 (cap-as-stop)** cut off after iter 1. The cap of 1 meant the loop ran one tool call (`find_employee_id`), then the `for` range was exhausted — so it never made the second call, never fetched the details, and the "best we can return" is the model's opening preamble. **No team, no start date.** A cap doesn't *decide* the agent is done; it just stops counting. The right role for `max_iters` (Lesson 03, Concept 3) is a high circuit-breaker that only fires on a bug.

- **Only `correct_loop`** returned the team and the start date — the final line confirms `'Platform' in correct` is `True`. Same model, same question, same tools. The only variable is the termination logic.

---

## Exercises (do these before moving on)

1. **Make anti-pattern 2 fail the *other* way.** Add `"let me"` to `DONE_MARKERS` and re-run. Now the iter-2 text ("Now let me fetch her employee details:") matches — and the loop exits *with a tool call still pending*, returning a mid-reasoning sentence instead of the answer. You've now seen the false positive and the false negative from the same parser. Write one sentence on why no marker list can be correct.

2. **Find the cap that "works" — then break it.** Raise anti-pattern 3's `max_iters` to 3 and re-run; it now returns the right answer. Does that make cap-as-primary-stop correct? (No — explain why. Hint: what happens to a 4-tool question under the same cap of 3? The cap didn't *understand* the task was done; it just happened to be ≥ the number of iterations this particular question needed.)

3. **Spot it in the wild.** Skim the three distractor framings and, for each, name which anti-pattern it is: (a) "Loop until the response contains a non-empty text block." (b) "Run up to 5 tool rounds, then return whatever you have." (c) "Stop when the model says it has finished."

Then answer in one sentence each:

1. Why does the "any text content?" check fail on the *first* iteration of a chain?
2. Give one false-positive and one false-negative failure mode of completion-phrase parsing.
3. What is the legitimate role of `max_iters`, and what should happen when it fires?
4. What single structured signal makes all three anti-patterns unnecessary?

---

## What you now know

- The three exam anti-patterns, each demonstrated failing on a real call: **text-present check** (returns the preamble before tools run), **completion-phrase parsing** (false positives and false negatives — brittle in both directions), **iteration cap as primary stop** (severs the chain; doesn't decide anything).
- They share one root error: inferring control flow from *side effects* (prose, counters) instead of reading the *structured signal* the API emits.
- `stop_reason == "end_turn"` is the only correct normal terminator; `stop_reason == "tool_use"` is the only correct continue condition; `max_iters` is a high circuit-breaker whose firing is a bug signal.

## Up next

**Lesson 06 — End-to-end multi-turn: build a customer-lookup agent.** You've now built the correct loop (L03) and ruled out the wrong terminators (L05). Lesson 06 puts it to work as a *real* multi-tool agent — lookup customer → fetch orders → check status — the canonical **Agent** pattern from L04's catalogue (not orchestrator-workers, not prompt chaining: Claude decides which tool each turn and ends with a clean answer). It's the first lesson where the loop stops being a demo and becomes a small product.

When you've worked through this lesson and the exercises, tick the box in `lessons/README.md` and tell me you're done — I'll write 06.
