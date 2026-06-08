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
            "properties": {"customer_id": {"type": "string", "description": "Id like 'C-7'."}},
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
            "properties": {"order_id": {"type": "string", "description": "Id like 'O-1001'."}},
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
    agent("What's the email for Santa Claus?")
