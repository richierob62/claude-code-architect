# Curriculum Mind Map

Hierarchical mind map for the Claude Certified Architect — Foundations curriculum. One overview map establishes the spine (5 domains → modules); one detail map per module captures the actual concept leaves. Cross-domain integration points live in the final section.

**How to read it**: start with the overview to anchor yourself, then drill into whichever module you're currently studying or revising. Use the Cross-links section as your exam-prep deck — those edges are where multi-domain questions live.

**Update cadence**: Claude adds concept leaves to a module's detail map at the end of each lesson, and adds any cross-domain edges discovered. You can re-arrange/prune at module boundaries.

**Rendering**: VS Code's Markdown preview (Cmd+Shift+V) renders Mermaid natively in recent versions, or via the *Markdown Preview Mermaid Support* extension. Mermaid `mindmap` chokes on characters like `+ % & : / ( ) ,` — when in doubt, wrap a node label in `["..."]`.

---

## Overview — domains and modules

```mermaid
mindmap
  root((Claude<br/>Architect<br/>Foundations))
    ["D1 Agentic Architecture 27%"]
      Module A Foundations
      Module B Agentic Loops
      Module D Claude Agent SDK
    ["D2 Tool Design and MCP 18%"]
      Module C MCP Deep Dive
    ["D3 Claude Code Config 20%"]
      Module E Claude Code Config
    ["D4 Prompt Eng and Structured Output 20%"]
      Module F Structured Output
      Module H Multi-pass Review
    ["D5 Context and Reliability 15%"]
      Module G Context and Reliability
    Mock Scenarios
      M1 Customer Support
      M2 Code Generation
      M3 Multi-Agent Research
      M4 Dev Productivity
      M5 Claude Code CI
      M6 Data Extraction
```

---

## Module A — Foundations (D1 prereqs)

Lessons 00–02. Environment setup, API mental model, tool-use basics. Foundation for every later module.

```mermaid
mindmap
  root((Module A<br/>Foundations))
    L00 Setup
      uv pyproject.toml
      ["dotenv ANTHROPIC_API_KEY"]
      ["claude-haiku-4-5 default"]
      stop_reason max_tokens demo
    L01 API mental model
      Stateless API
        replay history every turn
        you own the memory
      system is top-level param
        not a messages entry
      content is list of blocks
        TextBlock
        ToolUseBlock
        ToolResultBlock
        ImageBlock
        ThinkingBlock
      stop_reason control signal
        end_turn done
        max_tokens truncated
        stop_sequence custom
        tool_use mid-flight pause
        pause_turn server-tool resume
        refusal safety decline
      ["usage input and output tokens"]
      role alternation user assistant
    L02 Tool use basics
      Tool is JSON-Schema contract
        name description input_schema
        Claude requests you execute
      Four-step round-trip
        send plus tools
        tool_use block id name input
        execute plus tool_result
        end_turn final answer
      tool_result is user-role message
        preserves role alternation
      tool_use_id is the join key
        append assistant turn verbatim
      tools is an offer not a command
        end_turn when no tool needed
```

## Module B — Agentic Loops (D1 core)

Lessons 03–07. The heart of D1 — the highest-weighted domain. The loop pattern, anti-patterns, error handling, and tool_choice.

```mermaid
mindmap
  root((Module B<br/>Agentic Loops))
    L03 Anatomy of the loop
      stop_reason is the loop condition
        end_turn is the only normal exit
        tool_use means continue
        unexpected stop_reason handle explicitly
      Loop body
        append assistant turn verbatim
        run every tool_use block
        append user tool_results message
      Chained tool calls
        call N input depends on call N-1 output
        find_id then get_details pattern
      max_iters is a safety net
        fires only on runaway bug
        not the primary termination
    L04 Loop anti-patterns
      not yet written
    L05 Customer-lookup agent
      not yet written
    L06 Structured errors
      not yet written
    L07 tool_choice
      not yet written
```

## Module C — MCP Deep Dive (D2)

Lessons 08–11. MCP protocol, authoring servers with FastMCP, tool-description craft, `.mcp.json` configuration.

```mermaid
mindmap
  root((Module C<br/>MCP Deep Dive))
    L08 MCP mental model
      not yet written
    L09 FastMCP server
      not yet written
    L10 Tool descriptions
      not yet written
    ["L11 .mcp.json"]
      not yet written
```

## Module D — Claude Agent SDK (D1 advanced)

Lessons 12–17. Higher-level orchestration: AgentDefinition, subagent spawning, coordinator and parallel patterns, hooks.

```mermaid
mindmap
  root((Module D<br/>Claude Agent SDK))
    L12 SDK vs raw API
      not yet written
    L13 AgentDefinition
      not yet written
    L14 Subagent spawning
      not yet written
    L15 Coordinator pattern
      not yet written
    L16 Parallel subagents
      not yet written
    L17 Hooks
      not yet written
```

## Module E — Claude Code Configuration (D3)

Lessons 18–22. CLAUDE.md hierarchy, rules, commands and skills, plan mode, CI usage. Heavy weight; Rich is fluent on the day-to-day surfaces but exam tests specifics.

```mermaid
mindmap
  root((Module E<br/>Claude Code Config))
    ["L18 CLAUDE.md hierarchy"]
      not yet written
    ["L19 .claude/rules"]
      not yet written
    L20 Commands and skills
      not yet written
    L21 Plan mode
      not yet written
    L22 Claude Code in CI
      not yet written
```

## Module F — Structured Output and Extraction (D4)

Lessons 23–27. Schema design, tool_use as the structured-output mechanism, Pydantic validation, few-shot, Batches API.

```mermaid
mindmap
  root((Module F<br/>Structured Output))
    L23 Schema design
      not yet written
    L24 tool_use as structured output
      not yet written
    L25 Pydantic validation retry
      not yet written
    L26 Few-shot
      not yet written
    L27 Message Batches API
      not yet written
```

## Module G — Context and Reliability (D5)

Lessons 28–32. Case-facts blocks, output trimming, lost-in-the-middle, escalation calibration, provenance.

```mermaid
mindmap
  root((Module G<br/>Context and Reliability))
    L28 Case-facts blocks
      not yet written
    L29 Trim tool outputs
      not yet written
    L30 Lost-in-the-middle
      not yet written
    L31 Escalation calibration
      not yet written
    L32 Provenance
      not yet written
```

## Module H — Multi-pass and Self-Review (D4 advanced)

Lesson 33. Independent-instance review; per-file and cross-file passes.

```mermaid
mindmap
  root((Module H<br/>Multi-pass Review))
    L33 Independent-instance review
      not yet written
```

---

## Cross-links (the exam-rewarding part)

Edges between concepts in *different* modules. Add one whenever a lesson reveals an integration point. Dotted edges (`-.->`) are forward-looking placeholders; solid edges (`-->`) are confirmed integration points discovered in a lesson.

```mermaid
graph LR
    L01_stop_reason["L01 stop_reason tool_use"] --> L02_loop["L02 tool_use to tool_result dance"]
    L01_blocks["L01 content blocks"] --> L02_blocks["L02 tool_use and tool_result block shapes"]
    L02_loop --> L03_while["L03 while loop over stop_reason"]
    L01_stop_reason --> L03_while
    L03_while -.future.-> L04_anti["L04 loop anti-patterns text-parse iter-cap"]
    L03_while -.future.-> L05_lookup["L05 customer-lookup agent end-to-end"]
    L03_while -.future.-> L16_par["L16 parallel tool_use blocks in one turn"]
    L02_dance["L02 tool_use mechanism"] -.future.-> F_struct["Module F structured output via tool_use"]
    L02_dance -.future.-> C_mcp["Module C MCP tools same protocol"]
```

---

## Revision notes (free-form)

Scratch area for things that don't fit the tree — analogies that landed, comparisons to Next.js patterns, "this would be a trap question" observations. Append-only.

- *(nothing yet)*
