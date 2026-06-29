# Building Agentic Systems with Claude — A Mastery Course

A hands-on curriculum for genuinely understanding how to design, build, and operate agentic AI systems with Claude. Each lesson is ~15 minutes of focused work with a real build that you run and verify. Lessons depend on the ones before them — go in order.

> **What this course is for.** The goal is *mastery of agentic concepts*, not passing a test. It happens to cover everything on the **Claude Certified Architect — Foundations** exam (that guide seeded the core curriculum), but it deliberately goes beyond the exam where real production work demands it: RAG and retrieval, AI safety, evals, streaming, cost engineering, and observability. Exam-only framing has been retired; where a topic is exam-relevant it's noted in passing, not as the point.

**Tools**: Python primary (matches the Anthropic/industry default for the Agent SDK, MCP, Pydantic), TypeScript where genuinely warranted. Pydantic for schema validation. `uv` for Python env management. Real Anthropic API calls against Haiku 4.5 for builds (cheap; the whole course runs in a few dollars).

**Provider note**: This course teaches **Anthropic-native** patterns (Claude API, Agent SDK, MCP, Pydantic). Where a pattern is provider-agnostic (RAG, streaming, structured output, tool use), lessons note the **OpenAI / Zod / TypeScript** equivalent so the concepts transfer directly to other stacks — including the [AI Integration Portfolio](https://github.com/richierob62/ai-integration-portfolio) this course's capstone builds toward.

---

## How the course is organized

The course moves from fundamentals → agentic orchestration → tooling → configuration → structured output → retrieval & production concerns → reliability → evaluation → a real capstone.

- **Lessons 00–34** are the core sequence (agentic foundations + Claude Code + structured output + context/reliability).
- **Lessons 35–44** extend into production-grade topics the core sequence doesn't reach: session management, streaming, RAG, safety, cost/observability, evals, calibration.
- **The Capstone** replaces abstract exam scenarios with building real pieces of the AI Integration Portfolio, applying everything learned.

**How to use it**: Open the next unchecked lesson. Read, do the build, run the exercises. Tick the box (`- [ ]` → `- [x]`) when done so we both know where you are. Ask anything mid-lesson — answers come in chat without breaking the file.

---

## Module A — Foundations

The Claude API mental model and the tool-use primitive everything else is built on.

- [ ] [00 — Environment setup: uv, Python, API key, hello-world](./00-setup.md)
- [ ] [01 — The Claude API mental model: messages, stop_reason, system](./01-api-mental-model.md)
- [ ] [02 — Tool use basics: the tool_use ↔ tool_result dance](./02-tool-use-basics.md)

## Module B — Agentic Loops

The heart of agentic systems: the loop that lets a model take multi-step action.

- [ ] [03 — Anatomy of the agentic loop](./03-agentic-loop.md)
- [ ] [04 — Workflow patterns: the agentic-systems catalog](./04-workflow-patterns.md)
- [ ] [05 — Loop anti-patterns: text-parsing for completion, iteration caps as primary stop](./05-loop-antipatterns.md)
- [ ] [06 — End-to-end multi-turn: build a customer-lookup agent](./06-customer-lookup-agent.md)
- [ ] [07 — Structured errors: isError, errorCategory, isRetryable](./07-structured-errors.md)
- [ ] [08 — tool_choice: auto vs any vs forced](./08-tool-choice.md)

## Module C — MCP Deep Dive

Tools as a reusable, interoperable layer via the Model Context Protocol.

- [ ] [09 — MCP mental model: tools vs resources, the protocol](./09-mcp-mental-model.md)
- [ ] [10 — Build your first MCP server (FastMCP)](./10-fastmcp-server.md)
- [ ] [11 — Agent-Computer Interface (ACI): tool description craft, format choice, poka-yoke](./11-tool-descriptions.md)
- [ ] [12 — .mcp.json: project vs user scope, env var expansion, multi-server](./12-mcp-json-config.md)

## Module D — The Claude Agent SDK & Multi-Agent Orchestration

Stop hand-rolling the loop. Build coordinators, subagents, parallel delegation, hooks — and the session-management and streaming concerns that come with real agents.

- [ ] [13 — SDK vs raw API: when to use which](./13-sdk-vs-raw-api.md)
- [ ] [14 — ClaudeAgentOptions & your first query(): system prompts, tool gating, model selection](./14-agent-definition.md)
- [ ] [15 — Subagent spawning: explicit context passing](./15-subagent-spawning.md)
- [ ] [16 — Coordinator/subagent (orchestrator-workers) build](./16-coordinator-pattern.md)
- [ ] [17 — Parallel subagent calls in one turn (parallelization–sectioning)](./17-parallel-subagents.md)
- [ ] [18 — Hooks: PostToolUse normalization + tool-call interception + multi-agent error propagation](./18-hooks.md)
- [ ] [35 — Session management: --resume, fork_session, resume-vs-fresh judgment](./35-session-management.md) *(new)*
- [ ] [36 — Streaming agent output & UX: partial messages, surfacing tool progress](./36-streaming-ux.md) *(new; provider-agnostic — note OpenAI SSE equivalent)*

## Module E — Claude Code Configuration & Workflows

Configuring Claude Code itself as an agentic engineering environment.

- [ ] [19 — CLAUDE.md hierarchy, @import, and the /memory command](./19-claudemd-hierarchy.md)
- [ ] [20 — .claude/rules/ with glob path-scoping](./20-claude-rules.md)
- [ ] [21 — Custom slash commands and skills (context: fork, allowed-tools)](./21-commands-and-skills.md)
- [ ] [22 — Plan mode vs direct execution (and the Explore subagent)](./22-plan-mode.md)
- [ ] [23 — Claude Code in CI: -p, --output-format json, --json-schema](./23-claude-code-ci.md)

## Module F — Structured Output & Extraction

Getting reliable, schema-valid data out of a model — by hand, then with the libraries that package it.

- [ ] [24 — Schema design: required/optional/nullable, enums + 'other'+detail](./24-schema-design.md)
- [ ] [25 — tool_use as the structured-output mechanism](./25-tool-use-structured-output.md)
- [ ] [26 — Pydantic validation + retry-with-error-feedback (incl. self-correction fields)](./26-validation-retry.md)
- [ ] [27 — Few-shot prompting for ambiguity and false-positive control](./27-few-shot.md)
- [ ] [28 — Message Batches API: when, how, custom_id, failures](./28-batches.md)
- [ ] [37 — Structured-output libraries: Instructor & the native-vs-library trade-off](./37-instructor-libraries.md) *(new; Anthropic-native here, note Instructor/Zod equivalents)*

## Module G — Retrieval, Safety & Production Concerns

What production agents need that the fundamentals don't cover: retrieval-augmented generation, defending against adversarial input, and engineering for cost and observability.

- [ ] [38 — RAG fundamentals: embeddings, vector search, chunking, retrieval](./38-rag-fundamentals.md) *(new)*
- [ ] [39 — Prompt-injection & AI safety: input/output guards, rate limiting](./39-ai-safety.md) *(new)*
- [ ] [40 — Cost & latency engineering + observability: prompt caching (for real), model routing, per-call tracing & metrics](./40-cost-observability.md) *(new)*

## Module H — Context Management & Reliability

Keeping long-running, multi-step agents accurate as context grows.

- [ ] [29 — Case-facts blocks: extracting transactional facts](./29-case-facts.md)
- [ ] [30 — Trimming tool outputs before accumulation](./30-trim-tool-outputs.md)
- [ ] [31 — Lost-in-the-middle and position-aware input ordering](./31-lost-in-the-middle.md)
- [ ] [32 — Escalation calibration: explicit criteria over sentiment/confidence](./32-escalation.md)
- [ ] [33 — Provenance: claim-source mappings through synthesis](./33-provenance.md)
- [ ] [41 — Working beyond the context window: scratchpad/state files, /compact, crash-recovery manifests](./41-large-codebase-context.md) *(new)*

## Module I — Evaluation & Self-Review

Measuring agent quality and trusting (or routing) the output.

- [ ] [34 — Independent-instance review (multiple evaluators); per-file + cross-file passes](./34-multi-pass-review.md)
- [ ] [42 — Evaluating agents: eval sets, LLM-as-judge, regression harness](./42-evals.md) *(new)*
- [ ] [43 — Confidence calibration & human review: stratified sampling, field-level confidence, confidence-based routing](./43-confidence-calibration.md) *(new)*

## Module J — Capstone: The AI Integration Portfolio

Apply everything by building real pieces of the [AI Integration Portfolio](https://github.com/richierob62/ai-integration-portfolio). These replace the old abstract exam scenarios — the portfolio is the proving ground.

- [ ] [44 — Capstone: build the flagship's RAG retrieval + Answer Inspector Panel (sources, retrieval trace, metrics, provenance)](./44-capstone.md) *(new; further capstone pieces — support-bot agentic loop, tool-agent, observability wiring — scoped as we go)*

---

## Optional — Exam drill (for certification)

If you do decide to sit the **Claude Certified Architect — Foundations** exam, these six scenario walkthroughs are practice drills. They are no longer the course's ending — the capstone is — but they remain useful for exam rehearsal.

- [ ] [M1 — Customer Support Resolution Agent](./mock/M1-customer-support.md)
- [ ] [M2 — Code Generation with Claude Code](./mock/M2-code-generation.md)
- [ ] [M3 — Multi-Agent Research System](./mock/M3-multi-agent-research.md)
- [ ] [M4 — Developer Productivity with Claude](./mock/M4-dev-productivity.md)
- [ ] [M5 — Claude Code for CI](./mock/M5-ci.md)
- [ ] [M6 — Structured Data Extraction](./mock/M6-extraction.md)

---

### Notes on structure

- **Existing lessons 00–34 keep their numbers and filenames** so completion state and cross-references stay intact. New lessons are numbered **35–44** and slotted into the module where they belong pedagogically (read in module order, not strict numeric order — the list above is the intended reading order).
- **New lessons (35–44)** are written reactively, same as the rest — one at a time, after the prior one is done.
- The capstone (Module J) grows as you complete it; lesson 44 is the first piece, with more scoped against the portfolio as we go.
