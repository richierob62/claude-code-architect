# Lesson 07 — Structured errors: `isError`, `errorCategory`, `isRetryable`

**Time**: ~15 minutes
**Prerequisites**: Lesson 06 (you built the customer-lookup agent and watched it interpret a `{"error": ...}` string in exercise 2). Lesson 02 (content-block polymorphism — the discriminated-union shape per `type`). This is the lesson where that L02 question finally pays off.
**Goal**: Replace the ad-hoc `{"error": "..."}` strings your L06 tools returned with the **structured error shape the exam tests**. You'll learn the two levers that carry the real signal — the `tool_result`'s `is_error` flag (the transport-level "this failed") and a structured **payload** inside it (`errorCategory`, `isRetryable`, a human-readable message). And you'll learn the one distinction the exam keeps coming back to: an **access failure** is not the same as a **valid empty result**.

## Why this matters for the exam

Domain 2 (Tool Design & MCP, 18%) has a whole task statement on this — *"Implement structured error responses for MCP tools."* The exam's knowledge points, almost verbatim:

- **The `isError` flag pattern** for communicating tool failures back to the agent.
- **Four error categories**: *transient* (timeouts, service unavailable), *validation* (bad input), *business* (policy violation), *permission* (not allowed).
- **Why uniform errors are bad**: a generic `"Operation failed"` strips the agent of the information it needs to recover — should it retry? rephrase? give up and tell the user?
- **Retryable vs non-retryable**, and how returning that as *structured metadata* prevents wasted retries (the agent retries a transient timeout; it must *not* retry a validation error — the input won't fix itself).
- **The trap distinction** (it recurs in Domain 5 too): an **access failure** (the lookup couldn't run — timeout, permission) needs a retry/escalate decision; a **valid empty result** (the lookup ran fine, there's just nothing matching) is a *success*. Returning `[]` for "the service is down" is the classic exam mistake — it hides a failure as a success and the agent reports "you have no orders" when really it never checked.

If a scenario question hands you a tool that returns `"Error: could not complete"` and asks what's wrong, the answer is *"uniform error — no category, no retryability, agent can't choose a recovery path."* This lesson makes you build the fix.

## What's wrong with L06's errors

Your L06 tools did this:

```python
return json.dumps({"error": f"no customer matching {name!r}"})
```

Three problems, each one an exam talking point:

1. **It's not flagged as an error at the protocol level.** As far as the API is concerned this is an ordinary, *successful* tool result that happens to contain the word "error". The agent has to read the prose to notice anything went wrong. (Remember L06 exercise 2 — the agent *did* interpret it correctly, but only because Haiku is good at reading English. You don't want correctness to depend on that.)
2. **It has no category.** "No customer matching" — is that a validation error (you typed a bad name)? A transient one (the DB was down)? The agent can't tell, so it can't choose: retry, rephrase, or report.
3. **It carries no retry guidance.** The agent has to *guess* whether trying again could help. For "no customer matching" the answer is no — retrying the same name gets the same miss. But a timeout? Retry once. The tool *knows* which it is; an ad-hoc string throws that knowledge away.

---

## Concept — two layers: the flag and the payload

This is where your Lesson 02 question pays off. Recall: every content block is a **discriminated union** — a `type` field selects the shape. A `tool_result` block is one of those shapes, and it has an **optional `is_error` field**:

```python
{
    "type": "tool_result",
    "tool_use_id": block.id,
    "content": "...",
    "is_error": True,          # <-- the transport-level "this failed"
}
```

`is_error` is the **flag** — a boolean the *protocol* understands. When it's `True`, Claude is told unambiguously "the tool failed," independent of what the content says. That's layer one, and it's the literal "`isError` flag pattern" the exam names. (In the raw Anthropic API the field is `is_error`; MCP and the exam guide spell the concept `isError` — same idea, different surface.)

But a bare flag only says *that* it failed, not *how*. Layer two is the **payload**: the `content` you put in the error result is itself a structured object the agent can reason over.

```python
json.dumps({
    "errorCategory": "transient",      # transient | validation | business | permission
    "isRetryable": True,               # should the agent try again?
    "message": "Inventory service timed out. Retry in a moment.",  # human-readable
})
```

`errorCategory` + `isRetryable` + `message` is the structured-metadata triad the exam lists under *Skills in*. The flag tells the agent **it failed**; the payload tells it **why and what to do**. Both together let the agent pick a recovery path instead of guessing.

### The decision table the agent gets to make

The whole point of the structured shape is that it turns "the tool failed" into a *decision the agent can make*:

| `errorCategory` | Example | `isRetryable` | What a good agent does |
|---|---|---|---|
| `transient` | timeout, 503 | `true` | retry once or twice, then escalate |
| `validation` | malformed id | `false` | fix the input / rephrase, don't retry verbatim |
| `business` | "can't refund after 30 days" | `false` | stop, explain the rule to the user politely |
| `permission` | not allowed to see this | `false` | stop, escalate or tell the user |

And the distinction that sits *next to* this table, not in it:

> **Access failure ≠ valid empty result.** "No customer matching 'Zoe Carter'" is a *successful* lookup that found nothing — that is **not** an error. It's `{"customers": []}` with `is_error` **unset**. Reserve the error shape for cases where the lookup *couldn't run*. Getting this backwards is the single most-tested error-handling mistake on the exam.

---

## Build — give the L06 agent structured errors

We'll evolve the L06 customer agent. Two tools is enough to show every category, so this build trims to `find_customer` + `get_shipment` and adds three deliberate failure modes:

- a **validation** error (`get_shipment` rejects a malformed `order_id`),
- a **business** error (`get_shipment` refuses to expose tracking for a flagged/held order),
- a **transient** error you can toggle, to watch the agent *retry*.

And critically: a name that doesn't match returns a **valid empty result**, *not* an error — so you can see the agent treat "no such customer" differently from "the tool broke."

Create `lessons/scripts/structured_errors.py`:

```python
"""Lesson 07 — structured tool errors on top of the L06 agent.

Two layers of error signalling:
  1. the tool_result `is_error` flag  (protocol-level "this failed")
  2. a structured payload inside it    (errorCategory / isRetryable / message)

Plus the exam's key distinction: an ACCESS FAILURE (couldn't run) is an error;
a VALID EMPTY RESULT (ran fine, found nothing) is a success, not an error.
"""

import json

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

SYSTEM = (
    "You are a customer-support agent. Use the tools to look up real data. "
    "Tool results may be errors: each error tells you its errorCategory and "
    "whether isRetryable. If a transient error is retryable, try the SAME call "
    "again (at most twice). Never retry a validation, business, or permission "
    "error — instead, explain the situation to the user in plain language. "
    "An empty result list is NOT an error: it means the lookup ran and found "
    "nothing, so say so plainly. Never invent data."
)

TOOLS = [
    {
        "name": "find_customer",
        "description": (
            "Look up customers by full or partial name. Returns a list under "
            "'customers' (possibly empty if none match — that is a valid result, "
            "not an error)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "get_shipment",
        "description": (
            "Fetch carrier, tracking, and ETA for an order by order_id (format "
            "'O-####'). May fail with a structured error: validation (bad id), "
            "business (order is held and tracking is withheld), or transient "
            "(service timeout — retryable)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
]

CUSTOMERS = {
    "C-7": {"customer_id": "C-7", "name": "Nora Singh", "email": "nora@example.com"},
    "C-9": {"customer_id": "C-9", "name": "Omar Reyes", "email": "omar@example.com"},
}
SHIPMENTS = {
    "O-1001": {"carrier": "UPS", "tracking": "1Z999AA1", "eta": "2026-06-08"},
}
HELD_ORDERS = {"O-1002"}  # flagged: tracking withheld -> a BUSINESS error.

# Toggle to make get_shipment's FIRST call time out, so you can watch a retry.
SIMULATE_TIMEOUT = {"O-1001": 1}


def err(category: str, retryable: bool, message: str) -> tuple[str, bool]:
    """Build a structured error payload AND the is_error flag together.
    Returns (json_content, is_error=True)."""
    payload = {"errorCategory": category, "isRetryable": retryable, "message": message}
    return json.dumps(payload), True


def find_customer(name: str) -> tuple[str, bool]:
    needle = name.lower()
    matches = [rec for rec in CUSTOMERS.values() if needle in rec["name"].lower()]
    # VALID EMPTY RESULT: the lookup ran; there's just nothing. NOT an error.
    return json.dumps({"customers": matches}), False


def get_shipment(order_id: str) -> tuple[str, bool]:
    # 1. validation: wrong shape -> non-retryable, fix the input.
    if not order_id.startswith("O-") or not order_id[2:].isdigit():
        return err("validation", False, f"order_id {order_id!r} is malformed; expected 'O-####'.")
    # 2. transient: simulate a timeout on the first call only -> retryable.
    if SIMULATE_TIMEOUT.get(order_id, 0) > 0:
        SIMULATE_TIMEOUT[order_id] -= 1
        return err("transient", True, "Shipment service timed out. Retry shortly.")
    # 3. business: order is held -> non-retryable, explain to the user.
    if order_id in HELD_ORDERS:
        return err("business", False, f"Order {order_id} is on hold; tracking is withheld until the hold clears.")
    rec = SHIPMENTS.get(order_id)
    # access failure vs empty: an unknown id here is a genuine miss; treat as
    # validation (the agent shouldn't retry a not-found order verbatim).
    if rec is None:
        return err("validation", False, f"No order {order_id} on file.")
    return json.dumps(rec), False


IMPLEMENTATIONS = {"find_customer": find_customer, "get_shipment": get_shipment}


def agent(user_text: str, max_iters: int = 12) -> str:
    """Same L03/L06 loop — the ONLY change is that each tool now returns a
    (content, is_error) pair and we forward is_error on the tool_result."""
    messages = [{"role": "user", "content": user_text}]
    print(f"\n=== Q: {user_text}")

    for i in range(1, max_iters + 1):
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=600,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        print(f"[iter {i}] stop_reason={response.stop_reason!r}")

        if response.stop_reason == "end_turn":
            final = "".join(b.text for b in response.content if b.type == "text")
            print(f"  ANSWER: {final}")
            return final

        if response.stop_reason != "tool_use":
            print("  unexpected stop_reason; aborting")
            return ""

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                content, is_error = IMPLEMENTATIONS[block.name](**block.input)
                flag = "  *ERROR*" if is_error else ""
                print(f"  [exec]{flag} {block.name}({block.input}) -> {content}")
                result = {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                }
                if is_error:
                    result["is_error"] = True  # layer 1: the protocol flag
                tool_results.append(result)
        messages.append({"role": "user", "content": tool_results})

    print(f"  !! hit max_iters={max_iters} without end_turn")
    return ""


if __name__ == "__main__":
    # A: valid empty result — NOT an error. Agent should say "no such customer".
    agent("What's the email for Zoe Carter?")
    # B: transient error -> retryable. Watch get_shipment fail once, then succeed.
    agent("Where is order O-1001? Give me the tracking number.")
    # C: business error -> non-retryable. Agent must explain, not retry.
    agent("What's the tracking for order O-1002?")
    # D: validation error -> non-retryable. Agent must not retry a bad id.
    agent("Track order 1003 for me.")
```

Run it:

```bash
uv run python lessons/scripts/structured_errors.py
```

### What you should see (real output, captured from a live run)

```
=== Q: What's the email for Zoe Carter?
[iter 1] stop_reason='tool_use'
  [exec] find_customer({'name': 'Zoe Carter'}) -> {"customers": []}
[iter 2] stop_reason='end_turn'
  ANSWER: I didn't find any customer named Zoe Carter in the system. The lookup came back with no results. Could you double-check the name, or let me know if there's any other spelling variation I should try?

=== Q: Where is order O-1001? Give me the tracking number.
[iter 1] stop_reason='tool_use'
  [exec]  *ERROR* get_shipment({'order_id': 'O-1001'}) -> {"errorCategory": "transient", "isRetryable": true, "message": "Shipment service timed out. Retry shortly."}
[iter 2] stop_reason='tool_use'
  [exec] get_shipment({'order_id': 'O-1001'}) -> {"carrier": "UPS", "tracking": "1Z999AA1", "eta": "2026-06-08"}
[iter 3] stop_reason='end_turn'
  ANSWER: Here's the information for order O-1001: Carrier UPS, tracking number 1Z999AA1, estimated delivery June 8, 2026.

=== Q: What's the tracking for order O-1002?
[iter 1] stop_reason='tool_use'
  [exec]  *ERROR* get_shipment({'order_id': 'O-1002'}) -> {"errorCategory": "business", "isRetryable": false, "message": "Order O-1002 is on hold; tracking is withheld until the hold clears."}
[iter 2] stop_reason='end_turn'
  ANSWER: Order O-1002 is currently on hold, so tracking information is not available at this time. The tracking details will be released once the hold is cleared.

=== Q: Track order 1003 for me.
[iter 1] stop_reason='tool_use'
  [exec]  *ERROR* get_shipment({'order_id': 'O-1003'}) -> {"errorCategory": "validation", "isRetryable": false, "message": "No order O-1003 on file."}
[iter 2] stop_reason='end_turn'
  ANSWER: I couldn't find an order with ID O-1003 in the system. Could you double-check the order number? Order IDs are formatted as "O-" followed by four digits.
```

*(Note: in scenario D the model normalized "1003" to "O-1003" on its own, so the call landed on the not-found branch — also a non-retryable `validation` error — rather than the malformed-format branch. If your run passes a raw "1003" you'll see the `'O-####'` format message instead. Either way it's a non-retryable validation error and the agent does not retry.)*

*(The `[iter]` / `[exec]` structure and the `*ERROR*` flags are deterministic — same inputs, same categories, same retry on O-1001 every run. The `ANSWER:` prose is free-form model text and will vary slightly run-to-run.)*

### Read what the agent did

Each scenario exercises one row of the decision table — and the agent's *behaviour* changes per category, driven entirely by the structured payload you returned:

- **A — valid empty result.** `find_customer` returned `{"customers": []}` with **no** `is_error` flag. The agent did not treat this as a failure, did not retry, and reported "no such customer." This is the access-failure-vs-empty-result distinction in the flesh: the lookup *succeeded*; it just found nothing. If you'd returned an error here, the agent might have retried a name that will never match.

- **B — transient, retryable.** The first `get_shipment("O-1001")` returned `is_error=True` with `errorCategory: transient, isRetryable: true`. The agent **retried the same call** — and the second time the simulated timeout was used up, so it succeeded and answered. That retry happened because the metadata *told* it to, not because of any retry logic in the loop.

- **C — business, non-retryable.** `get_shipment("O-1002")` returned `business / isRetryable: false`. The agent did **not** retry; it explained the hold to the user in plain language. A bare `{"error": "failed"}` could not have produced this — the agent wouldn't know it's a policy issue rather than a glitch.

- **D — validation, non-retryable.** "Track order 1003" → the agent calls `get_shipment` with a malformed id → `validation / isRetryable: false`. The agent doesn't retry the same bad id; it either reports the format problem or asks for a correct order id.

The loop body still knows nothing about emails, holds, or timeouts. The **only** structural change from L06 is that tools return `(content, is_error)` and we forward `is_error` on the `tool_result`. Every behavioural difference above came from the *payload*, read by the model.

---

## Exercises (do these before moving on)

1. **Prove the flag matters.** In the `agent` loop, comment out the `if is_error: result["is_error"] = True` line so the flag is never set (but keep the structured payload in `content`). Re-run scenario B. Does the agent still retry? (It probably still does — Haiku reads the `errorCategory` prose — but you've now *demoted* a protocol signal to "hope the model reads English." Note in one sentence why relying on that is fragile, and what the flag buys you that the prose alone doesn't.)

2. **Break the empty-result distinction on purpose.** Change `find_customer` so that a no-match returns `err("transient", True, "lookup failed")` instead of `{"customers": []}`. Re-run scenario A. Watch the agent **retry a lookup that can never succeed** (Zoe Carter still won't exist on the retry). Then revert. Write one sentence: which exam mistake did you just reproduce, and why is "empty list, no error" the correct shape?

3. **Add a permission category.** Add a held set `RESTRICTED = {"O-1001"}` and, *before* the transient check in `get_shipment`, return `err("permission", False, "You are not authorized to view tracking for this order.")` for restricted orders. Ask scenario B again. Confirm the agent stops and explains rather than retrying — `permission`, like `business` and `validation`, is non-retryable. (Then revert so the rest of the build still works.)

Then answer in one sentence each:

1. What is the difference between the `is_error` **flag** and the `errorCategory` **payload** — what does each one let the agent do that the other can't?
2. Why is `transient` the only category in the table with `isRetryable: true`?
3. Scenario A returned an empty list with no error flag. Why would returning a `transient` error there have been a bug, even though "we found nothing" *feels* like a failure?
4. The exam calls a generic `"Operation failed"` an anti-pattern. In terms of the decision table, what exactly does the agent lose when the error is uniform?

---

## What you now know

- **Two layers of error signalling**: the `tool_result` `is_error` flag (protocol-level "this failed", the exam's `isError` pattern) and a structured **payload** (`errorCategory`, `isRetryable`, human-readable `message`) the agent reasons over.
- **The four categories** — *transient / validation / business / permission* — and the rule that only `transient` is retryable; the rest mean "stop and explain," not "try again."
- **Why uniform errors are an anti-pattern**: `"Operation failed"` collapses the whole decision table into one undifferentiated signal, so the agent can't choose a recovery path.
- **Access failure ≠ valid empty result** — the most-tested distinction in error handling. The lookup that runs and finds nothing returns `[]` with no error; reserve the error shape for the lookup that *couldn't run*.
- This rides on the **L02 discriminated-union** insight: `tool_result` is one content-block shape, and `is_error` is the optional field on it that flips its meaning.

## Up next

**Lesson 08 — `tool_choice`: `auto` vs `any` vs forced.** So far the model has always *chosen* whether to call a tool (`tool_choice` defaulted to `auto`). Lesson 08 covers the three modes — let the model decide (`auto`), force it to call *some* tool (`any`), or force one *specific* tool (`{"type": "tool", "name": ...}`) — and when each is the right call (e.g. forcing a tool to guarantee structured output, the bridge into Module F). That closes Module B.

When you've worked through this lesson and the exercises, tick the box in `lessons/README.md` and tell me you're done — I'll write 08.
