# Claude Certified Architect — Foundations: Study Plan

This is your personal curriculum for the Claude Certified Architect (Foundations) exam, built from `../test-guidelines.md`. Each lesson is ~15 minutes of focused work with a hands-on build. Lessons depend on the ones before them — go in order.

**Tools**: Python primary (matches Anthropic/industry default), TypeScript where genuinely warranted (Claude Code surfaces, your Next.js work). Pydantic for schema validation. `uv` for Python env management. Real Anthropic API calls against Haiku 4.5 for builds (cheap; ~$3–5 total).

**Domain weights** (so you know where the points are):

- D1 Agentic Architecture & Orchestration — **27%**
- D3 Claude Code Configuration & Workflows — **20%**
- D4 Prompt Engineering & Structured Output — **20%**
- D2 Tool Design & MCP Integration — **18%**
- D5 Context Management & Reliability — **15%**

## Module A — Foundations (3 lessons)

- [x] [00 — Environment setup: uv, Python, API key, hello-world](./00-setup.md)
- [x] [01 — The Claude API mental model: messages, stop_reason, system](./01-api-mental-model.md)
- [x] [02 — Tool use basics: the tool_use ↔ tool_result dance](./02-tool-use-basics.md)

## Module B — Agentic Loops (Domain 1 core, 5 lessons)

- [ ] [03 — Anatomy of the agentic loop](./03-agentic-loop.md)
- [ ] [04 — Loop anti-patterns: text-parsing for completion, iteration caps as primary stop](./04-loop-antipatterns.md)
- [ ] [05 — End-to-end multi-turn: build a customer-lookup agent](./05-customer-lookup-agent.md)
- [ ] [06 — Structured errors: isError, errorCategory, isRetryable](./06-structured-errors.md)
- [ ] [07 — tool_choice: auto vs any vs forced](./07-tool-choice.md)

## Module C — MCP Deep Dive (Domain 2, 4 lessons)

- [ ] [08 — MCP mental model: tools vs resources, the protocol](./08-mcp-mental-model.md)
- [ ] [09 — Build your first MCP server (FastMCP)](./09-fastmcp-server.md)
- [ ] [10 — Tool description craft: differentiating similar tools](./10-tool-descriptions.md)
- [ ] [11 — .mcp.json: project vs user scope, env var expansion, multi-server](./11-mcp-json-config.md)

## Module D — Claude Agent SDK (Domain 1 advanced, 6 lessons)

- [ ] [12 — SDK vs raw API: when to use which](./12-sdk-vs-raw-api.md)
- [ ] [13 — AgentDefinition: system prompts, allowedTools, model selection](./13-agent-definition.md)
- [ ] [14 — Subagent spawning via the Task tool: explicit context passing](./14-subagent-spawning.md)
- [ ] [15 — Coordinator/subagent (hub-and-spoke) build](./15-coordinator-pattern.md)
- [ ] [16 — Parallel subagent calls in one turn](./16-parallel-subagents.md)
- [ ] [17 — Hooks: PostToolUse normalization + tool-call interception](./17-hooks.md)

## Module E — Claude Code Configuration (Domain 3, 5 lessons)

- [ ] [18 — CLAUDE.md hierarchy and @import](./18-claudemd-hierarchy.md)
- [ ] [19 — .claude/rules/ with glob path-scoping](./19-claude-rules.md)
- [ ] [20 — Custom slash commands and skills (context: fork, allowed-tools)](./20-commands-and-skills.md)
- [ ] [21 — Plan mode vs direct execution](./21-plan-mode.md)
- [ ] [22 — Claude Code in CI: -p, --output-format json, --json-schema](./22-claude-code-ci.md)

## Module F — Structured Output & Extraction (Domain 4, 5 lessons)

- [ ] [23 — Schema design: required/optional/nullable, enums + 'other'+detail](./23-schema-design.md)
- [ ] [24 — tool_use as the structured-output mechanism](./24-tool-use-structured-output.md)
- [ ] [25 — Pydantic validation + retry-with-error-feedback](./25-validation-retry.md)
- [ ] [26 — Few-shot prompting for ambiguity and false-positive control](./26-few-shot.md)
- [ ] [27 — Message Batches API: when, how, custom_id, failures](./27-batches.md)

## Module G — Context & Reliability (Domain 5, 5 lessons)

- [ ] [28 — Case-facts blocks: extracting transactional facts](./28-case-facts.md)
- [ ] [29 — Trimming tool outputs before accumulation](./29-trim-tool-outputs.md)
- [ ] [30 — Lost-in-the-middle and position-aware input ordering](./30-lost-in-the-middle.md)
- [ ] [31 — Escalation calibration: explicit criteria over sentiment/confidence](./31-escalation.md)
- [ ] [32 — Provenance: claim-source mappings through synthesis](./32-provenance.md)

## Module H — Multi-pass & Self-Review (1 lesson)

- [ ] [33 — Independent-instance review; per-file + cross-file passes](./33-multi-pass-review.md)

## Mock Exam (6 scenarios)

- [ ] [M1 — Customer Support Resolution Agent](./mock/M1-customer-support.md)
- [ ] [M2 — Code Generation with Claude Code](./mock/M2-code-generation.md)
- [ ] [M3 — Multi-Agent Research System](./mock/M3-multi-agent-research.md)
- [ ] [M4 — Developer Productivity with Claude](./mock/M4-dev-productivity.md)
- [ ] [M5 — Claude Code for CI](./mock/M5-ci.md)
- [ ] [M6 — Structured Data Extraction](./mock/M6-extraction.md)

---

**How to use**: Open the next unchecked lesson. Read, do the build, run the exercises. When you're done, tick the box (literally `- [ ]` → `- [x]` in this file) so we both know where you are. Ask me anything mid-lesson — I'll answer in chat without breaking the file. Every 5–7 lessons we'll do a short course-correction.

**When to skip**: Don't. Even the modules you think you know (Claude Code config, especially) have exam-specific patterns that aren't always obvious from daily use — e.g., glob-pattern rules vs subdirectory CLAUDE.md, `context: fork`, the `--json-schema` flag.
