# Lesson 00 — Environment setup

**Time**: ~15 minutes
**Prerequisites**: none
**Goal**: A working Python 3.12 environment in this repo, the `anthropic` SDK installed, your API key wired up, and a verified hello-world call to Claude.

## Why this matters for the exam

It doesn't, directly — but every lesson from 01 onward assumes you can `uv run python some_script.py` and get a real API response. Nailing this once means zero friction for the next 33 lessons.

## What we're going to do

1. Use `uv` to pin Python 3.12 for this project.
2. Create a `pyproject.toml` with the `anthropic` SDK.
3. Put your `ANTHROPIC_API_KEY` in a `.env` file (gitignored).
4. Write `hello.py` — a 10-line script that calls Haiku 4.5 and prints the response.
5. Run it. Confirm it works. Look at the response object so you know the shape.

## Step 1 — Verify uv works

You already have `uv` installed (we checked). Confirm:

```bash
uv --version
```

You should see `uv 0.8.x` or later. If not, install it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

`uv` is the modern Python package manager — written in Rust, ~10–100× faster than `pip`, manages Python versions itself (no `pyenv` needed), and creates per-project virtual environments automatically. The Anthropic ecosystem has standardized on it.

## Step 2 — Initialize this project with uv

From the repo root (`claude-code-architect/`):

```bash
uv init --python 3.12 --no-readme
```

This creates:
- `pyproject.toml` — declares Python version and dependencies
- `.python-version` — pins 3.12 for this directory
- `main.py` — a stub (delete or ignore)
- `uv.lock` (after first sync) — locked dep versions

Then add the SDK:

```bash
uv add anthropic python-dotenv
```

`python-dotenv` is a small library for loading `.env` files. The Anthropic SDK auto-picks up `ANTHROPIC_API_KEY` from the environment.

## Step 3 — Get an API key and put it in `.env`

If you don't already have one:
1. Go to <https://console.anthropic.com>.
2. Settings → API Keys → Create Key.
3. Copy the key (starts with `sk-ant-`).

Create `.env` in the repo root (already gitignored by the `.env*` rules):

```bash
ANTHROPIC_API_KEY=sk-ant-...your-key-here...
```

Verify it's gitignored:

```bash
grep -E "^\.env" .gitignore
```

Should show `.env`, `.env.local`, and `.env.*.local`. If not, add `.env`.

## Step 4 — Write the hello-world

Create `lessons/scripts/hello.py`:

```python
"""Lesson 00 — confirm the API works end-to-end."""

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # reads .env from the cwd

client = Anthropic()  # picks up ANTHROPIC_API_KEY from env

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=200,
    messages=[
        {"role": "user", "content": "In one sentence, what is the agentic loop?"}
    ],
)

print("=== response.content ===")
print(response.content)
print()
print("=== response.stop_reason ===")
print(response.stop_reason)
print()
print("=== response.usage ===")
print(response.usage)
```

## Step 5 — Run it

```bash
uv run python lessons/scripts/hello.py
```

`uv run` auto-syncs your venv and executes the script in it — no manual `source .venv/bin/activate` needed.

Expected output (the text varies, the shape doesn't):

```
=== response.content ===
[TextBlock(citations=None, text="The agentic loop is the cycle ...", type='text')]

=== response.stop_reason ===
end_turn

=== response.usage ===
Usage(cache_creation_input_tokens=0, cache_read_input_tokens=0, input_tokens=18, output_tokens=42, ...)
```

## What to notice in the response

Three things matter for later lessons — burn these into memory:

| Field | What it is | Why it matters |
|---|---|---|
| `response.content` | A **list of content blocks**, not a string. Each block has a `type` (`text`, `tool_use`, etc.). | Every Claude response is structurally typed. Mixed-type responses (text + tool_use in one turn) are normal. |
| `response.stop_reason` | Why Claude stopped this turn. Values: `end_turn`, `tool_use`, `max_tokens`, `stop_sequence`, `pause_turn`, `refusal`. | **This is the heart of the agentic loop.** Lesson 03 is built entirely around inspecting this value. The exam will hammer it. |
| `response.usage` | Input/output token counts (and cache hits, if used). | Cost and context-window budgeting. Lessons in Module G use this directly. |

## Exercise (5 min)

Modify `hello.py` to ask Claude to count to 10000 with `max_tokens=50`. Run it. Look at `response.stop_reason`.

You should see `max_tokens` instead of `end_turn`. This is your first taste of "the stop reason tells you what to do next" — in this case, the response is truncated and your loop (if you had one) would need to decide whether to continue or give up. Save the contrast for Lesson 03.

## Done check

- [ ] `uv run python -c "from anthropic import Anthropic; print(Anthropic().messages.create(model='claude-haiku-4-5', max_tokens=10, messages=[{'role':'user','content':'hi'}]).content[0].text)"` prints a short greeting.
- [ ] `.env` is gitignored.
- [ ] You ran the exercise and saw `stop_reason == 'max_tokens'`.

Tick this lesson off in `lessons/README.md` and move to [01 — The Claude API mental model](./01-api-mental-model.md).
