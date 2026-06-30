# Building Agentic Systems with Claude — A Mastery Course

A hands-on course for genuinely understanding how to design, build, and operate agentic AI systems with Claude. Built as a sequence of ~15-minute lessons that each end with a small thing you've built and run against the live Anthropic API, not a thing you've read about.

If you want to learn this material, fork or clone this repo and work through the lessons in order. Every lesson assumes the previous lesson is done.

> **What this course is for.** The goal is *mastery of agentic concepts*, not passing a test. It happens to cover everything on Anthropic's **Claude Certified Architect — Foundations** exam (that guide seeded the core curriculum), but it deliberately goes beyond the exam where real production work demands it: RAG and retrieval, AI safety, evals, streaming, cost engineering, and observability. Where a topic is exam-relevant it's noted in passing, not treated as the point. If you *do* want the cert, see [For the exam](#for-the-exam-optional) below.

> **Disclaimer**: This is an independent learning resource, not an official Anthropic product. Any certification referenced is administered by Anthropic; this course is one practitioner's structured path through the underlying material, designed so others can follow along.

---

## What you'll learn

The course teaches **Anthropic-native** patterns across the four core Claude technologies, then pushes past them into the production concerns real agentic systems need:

- **Claude API** — the messages + tool-use surface everything is built on
- **Claude Agent SDK** — agentic loops, subagents, coordinators, parallel delegation, hooks, the `Task` tool
- **Model Context Protocol (MCP)** — server/tool/resource design, `.mcp.json` configuration
- **Claude Code** — `CLAUDE.md` hierarchy, slash commands, skills, plan mode, CI integration

…plus the topics the fundamentals don't reach: **RAG & retrieval, prompt-injection defense & AI safety, evals & LLM-as-judge, streaming UX, cost/latency engineering, observability, and context-management reliability.**

Where a pattern is provider-agnostic (RAG, streaming, structured output, tool use), lessons note the **OpenAI / Zod / TypeScript** equivalent so the concepts transfer to other stacks.

---

## What you'll build

A short list of the artifacts you'll actually create and run across the course:

- A bare-metal agentic loop that drives Claude through a multi-turn tool-use conversation by inspecting `stop_reason`
- A customer-lookup agent with structured error responses (`isError`, `errorCategory`, `isRetryable`)
- A working MCP server in Python (FastMCP) with tools, resources, and good differentiating descriptions
- A coordinator/subagent system on the Claude Agent SDK — spawning subagents (sequentially *and* in parallel) via the `Task` tool with explicit context passing, plus hooks
- A Claude Code configuration: `CLAUDE.md` hierarchy, glob-scoped conventions, custom slash commands, and skills
- A structured-data extraction pipeline with `tool_use` + Pydantic + validation-retry feedback loops, run both synchronously and through the Message Batches API
- A web-ingestion tool wrapping Crawl4AI, then a RAG retrieval pipeline (embeddings, chunking, vector search)
- A multi-pass review system, an eval/LLM-as-judge harness, and confidence-based routing

### The Capstone

The course ends not with abstract exercises but with a **capstone** (Module J): you build real pieces of the [AI Integration Portfolio](https://github.com/richierob62/ai-integration-portfolio) — starting with the flagship's RAG retrieval and an Answer Inspector Panel (sources, retrieval trace, metrics, provenance), with further pieces (support-bot agentic loop, tool-agent, observability wiring) scoped as you go. The portfolio *is* the proving ground.

---

## Prerequisites

- **Hands-on familiarity with at least one of the four core technologies.** If you've never used Claude Code, never made a Claude API call, and never heard of MCP, this course assumes too much. Start with [Anthropic's docs](https://docs.anthropic.com) and the Claude Agent SDK quickstart first.
- **Comfort writing Python.** Most lessons are in Python (matches Anthropic's first-party docs, SDK examples, and the Pydantic-based validation patterns). A handful are in TypeScript where it's genuinely the better fit (Claude Code surfaces, MCP clients in TS projects). You don't need to be a Python expert — `uv` handles environment management for you — but you should be comfortable reading and modifying small Python scripts.
- **An Anthropic API key.** Lessons run against the real API. Total spend across the course is estimated at **$3–5**, defaulting to Haiku 4.5 for exercises. Get a key at <https://console.anthropic.com>.
- **macOS or Linux shell.** Lessons assume a Unix-like environment. Windows users should use WSL.

That's it. Lesson 00 sets up `uv`, Python 3.12, the SDK, and your `.env` file. If you can run `uv --version` and get a result (or are willing to install `uv` in lesson 00), you have everything you need.

---

## How to use this course

1. **Start at [`lessons/README.md`](lessons/README.md).** That's the full syllabus — 45 lessons across 10 modules (A–J), ending in the capstone.
2. **Work through the lessons in order.** Each lesson is ~15 minutes, ends with a checklist, and assumes you completed the previous one. Numbers are contiguous; just take the next unchecked one.
3. **Build, don't just read.** Every lesson has a hands-on component. Type the code, run it, look at the response objects, do the exercise. Judgment comes from having seen the patterns fail and succeed in your own terminal.
4. **Track your progress in `lessons/README.md`.** Tick the boxes (`- [ ]` → `- [x]`) as you finish each lesson.
5. **Use `session-notes.md` if you're working with Claude Code.** If you have Claude Code installed and run `/handoff`, Claude maintains a local `session-notes.md` capturing your progress and sticking points so it can pick up cleanly across sessions. This file is gitignored — yours stays yours.
6. **Finish with the capstone.** Module J applies everything to real portfolio pieces.

### Estimated time investment

- Per lesson: ~15 min, plus build/exercise time. Budget 20–30 min realistically.
- Full course: ~18–22 hours of focused work, spread however you like.

---

## For the exam (optional)

This course was seeded by Anthropic's **Claude Certified Architect — Foundations** exam guide, so it covers the exam's material thoroughly even though the exam is no longer its purpose. If you intend to sit the exam:

- The lesson content maps to the exam's five domains (Agentic Architecture & Orchestration; Tool Design & MCP; Claude Code Configuration & Workflows; Prompt Engineering & Structured Output; Context Management & Reliability).
- An **optional exam-drill module** of six scenario walkthroughs (M1–M6) lives at the end of [`lessons/README.md`](lessons/README.md) for rehearsal. These are practice drills, not the course's ending — the capstone is.
- The authoritative exam guide is published by Anthropic and marked confidential, so it is **not** redistributed here. Get it from Anthropic's certification program directly.

---

## Repository layout

```
.
├── README.md              ← you are here
├── CLAUDE.md              ← Claude Code project instructions (if you're using Claude Code)
├── lessons/
│   ├── README.md          ← syllabus, the real entry point
│   ├── 00-setup.md        ← first lesson: uv + Python + API key
│   ├── 01-..., 02-...     ← lessons in order (00–45)
│   ├── scripts/           ← runnable code you write during lessons
│   └── mock/              ← M1–M6 optional exam-drill scenarios
├── .claude/
│   └── settings.json      ← minimal permissions for Claude Code
└── .vscode/
    └── settings.json      ← formatOnSave
```

---

## Contributing

Issues and PRs welcome. Especially valuable:

- **Lesson errata.** If a lesson's code doesn't run, an API surface has changed, or an explanation is wrong, please file an issue with the lesson number and what you saw.
- **Capstone & portfolio pieces.** Improvements to the real builds in Module J.
- **Translations of the lessons to other languages.**

Not welcome: copies of any confidential Anthropic exam guide, or attempts to reverse-engineer specific exam questions. The point is to learn the underlying material well enough that any scenario is one you can reason through from first principles.

---

## License

MIT. See [`LICENSE`](LICENSE) if present, otherwise consider this MIT-licensed by default. Any Anthropic exam guide referenced (but not included) belongs to Anthropic and is subject to their own terms.
