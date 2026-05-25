# claude-code-architect

This project is a personal study course for the **Claude Certified Architect — Foundations** exam. The source-of-truth exam guide is [`test-guidelines.md`](test-guidelines.md). The full curriculum lives in [`lessons/`](lessons/) with the syllabus index in [`lessons/README.md`](lessons/README.md).

Global instructions in `~/.claude/CLAUDE.md` apply.

## Files to Ignore
- `scratch-pad.md` — User's personal scratch pad, if present. Do not modify, delete, or reference.

---

## Session Notes (Authoritative Project Memory)

1. **You are the sole owner and steward** of [`session-notes.md`](session-notes.md). Treat it as the **single source of truth** for this project.

2. The purpose of this file is to **persist all knowledge required for any LLM (including yourself)** to resume teaching Rich at any point in the future without context loss. The two anchor sections are **Learner Profile** (read every session start — drives explanation depth and language choice) and **Pickup when resuming** (read first if you only read one section).

3. **Continuously update this file during the session.** Assume sessions may end abruptly and optimize for zero critical knowledge loss. You do not need permission. Default to updating it whenever:
   - Rich completes a lesson (add a row to the Lesson Log)
   - Rich gets stuck on a concept (add to Sticking Points; weave a callback into the next lesson)
   - Rich asks a question that needs follow-up (add to Open Questions)
   - A teaching decision or convention is established (e.g. "we're using `uv` not `pip`")
   - A pacing or plan change is agreed with Rich

4. **Aggressively prune obsolete or superseded information.** Represent current truth, not history. The "Permanent skeleton" block at the bottom of `session-notes.md` lists the sections that must always exist (even if empty). Everything else is pruneable.

5. **Pruning trigger (event-based):** every time you update `session-notes.md`, first do a prune pass:
   - Keep only the most recent `## Handoff State (...)` entry. Lift any orphan facts into the appropriate permanent section before deleting older entries.
   - Delete any section labeled "Historical / Deprecated" once its load-bearing content has been lifted.
   - Never prune the permanent skeleton sections.

6. **Single-writer discipline.** This is not a git/worktree project — no PRs, no merge conflicts. Updates happen freely during sessions. The "running-log files in git worktrees" universal rule from `~/.claude/CLAUDE.md` does not apply here.

7. **Context-full protocol.** When your context reaches ~80%, immediately flush everything needed to resume into `session-notes.md` and prompt Rich to end the session. He'll start a new one with `/start` and you'll pick up from the Handoff State block.

---

## Course conventions

- **Language**: Python primary (matches Anthropic/industry default for Agent SDK, MCP, Pydantic). TypeScript only where genuinely warranted — Claude Code surfaces, Next.js integration patterns, MCP clients in TS projects.
- **Python tooling**: `uv` for env + dep management. `uv run python <script>` for execution; `uv add <pkg>` for deps. No `pip`, no `pyenv`, no `poetry`.
- **Default model for lesson exercises**: `claude-haiku-4-5`. Switch up only when a specific lesson requires it.
- **Pacing**: reactive, not batch. Write the next lesson only after Rich reports completion of the current one. Each lesson is ~15 min.
- **API costs**: Rich has approved ~$3–5 across the course. Use Haiku, keep `max_tokens` modest.

## Commands

The standard global commands are symlinked into `.claude/commands/` and available here:

| Command | What it does |
|---|---|
| `/handoff` | Update `session-notes.md` with current context. Run automatically when context hits ~70%, when a lesson completes, or before ending a session. |
| `/cheatsheet` | List all available commands and skills with trigger phrases. |
| `/grill-me` | Stress-test a plan via interview. Useful before locking lesson direction. |
| `/link-claude`, `/organize-skills`, `/review`, `/deploy-check`, `/style` | Stock global commands. Mostly not applicable to a tutorial project but available. |

A project `/start` command can be added later if useful (it would read `session-notes.md` + `test-guidelines.md` + the latest lesson and summarize state).
