import json

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

messages = []
cumulative_input = 0
cumulative_output = 0


def ask(user_text: str) -> str:
    global cumulative_input, cumulative_output
    messages.append({"role": "user", "content": user_text})
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        messages=messages,
    )
    # Extract the assistant's reply text and append it as the next turn.
    reply_text = response.content[0].text
    messages.append({"role": "assistant", "content": reply_text})

    # Track token usage. Note input grows every turn because the whole
    # history is re-sent each call — that's the cost of statelessness.
    cumulative_input += response.usage.input_tokens
    cumulative_output += response.usage.output_tokens
    print(
        f"  [tokens] this turn: in={response.usage.input_tokens} "
        f"out={response.usage.output_tokens} | "
        f"cumulative: in={cumulative_input} out={cumulative_output} "
        f"total={cumulative_input + cumulative_output}"
    )
    return reply_text


def ask_stateless(user_text: str) -> str:
    # Sends ONLY the current turn — no accumulated history.
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": user_text}],
    )
    return response.content[0].text


print("Turn 1:", ask("My name is Rich. Remember it."))
print("Turn 2:", ask("What's 2 + 2?"))
print("Turn 3:", ask("What's my name?"))

print(f"\nFinal messages list has {len(messages)} entries.")
print("\nFull messages list:")
print(json.dumps(messages, indent=2))

print("\n--- Stateless (no replay) ---")
print("Turn 1:", ask_stateless("My name is Rich. Remember it."))
print("Turn 3:", ask_stateless("What's my name?"))
