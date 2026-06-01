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
    {
        "name": "list_team_members",
        "description": (
            "Return the names and roles of all employees belonging to the team having received the team name."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "team": {
                    "type": "string",
                    "description": "The name of the team.",
                }
            },
            "required": ["team"],
        },
    },
]

# Fake "database". Tiny on purpose.
DIRECTORY = {
    "E-1042": {
        "name": "Ada Lovelace",
        "role": "Staff Engineer",
        "team": "Platform",
        "start": "2021-03-15",
    },
    "E-2087": {
        "name": "Alan Turing",
        "role": "Principal Researcher",
        "team": "Cryptography",
        "start": "2019-09-01",
    },
    "E-1055": {
        "name": "Max Romeo",
        "role": "Senior Engineer",
        "team": "Platform",
        "start": "2019-11-01",
    },
    "E-3120": {
        "name": "Grace Hopper",
        "role": "Director of Compilers",
        "team": "Languages",
        "start": "2018-01-08",
    },
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


def list_team_members(team: str) -> str:
    members: list[dict[str, str]] = [
        {"name": rec["name"], "role": rec["role"]}
        for rec in DIRECTORY.values()
        if rec["team"] == team
    ]
    if not members:
        return json.dumps({"error": f"no employees on team {team!r}"})
    return json.dumps(members)


# Dispatch table. New tools just go in here.
IMPLEMENTATIONS = {
    "find_employee_id": find_employee_id,
    "get_employee_details": get_employee_details,
    "list_team_members": list_team_members,
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
        # several at once — Lesson 16 explores parallel calls in depth.)
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
    # Forces a 2-call chain: name → id (call 1), id → details (call 2), then end_turn.
    run("What team does Ada Lovelace work on, and when did she start?")
    # Forces a different chain on a different employee.
    run("Tell me Grace Hopper's role and team.")
    # Direct answer; no tools needed. Loop exits on iter 1 with end_turn.
    run("What does the acronym 'API' stand for?")
    run("Who are the employees on Ada's team?")
