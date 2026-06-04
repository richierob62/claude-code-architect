# Lesson 06 — End-to-end multi-turn: build a customer-lookup agent

**Time**: ~15 minutes
**Prerequisites**: Lesson 03 (the `stop_reason`-driven loop) and Lesson 05 (you've watched the three wrong terminators fail). Lesson 04 gave you the word **Agent** for what we build here.
**Goal**: Stop demoing the loop and use it. Build a three-tool customer-support agent — *look up customer → fetch their orders → check a shipment's status* — where the loop length isn't fixed and **Claude decides which tool to call each turn**. This is the canonical **Agent** pattern from L04's catalogue, running for real.

## Why this matters for the exam

Domain 1 (27%) doesn't just ask you to *recognize* the agentic loop — several scenario questions hand you a support/ops workflow and ask "what shape is this?" The trap answers are the neighbouring patterns from L04:

- **"Prompt chaining"** — wrong, because chaining means *you* hard-code the sequence (call A, then always B, then always C). Here the sequence isn't fixed: a question about a customer's email needs one tool; a question about a shipment needs three. The model picks the path.
- **"Orchestrator-workers"** — wrong, because there's no orchestrator delegating subtasks to worker agents. It's one model, one loop, calling tools.

The right answer is **Agent**: *a single model in a loop, choosing tools turn by turn until it has what it needs, terminating on `end_turn`.* This lesson builds exactly that so the label is grounded in something you ran, not memorized. Recall the L04 mnemonic — *"Charlie ran parallel to the orchestra evaluating the **agent**"* — the agent is the last and most autonomous pattern, and this is it.

## What's new vs. Lesson 03

L03's employee world was deliberately rigid: every interesting question forced the *same* 2-step chain (`find_id → get_details`). That made the loop visible but hid the agent's real job — **choosing**. Here we add a third tool and a branch in the data so different questions take different paths:

- A one-hop question (`find_customer` only) ends in 2 iterations.
- A two-hop question (`find_customer → get_orders`) ends in 3.
- A three-hop question (`find_customer → get_orders → get_shipment`) ends in 4.

Same loop body, same termination rule. The only thing that changes between runs is **how many tools Claude decides it needs** — and that decision is the agent.

---

## Concept — the loop doesn't change; the agent's *choices* do

You already have the control flow. It is byte-for-byte the L03 loop: call → if `end_turn` return → if `tool_use` run every block and append results → repeat, with a high `max_iters` circuit-breaker. **Do not add anything to it.** No "which question is this?" routing, no per-tool special-casing, no counting how many tools you expect. The whole point of the Agent pattern is that the control flow is fixed and *generic* while the behaviour is open-ended.

What makes it feel like a product rather than a demo is three things layered on top of that unchanged loop:

1. **A realistic tool surface** — three tools whose outputs feed each other (`customer_id → order_id → shipment`), so the agent has to thread state across calls.
2. **A system prompt** that gives the agent a role and a rule ("you are a support agent; never invent order or shipment data — always look it up"). This is your first real system prompt in the course; it shapes *how* the agent uses the tools.
3. **A clean return value** — the loop hands back the final text, so a caller (a CLI, a web handler, a test) can use it. That's the line between "script that prints" and "function you can build on."

---

## Build — the customer-lookup agent

Create `lessons/scripts/customer_agent.py`. Three tools, a small data world with a deliberate branch, a system prompt, and the *unchanged* L03 loop returning a final answer.

```python
"""Lesson 06 — a real multi-tool Agent: customer support lookup.

Three tools that chain: find_customer (name -> id) feeds get_orders
(id -> list of orders) feeds get_shipment (order_id -> tracking). Different
questions need different numbers of hops, so the AGENT decides the path.
The loop itself is identical to Lesson 03 — only the tools and the system
prompt are new.
"""

import json

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

SYSTEM = (
    "You are a customer-support agent for an online store. Answer the user's "
    "question by looking up real data with the tools provided. Never invent "
    "customer, order, or shipment details — if you don't have a fact, fetch it. "
    "When you have enough to answer, reply concisely in plain language."
)

TOOLS = [
    {
        "name": "find_customer",
        "description": (
            "Look up a customer's internal ID and email by their full or partial "
            "name. Use this first when you have a name but not a customer_id."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Full or partial customer name."}
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_orders",
        "description": (
            "List a customer's orders (order_id, item, status) by their customer_id. "
            "Requires the customer_id from find_customer; does not accept names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Id like 'C-7'."}
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_shipment",
        "description": (
            "Fetch the carrier, tracking number, and delivery estimate for a single "
            "order by its order_id. Requires an order_id from get_orders."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Id like 'O-1001'."}
            },
            "required": ["order_id"],
        },
    },
]

# Small world with a branch: Nora has two orders, one shipped, one processing.
CUSTOMERS = {
    "C-7": {"name": "Nora Singh", "email": "nora@example.com"},
    "C-9": {"name": "Omar Reyes", "email": "omar@example.com"},
}
ORDERS = {
    "C-7": [
        {"order_id": "O-1001", "item": "Mechanical keyboard", "status": "shipped"},
        {"order_id": "O-1002", "item": "USB-C cable", "status": "processing"},
    ],
    "C-9": [
        {"order_id": "O-1050", "item": "Laptop stand", "status": "delivered"},
    ],
}
SHIPMENTS = {
    "O-1001": {"carrier": "UPS", "tracking": "1Z999AA1", "eta": "2026-06-08"},
    "O-1050": {"carrier": "FedEx", "tracking": "7700123456", "eta": "delivered 2026-06-01"},
}


def find_customer(name: str) -> str:
    needle = name.lower()
    for cid, rec in CUSTOMERS.items():
        if needle in rec["name"].lower():
            return json.dumps({"customer_id": cid, **rec})
    return json.dumps({"error": f"no customer matching {name!r}"})


def get_orders(customer_id: str) -> str:
    orders = ORDERS.get(customer_id)
    if orders is None:
        return json.dumps({"error": f"unknown customer_id {customer_id!r}"})
    return json.dumps(orders)


def get_shipment(order_id: str) -> str:
    rec = SHIPMENTS.get(order_id)
    if rec is None:
        return json.dumps({"error": f"no shipment on file for {order_id!r}"})
    return json.dumps(rec)


IMPLEMENTATIONS = {
    "find_customer": find_customer,
    "get_orders": get_orders,
    "get_shipment": get_shipment,
}


def agent(user_text: str, max_iters: int = 10) -> str:
    """The Agent pattern. This loop is identical to Lesson 03 — stop_reason is
    the only termination logic. It RETURNS the final answer so a caller can use
    it; that return value is what makes this a function, not just a printout."""
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
                output = IMPLEMENTATIONS[block.name](**block.input)
                print(f"  [exec] {block.name}({block.input}) -> {output}")
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": output}
                )
        messages.append({"role": "user", "content": tool_results})

    print(f"  !! hit max_iters={max_iters} without end_turn — runaway")
    return ""


if __name__ == "__main__":
    # 1 hop: only needs find_customer.
    agent("What's the email address on file for Nora Singh?")
    # 2 hops: find_customer -> get_orders.
    agent("What has Omar Reyes ordered?")
    # 3 hops: find_customer -> get_orders -> get_shipment.
    agent("When will Nora Singh's mechanical keyboard arrive?")
```

Run it:

```bash
uv run python lessons/scripts/customer_agent.py
```

### What you should see (real output, captured from a live run)

```
=== Q: What's the email address on file for Nora Singh?
[iter 1] stop_reason='tool_use'
  [exec] find_customer({'name': 'Nora Singh'}) -> {"customer_id": "C-7", "name": "Nora Singh", "email": "nora@example.com"}
[iter 2] stop_reason='end_turn'
  ANSWER: The email address on file for Nora Singh is **nora@example.com**.

=== Q: What has Omar Reyes ordered?
[iter 1] stop_reason='tool_use'
  [exec] find_customer({'name': 'Omar Reyes'}) -> {"customer_id": "C-9", "name": "Omar Reyes", "email": "omar@example.com"}
[iter 2] stop_reason='tool_use'
  [exec] get_orders({'customer_id': 'C-9'}) -> [{"order_id": "O-1050", "item": "Laptop stand", "status": "delivered"}]
[iter 3] stop_reason='end_turn'
  ANSWER: Omar Reyes has ordered one item:

- **Laptop stand** (Order ID: O-1050) — Status: **Delivered**

=== Q: When will Nora Singh's mechanical keyboard arrive?
[iter 1] stop_reason='tool_use'
  [exec] find_customer({'name': 'Nora Singh'}) -> {"customer_id": "C-7", "name": "Nora Singh", "email": "nora@example.com"}
[iter 2] stop_reason='tool_use'
  [exec] get_orders({'customer_id': 'C-7'}) -> [{"order_id": "O-1001", "item": "Mechanical keyboard", "status": "shipped"}, {"order_id": "O-1002", "item": "USB-C cable", "status": "processing"}]
[iter 3] stop_reason='tool_use'
  [exec] get_shipment({'order_id': 'O-1001'}) -> {"carrier": "UPS", "tracking": "1Z999AA1", "eta": "2026-06-08"}
[iter 4] stop_reason='end_turn'
  ANSWER: Nora Singh's mechanical keyboard is scheduled to arrive on **June 8, 2026**. It's being shipped via UPS with tracking number **1Z999AA1**.
```

(The `[iter]` / `[exec]` structure is deterministic — same tools, same hops, same `stop_reason` sequence on every run. The `ANSWER:` *prose* will vary slightly run-to-run, since that's free-form model text; don't worry if your wording differs from above.)

### Read what the agent did

This is the lesson. **Three questions, three different loop lengths — and you wrote no branching to make that happen.**

- **The email question stopped at 2 iterations.** `find_customer` returned the email in its very first result, so the agent had everything it needed and went straight to `end_turn`. It did *not* call `get_orders` "just because the tool exists." The agent only fetches what the question requires.

- **The orders question took 3.** The agent looked up Omar's id, then called `get_orders` with it — but stopped there. It did **not** go on to `get_shipment`, because "what has Omar ordered?" doesn't ask about delivery. Compare this to L03, where *every* interesting question forced the same chain. Here the agent chose to stop one hop early.

- **The keyboard question took the full 4.** Here's the part worth staring at: in iter 2, `get_orders` returned **two** orders — the keyboard *and* a USB-C cable. The agent had to (a) pick the right one (the keyboard, `O-1001`, not the cable) and (b) extract *its* `order_id` to pass to `get_shipment`. That's the agent threading state across calls and filtering — the same skill that made L03 a "loop" rather than two independent calls, now with a choice baked in. It never looked up the cable's shipment, because you didn't ask about the cable.

The control flow that produced all three is the **identical** L03 loop. Nothing in it knows about emails, orders, or shipments. The branching lives entirely in the model's turn-by-turn tool choices — which is the definition of the **Agent** pattern.

---

## Exercises (do these before moving on)

1. **Prove it's choosing, not chaining.** Ask `agent("What's Omar Reyes's email and has his order shipped?")`. Watch the path: it should take *both* a one-hop fact (email, from `find_customer`) and the order status — and decide on its own whether it needs `get_shipment` (Omar's order is already "delivered", so it may skip it). Note how many iterations it took and why. A prompt-chaining implementation couldn't vary like this; an Agent does it for free.

2. **Test the system prompt's "never invent" rule.** Ask about a customer who doesn't exist: `agent("What's the email for Zoe Carter?")`. `find_customer` returns an `error`. Does the agent fabricate an email, or does it report that it couldn't find the customer? (It should report the miss — that's the system prompt earning its keep. If you delete the "never invent" sentence and re-run, watch whether behaviour drifts.)

3. **Add a tool, change nothing else.** Add `get_return_policy(item: str)` returning a canned policy string, drop it in `TOOLS` and `IMPLEMENTATIONS`, then ask `agent("Can Nora return her keyboard, and when does it arrive?")`. You should see the agent interleave a *new* tool with the existing chain — proving the loop body never needs to know which tools exist. The dispatch table is the only thing that grows.

Then answer in one sentence each:

1. Why is this the **Agent** pattern and not **prompt chaining**? (What specifically would chaining have hard-coded?)
2. The email question stopped after one tool call; the keyboard question used three. What in the code decided that difference — and what *didn't*?
3. In the keyboard run, `get_orders` returned two orders. What did the agent have to do with that result before it could call `get_shipment`?
4. What is the system prompt's job here, given that the tools already constrain what the agent *can* do?

---

## What you now know

- The **Agent** pattern in the flesh: one model, one generic loop, choosing tools turn by turn — loop length varies with the question, and **no branching logic in your code** produces that variation.
- A real agent threads state across calls (id → order → shipment) *and* filters (pick the keyboard, not the cable) — the model does this inside the unchanged L03 loop.
- A system prompt gives the agent a role and guardrails ("never invent — look it up") that shape tool use without touching control flow.
- Returning the final text (not just printing it) is what turns the loop into a reusable function — the seam every later lesson builds on.

## Up next

**Lesson 07 — Structured errors: `isError`, `errorCategory`, `isRetryable`.** Your tools currently signal failure by returning `{"error": "..."}` as plain JSON — and the agent in exercise 2 had to *interpret* that prose to know it failed. Lesson 07 replaces ad-hoc error strings with the structured tool-error shape the exam tests: marking a `tool_result` as an error, categorizing it, and telling the agent whether retrying is worthwhile. This is also where your Lesson 02 content-block question (the discriminated-union shape) finally pays off.

When you've worked through this lesson and the exercises, tick the box in `lessons/README.md` and tell me you're done — I'll write 07.
