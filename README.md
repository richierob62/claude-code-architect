# Claude Certified Architect — Foundations: A Self-Guided Course

A from-zero-to-cert-ready study course for Anthropic's **Claude Certified Architect — Foundations** exam. Built as a sequence of ~15-minute lessons that each end with a small thing you've built and run against the live Anthropic API, not a thing you've read about.

If you're preparing for the exam, fork or clone this repo and work through the lessons in order. Every lesson assumes the previous lesson is done.

> **Disclaimer**: This is an independent study resource, not an official Anthropic product. The exam is administered by Anthropic; this course is one learner's structured path through the published exam objectives, designed so others can follow along.

---

## What the exam covers

The Foundations exam validates that you can make sound architectural decisions when building production systems with the four core Claude technologies:

- **Claude API** — the underlying messages + tool-use surface
- **Claude Agent SDK** — agentic loops, subagents, hooks, the `Task` tool
- **Model Context Protocol (MCP)** — server/tool/resource design, `.mcp.json` configuration
- **Claude Code** — `CLAUDE.md` hierarchy, slash commands, skills, plan mode, CI integration

Format is multiple-choice, scenario-based. Each question hands you a realistic production situation (a misbehaving customer-support agent, a flaky multi-agent research pipeline, a noisy CI code-review bot) and asks you to pick the highest-leverage intervention from four plausible options. The wrong answers are usually wrong because they over-engineer, under-engineer, or address a symptom instead of the root cause — so the exam is really testing judgment, not recall.

### Domains and weights

| # | Domain | Weight |
|---|---|---|
| 1 | **Agentic Architecture & Orchestration** — agentic loops, `stop_reason` handling, coordinator/subagent patterns, hooks, task decomposition, session resumption + forking | **27%** |
| 2 | **Tool Design & MCP Integration** — tool descriptions, structured error responses, tool distribution across agents, `tool_choice`, MCP server scoping, built-in tools (Read/Write/Edit/Bash/Grep/Glob) | **18%** |
| 3 | **Claude Code Configuration & Workflows** — `CLAUDE.md` hierarchy, `.claude/rules/` with glob path-scoping, custom slash commands, skills with `context: fork`, plan mode vs direct execution, CI integration | **20%** |
| 4 | **Prompt Engineering & Structured Output** — explicit criteria over vague instructions, few-shot prompting, `tool_use` with JSON schemas, Pydantic validation-retry loops, Message Batches API, multi-pass review architectures | **20%** |
| 5 | **Context Management & Reliability** — long-conversation context preservation, escalation calibration, structured error propagation, large-codebase exploration, human-review workflows, multi-source provenance | **15%** |

The exam draws 4 scenarios from a published pool of 6:

1. **Customer Support Resolution Agent** (D1, D2, D5)
2. **Code Generation with Claude Code** (D3, D5)
3. **Multi-Agent Research System** (D1, D2, D5)
4. **Developer Productivity with Claude** (D2, D3, D1)
5. **Claude Code for Continuous Integration** (D3, D4)
6. **Structured Data Extraction** (D4, D5)

This course's lesson modules map onto the domains in roughly weight-proportional depth.

### Source-of-truth study guide

The authoritative exam guide is **"Claude Certified Architect – Foundations Certification Exam Guide"**, published by Anthropic. It's marked confidential, so it's not redistributed in this repo. If you're preparing for the exam, get the guide from Anthropic's certification program directly. This course's lessons are aligned to its task statements but written in original prose.

---

## What you'll build

A short list of the artifacts you'll actually create and run across the course:

- A bare-metal agentic loop that drives Claude through a multi-turn tool-use conversation by inspecting `stop_reason`
- A customer-lookup agent with structured error responses (`isError`, `errorCategory`, `isRetryable`) and a programmatic hook that blocks policy-violating actions
- A working MCP server in Python (FastMCP) with tools, resources, and good differentiating descriptions
- A coordinator/subagent system using the Claude Agent SDK that spawns parallel subagents via the `Task` tool with explicit context passing
- A Claude Code configuration with a `CLAUDE.md` hierarchy, `.claude/rules/` glob-scoped conventions, custom slash commands, and a skill that runs with `context: fork`
- A structured-data extraction pipeline with `tool_use` + Pydantic + validation-retry feedback loops, run both synchronously and through the Message Batches API
- A multi-pass review system that separates per-file local analysis from cross-file integration analysis

Plus mock-exam sets at the end so you can pressure-test recall under exam-like conditions.

---

## Prerequisites

- **Hands-on familiarity with at least one of the four core technologies.** If you've never used Claude Code, never made a Claude API call, and never heard of MCP, this course assumes too much. Start with [Anthropic's docs](https://docs.anthropic.com) and the Claude Agent SDK quickstart first.
- **Comfort writing Python.** Most lessons are in Python (matches Anthropic's first-party docs, SDK examples, and the Pydantic-based validation patterns the exam references). A handful of lessons are in TypeScript where it's genuinely the better fit (Claude Code surfaces, MCP clients in TS projects). You don't need to be a Python expert — `uv` handles environment management for you — but you should be comfortable reading and modifying small Python scripts.
- **An Anthropic API key.** Lessons run against the real API. Total spend across the course is estimated at **$3–5**, defaulting to Haiku 4.5 for exercises. Get a key at <https://console.anthropic.com>.
- **macOS or Linux shell.** Lessons assume a Unix-like environment. Windows users should use WSL.

That's it. Lesson 00 sets up `uv`, Python 3.12, the `anthropic` SDK, and your `.env` file. If you can run `uv --version` and get a result (or are willing to install `uv` in lesson 00), you have everything you need.

---

## How to use this course

1. **Start at [`lessons/README.md`](lessons/README.md).** That's the full syllabus — 34 lessons across 8 modules, plus 6 end-of-course mock-exam scenarios.
2. **Work through the lessons in order.** Each lesson is ~15 minutes, ends with a checklist, and assumes you completed the previous one. Skipping ahead will bite you — even modules you think you know (especially Claude Code config, if you're a daily user) test patterns that aren't obvious from regular use.
3. **Build, don't just read.** Every lesson has a hands-on component. Type the code, run it, look at the response objects, do the exercise. The exam tests *judgment*, and judgment comes from having seen the patterns fail and succeed in your own terminal.
4. **Track your progress in `lessons/README.md`.** Tick the boxes (`- [ ]` → `- [x]`) as you finish each lesson. This is your only progress signal.
5. **Use `session-notes.md` if you're working with Claude Code.** If you have Claude Code installed and run `/handoff`, Claude will maintain a local `session-notes.md` capturing your progress and sticking points so it can pick up cleanly across sessions. This file is gitignored — yours stays yours.
6. **Take the mock scenarios at the end.** They mirror the real exam's scenario format and difficulty. If you're consistently getting 80%+ on the mocks, you're ready.

### Estimated time investment

- Per lesson: ~15 min, plus build/exercise time. Budget 20–30 min realistically.
- Full course: ~12–15 hours of focused work, spread however you like.
- Mock exam: ~1.5–2 hours.

---

## Repository layout

```
.
├── README.md              ← you are here
├── CLAUDE.md              ← Claude Code project instructions (if you're using Claude Code)
├── lessons/
│   ├── README.md          ← syllabus, the real entry point
│   ├── 00-setup.md        ← first lesson: uv + Python + API key
│   ├── 01-..., 02-...     ← lessons in order
│   ├── scripts/           ← runnable code you write during lessons
│   └── mock/              ← M1–M6 mock-exam scenarios (end of course)
├── .claude/
│   └── settings.json      ← minimal permissions for Claude Code
└── .vscode/
    └── settings.json      ← formatOnSave
```

Files intentionally gitignored:
- `test-guidelines.md` — the Anthropic exam guide (confidential, not redistributed)
- `session-notes.md` — personal continuity memory for the original author / any cloner using Claude Code
- `.env` — your `ANTHROPIC_API_KEY` lives here, never commit it

---

## Contributing

Issues and PRs welcome. Especially valuable:

- **Lesson errata.** If a lesson's code doesn't run, an API surface has changed, or an explanation is wrong, please file an issue with the lesson number and what you saw.
- **Mock-exam additions.** More high-quality scenario questions improve the course for everyone.
- **Translations of the lessons to other languages.**

Not welcome: copies of the Anthropic exam guide, or attempts to reverse-engineer specific exam questions. The point is to learn the underlying material well enough that any scenario the exam throws at you is one you can reason through from first principles.

---

## License

MIT. See [`LICENSE`](LICENSE) if present, otherwise consider this MIT-licensed by default. The Anthropic exam guide referenced (but not included) belongs to Anthropic and is subject to their own terms.
