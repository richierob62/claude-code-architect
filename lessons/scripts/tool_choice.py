"""Lesson 08 — tool_choice: auto vs any vs forced, on one input.

We send the SAME message under each mode and watch stop_reason + whether a
tool was called. Then we show the forced-first-step-then-auto pattern.
"""

import json

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# One extraction tool. Its input_schema IS the structured-output shape we want.
TOOLS = [
    {
        "name": "record_sentiment",
        "description": "Record the sentiment of a customer message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "negative", "neutral"],
                },
                "intensity": {
                    "type": "integer",
                    "description": "1 (mild) to 5 (strong).",
                },
            },
            "required": ["sentiment", "intensity"],
        },
    }
]


def ask(user_text: str, tool_choice: dict, label: str) -> None:
    """One single-turn call. Print stop_reason and whether a tool was called.
    We do NOT loop or feed results back — this lesson is about the FIRST turn."""
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        tools=TOOLS,
        tool_choice=tool_choice,
        messages=[{"role": "user", "content": user_text}],
    )
    tool_calls = [b for b in response.content if b.type == "tool_use"]
    text = "".join(b.text for b in response.content if b.type == "text")
    print(f"\n--- {label}: tool_choice={tool_choice}")
    print(f"    user: {user_text!r}")
    print(f"    stop_reason={response.stop_reason!r}  tools_called={len(tool_calls)}")
    if tool_calls:
        print(f"    -> {tool_calls[0].name}({json.dumps(tool_calls[0].input)})")
    if text:
        print(f"    text: {text!r}")


if __name__ == "__main__":
    angry = "This is the third time my order arrived broken. I am furious."
    chitchat = "Hey, thanks so much, you've been really helpful today!"
    neutral_q = "What time do you close on Saturdays?"

    # 1. auto on a clearly-extractable message: model CHOOSES to call the tool.
    ask(angry, {"type": "auto"}, "AUTO + extractable")

    # 2. auto on a question the tool can't answer: model returns TEXT, no tool.
    ask(neutral_q, {"type": "auto"}, "AUTO + non-extractable")

    # 3. any: model MUST call a tool (it has only one, so it calls that one).
    ask(chitchat, {"type": "any"}, "ANY")

    # 4. forced: model MUST call record_sentiment by name, this turn.
    ask(neutral_q, {"type": "tool", "name": "record_sentiment"}, "FORCED")
