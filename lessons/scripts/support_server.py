"""A tiny MCP server: one tool (action) + one resource (content catalog).

Run directly (`uv run python lessons/scripts/support_server.py`) and it
waits on stdin for MCP messages — that's a server speaking stdio, not a
hang. A client (part 2) is what drives it.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("support-desk")

# Pretend this is a backend. In a real server the catalog would be built
# from a live DB/API; here it's a hand-written dict so the lesson is cheap.
PLANS = {
    "free": {"price": 0, "seats": 1, "support": "community"},
    "pro": {"price": 20, "seats": 5, "support": "email"},
    "business": {"price": 60, "seats": 25, "support": "priority"},
}


@mcp.tool()
def lookup_plan(plan_name: str) -> dict:
    """Look up the price, seat limit, and support tier for ONE plan by name.

    Use this when the customer names a specific plan. Returns a dict with
    price (USD/month), seats, and support tier. Unknown name -> an error
    payload listing the known plans.
    """
    plan = PLANS.get(plan_name.lower())
    if plan is None:
        return {"error": f"unknown plan: {plan_name}", "known": list(PLANS)}
    return {"plan": plan_name.lower(), **plan}


@mcp.tool()
def cheapest_plan() -> dict:
    """Return the cheapest PAID plan (lowest price among plans costing more than $0).

    Takes no arguments. Returns a dict with the plan name plus its price
    (USD/month), seats, and support tier.
    """
    name, plan = min(
        ((name, p) for name, p in PLANS.items() if p["price"] > 0),
        key=lambda item: item[1]["price"],
    )
    return {"plan": name, **plan}


@mcp.resource("catalog://plans")
def plan_catalog() -> str:
    """The full catalog of available plans, so an agent knows what exists
    up front WITHOUT calling lookup_plan once per guess."""
    lines = ["Available plans (name: $price/mo, seats, support):"]
    for name, p in PLANS.items():
        lines.append(f"- {name}: ${p['price']}/mo, {p['seats']} seats, {p['support']} support")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()  # defaults to stdio transport
