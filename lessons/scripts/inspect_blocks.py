from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=300,
    messages=[{"role": "user", "content": "Say hi in one short sentence."}],
)

print(f"\nstop_reason: {response.stop_reason}")
print(f"\nusage: {response.usage}")
print(f"\ncontent is a {type(response.content).__name__} with {len(response.content)} block(s):")
for i, block in enumerate(response.content):
    print(f"\n  [{i}] type={type(block).__name__} → {block!r}")
