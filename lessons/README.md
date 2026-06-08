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

## Module B — Agentic Loops (Domain 1 core, 6 lessons)

- [x] [03 — Anatomy of the agentic loop](./03-agentic-loop.md)
- [x] [04 — Workflow patterns: the agentic-systems catalog](./04-workflow-patterns.md)
- [x] [05 — Loop anti-patterns: text-parsing for completion, iteration caps as primary stop](./05-loop-antipatterns.md)
- [x] [06 — End-to-end multi-turn: build a customer-lookup agent](./06-customer-lookup-agent.md)
- [x] [07 — Structured errors: isError, errorCategory, isRetryable](./07-structured-errors.md)
- [ ] [08 — tool_choice: auto vs any vs forced](./08-tool-choice.md)

## Module C — MCP Deep Dive (Domain 2, 4 lessons)

- [ ] [09 — MCP mental model: tools vs resources, the protocol](./09-mcp-mental-model.md)
- [ ] [10 — Build your first MCP server (FastMCP)](./10-fastmcp-server.md)
- [ ] [11 — Agent-Computer Interface (ACI): tool description craft, format choice, poka-yoke](./11-tool-descriptions.md)
- [ ] [12 — .mcp.json: project vs user scope, env var expansion, multi-server](./12-mcp-json-config.md)

## Module D — Claude Agent SDK (Domain 1 advanced, 6 lessons)

- [ ] [13 — SDK vs raw API: when to use which](./13-sdk-vs-raw-api.md)
- [ ] [14 — AgentDefinition: system prompts, allowedTools, model selection](./14-agent-definition.md)
- [ ] [15 — Subagent spawning via the Task tool: explicit context passing](./15-subagent-spawning.md)
- [ ] [16 — Coordinator/subagent (orchestrator-workers) build](./16-coordinator-pattern.md)
- [ ] [17 — Parallel subagent calls in one turn (parallelization–sectioning)](./17-parallel-subagents.md)
- [ ] [18 — Hooks: PostToolUse normalization + tool-call interception](./18-hooks.md)

## Module E — Claude Code Configuration (Domain 3, 5 lessons)

- [ ] [19 — CLAUDE.md hierarchy and @import](./19-claudemd-hierarchy.md)
- [ ] [20 — .claude/rules/ with glob path-scoping](./20-claude-rules.md)
- [ ] [21 — Custom slash commands and skills (context: fork, allowed-tools)](./21-commands-and-skills.md)
- [ ] [22 — Plan mode vs direct execution](./22-plan-mode.md)
- [ ] [23 — Claude Code in CI: -p, --output-format json, --json-schema](./23-claude-code-ci.md)

## Module F — Structured Output & Extraction (Domain 4, 5 lessons)

- [ ] [24 — Schema design: required/optional/nullable, enums + 'other'+detail](./24-schema-design.md)
- [ ] [25 — tool_use as the structured-output mechanism](./25-tool-use-structured-output.md)
- [ ] [26 — Pydantic validation + retry-with-error-feedback (evaluator-optimizer)](./26-validation-retry.md)
- [ ] [27 — Few-shot prompting for ambiguity and false-positive control](./27-few-shot.md)
- [ ] [28 — Message Batches API: when, how, custom_id, failures](./28-batches.md)

## Module G — Context & Reliability (Domain 5, 5 lessons)

- [ ] [29 — Case-facts blocks: extracting transactional facts](./29-case-facts.md)
- [ ] [30 — Trimming tool outputs before accumulation](./30-trim-tool-outputs.md)
- [ ] [31 — Lost-in-the-middle and position-aware input ordering](./31-lost-in-the-middle.md)
- [ ] [32 — Escalation calibration: explicit criteria over sentiment/confidence](./32-escalation.md)
- [ ] [33 — Provenance: claim-source mappings through synthesis](./33-provenance.md)

## Module H — Multi-pass & Self-Review (1 lesson)

- [ ] [34 — Independent-instance review (evaluator-optimizer with multiple evaluators); per-file + cross-file passes](./34-multi-pass-review.md)

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
