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
