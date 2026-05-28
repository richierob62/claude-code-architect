from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()


def show(label: str, **kwargs):
    response = client.messages.create(model="claude-haiku-4-5", **kwargs)
    print(
        f"{label}: stop_reason={response.stop_reason!r}, output_tokens={response.usage.output_tokens}"
    )


# 1. Natural finish → "end_turn"
show(
    "end_turn",
    max_tokens=500,
    messages=[{"role": "user", "content": "Reply with exactly: OK"}],
)

# 2. Truncation → "max_tokens"
show(
    "max_tokens",
    max_tokens=5,  # absurdly low, will truncate
    messages=[{"role": "user", "content": "Write a 200-word essay about clouds."}],
)

# 3. Custom stop sequence → "stop_sequence"
show(
    "stop_sequence",
    max_tokens=500,
    stop_sequences=["STOP_HERE"],
    messages=[{"role": "user", "content": "Count: 1, 2, 3, STOP_HERE, 4, 5."}],
)
