# Session Notes — Claude Certified Architect Tutorial

## Handoff State (2026-05-25 — course scaffolded, ready for Lesson 00)

### Current Task
Teaching Rich the Claude Certified Architect — Foundations curriculum. 34-lesson + 6-mock-scenario plan locked in [`lessons/README.md`](lessons/README.md). Reactive pacing — one lesson written at a time, after Rich completes the previous and reports back.

### Completed This Session
- [x] Carried agentic infra over from `lago_west` (`.claude/commands` symlinks, `.claude/settings.json`, `.vscode/settings.json`, `.gitignore`, stub `CLAUDE.md`)
- [x] Grilled Rich to lock plan: Python primary + TS where warranted; heavy hands-on; deep mastery (no time pressure); real API calls allowed (~$3–5 budget); 4–6 mock scenarios at the end
- [x] Probed local env: `uv 0.8.3` present; system `python3` is 3.7.3 (too old, but `uv` will pin 3.12 per-project); no `ANTHROPIC_API_KEY` in shell yet; `pyenv` not installed (don't need it — uv handles versions)
- [x] Wrote `lessons/README.md` (full syllabus with weighted-domain awareness, tickable checkboxes)
- [x] Wrote `lessons/00-setup.md` (uv init → `pyproject.toml` + `anthropic` + `python-dotenv` → `.env` with API key → `hello.py` → exercise observing `stop_reason == 'max_tokens'`)
- [x] Established session-notes discipline (this file) per Rich's preference for the lago_west pattern

### In Progress
- [ ] Rich starts Lesson 00 tomorrow. Awaiting his completion signal before writing Lesson 01.

### Key Decisions Made
- **Python primary, TS where warranted.** Industry/Anthropic default. Pydantic, anthropic SDK, FastMCP, claude-agent-sdk all in Python. TS for Claude Code surfaces and Rich's Next.js sibling work.
- **`uv` over pip/poetry/pyenv.** Already installed. Manages Python versions per-project; no system Python upgrade needed.
- **Haiku 4.5 (`claude-haiku-4-5`) as the default lesson model.** Cheap; sufficient for the patterns being taught.
- **Reactive pacing, not batch-write.** One lesson at a time so each can adapt to what tripped Rich up in the previous. Rich approved.
- **session-notes adapted from lago_west pattern** (single authoritative continuity memory, continuously updated, structured skeleton + Handoff State block at top, aggressive pruning). Structural sections specific to a course — no Architecture/Security blocks; instead Curriculum Map, Learner Profile, Lesson Log, Sticking Points.

### Files Modified
- `lessons/README.md` — full syllabus
- `lessons/00-setup.md` — environment setup lesson
- `session-notes.md` — this file (new)
- `CLAUDE.md` — will add session-notes stewardship block on next edit (TODO below)

### Next Steps
1. Rich runs Lesson 00 tomorrow. He'll tell me when `hello.py` works and the `max_tokens` exercise lands as expected.
2. When he reports done, I write `lessons/01-api-mental-model.md` covering: the `messages` list shape, role alternation rules, system prompts, the content-block model (TextBlock vs ToolUseBlock etc.), the full `stop_reason` enumeration with what each value means for the *next* turn.
3. Add a stewardship block to `CLAUDE.md` declaring this file authoritative (mirrors lago_west's "Session Notes" section).

### Critical Context
- **Rich is brand-new to Python tooling.** System Python is 3.7. `uv` is installed but he hasn't used it yet. Lesson 00 has to land cleanly or every subsequent lesson is friction.
- **No `ANTHROPIC_API_KEY` in his shell.** Lesson 00 walks through console.anthropic.com → key → `.env`. If he hits a snag here it'll be before any code runs.
- **No git repo in this project.** This isn't a worktree-bearing project; the universal "running-log files in git worktrees" rule from `~/.claude/CLAUDE.md` doesn't apply. No PR cadence, no merge-conflict risk. I update this file freely during sessions.
- **Rich's profile is in `## Learner Profile` below — read it on every session start.**

---

## Curriculum Map

**Source of truth**: [`test-guidelines.md`](test-guidelines.md) — official Anthropic exam guide (1189 lines, includes content outline, sample questions, prep exercises).

**Domain weights** (drive depth of attention per module):
- D1 Agentic Architecture & Orchestration — **27%**
- D3 Claude Code Configuration & Workflows — **20%**
- D4 Prompt Engineering & Structured Output — **20%**
- D2 Tool Design & MCP Integration — **18%**
- D5 Context Management & Reliability — **15%**

**Module map** (full lesson list in `lessons/README.md`):

| Module | Lessons | Primary domain | Status |
|---|---|---|---|
| A — Foundations | 00–02 | setup + D1/D4 prerequisites | 00 written, 01–02 pending |
| B — Agentic Loops | 03–07 | D1 core | pending |
| C — MCP Deep Dive | 08–11 | D2 | pending |
| D — Claude Agent SDK | 12–17 | D1 advanced | pending |
| E — Claude Code Config | 18–22 | D3 | pending |
| F — Structured Output | 23–27 | D4 | pending |
| G — Context & Reliability | 28–32 | D5 | pending |
| H — Multi-pass Review | 33 | D4 advanced | pending |
| Mock Exam | M1–M6 | all | pending |

**Pass threshold**: 720 / 1000 scaled. Multi-choice format, 4 scenarios drawn from the 6 in the guide.

---

## Learner Profile (Rich)

Read this on every session start. Drives explanation style and lesson depth.

- **Claude Code**: daily user. Knows CLAUDE.md, slash commands, plan mode, skills, `.mcp.json`. Don't over-explain Claude Code surfaces.
- **Claude Agent SDK**: new. Treat all SDK lessons as ground-up.
- **MCP**: new to authoring servers; has only consumed via `.mcp.json`. Treat MCP server lessons as ground-up.
- **Claude API direct (`tool_use`, JSON schemas, batches)**: new. Treat as ground-up.
- **Python**: rusty (system Python is 3.7; no recent project use). Don't assume Python idioms; explain `uv`, venvs, `pyproject.toml` the first time they appear.
- **TypeScript / Next.js**: fluent. Sibling project `lago_west` is a large Next.js codebase he ships daily.
- **Working style preferences**:
  - Wants to be grilled before plans are locked.
  - Likes the lago_west session-notes pattern (this file mirrors it).
  - Prefers reactive pacing — one lesson at a time, adapt as we go.
  - Heavy hands-on (build it, don't just read about it).
  - "True mastery" goal, not just passing the test.
- **Budget**: $3–5 in Anthropic API spend across the course is fine. Default to Haiku 4.5 for exercises.
- **Time**: no deadline. Starting tomorrow (2026-05-26).

---

## Lesson Log

One row per lesson as it's completed. When Rich reports a lesson done, add a row here capturing: completion date, time spent (his estimate), what stuck, what felt shaky, anything he asked about that suggests a future-lesson reinforcement. Use this on resume to know where attention belongs.

| Lesson | Completed | Time | Stuck | Shaky | Notes |
|---|---|---|---|---|---|
| 00 — Setup | — | — | — | — | not started |

---

## Sticking Points (running)

Concepts Rich has bumped on more than once. Reinforce these in subsequent lessons (callbacks, "remember from lesson N"). Trim when a concept has clearly stuck (i.e. correctly applied in a build without prompting).

*(empty — nothing yet)*

---

## Open Questions (Rich → me)

Things Rich asked that I want to revisit after the lesson stream catches up, or that need a decision I shouldn't unilaterally make. Trim when resolved.

*(empty — nothing yet)*

---

## Pickup when resuming

The block that whoever opens this file (me or Rich after `/start`) should read first if they only read one section.

1. **What's the latest lesson Rich has on his plate?** Check the "In Progress" item in Handoff State above and the Lesson Log table. Whatever is the next unchecked lesson in `lessons/README.md` is where attention goes.
2. **Did Rich report completion since the last update?** If yes and the next lesson isn't written yet, write it now. If no, ask what's blocking him.
3. **Anything in Sticking Points?** Weave a one-line callback into the lesson being written.
4. **Anything in Open Questions?** Resolve before continuing, or surface to Rich if it needs his input.

---

## Permanent skeleton (do not prune)

These sections are the file's spine. Even when empty, keep the headers so the structure stays predictable:
- Handoff State (top, always most-recent only)
- Curriculum Map
- Learner Profile
- Lesson Log
- Sticking Points
- Open Questions
- Pickup when resuming

Everything else (dated handoff entries, deprecated notes, in-flight bookkeeping) can be pruned aggressively per the global session-notes rules.
