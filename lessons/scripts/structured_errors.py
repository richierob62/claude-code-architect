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
        return err(
            "business",
            False,
            f"Order {order_id} is on hold; tracking is withheld until the hold clears.",
        )
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
