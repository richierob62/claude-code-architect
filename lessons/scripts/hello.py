"""Lesson 00 — confirm the API works end-to-end."""

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # reads .env from the cwd

client = Anthropic()  # picks up ANTHROPIC_API_KEY from env

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=200,
    messages=[{"role": "user", "content": "In one sentence, what is the agentic loop?"}],
)

print("=== response.content ===")
print(response.content)
print()
print("=== response.stop_reason ===")
print(response.stop_reason)
print()
print("=== response.usage ===")
print(response.usage)
print("=== client innards ===")
print(dir(client.messages))
