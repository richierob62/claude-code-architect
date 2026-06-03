# Lesson 04 — Workflow patterns: the agentic-systems catalog

**Time**: ~15–20 minutes
**Prerequisites**: Lesson 03 complete. You can run `agentic_loop.py`, explain why `stop_reason == "end_turn"` is the only normal exit, and articulate why `max_iters` is a safety net rather than a stop condition.
**Goal**: Learn the Anthropic-canonical vocabulary for agentic-system patterns — **workflows vs. agents**, and the five common workflow shapes (prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer). Build a decision rubric for picking the right pattern. You won't write much code in this lesson — you'll spend the time mapping names to shapes so they're instantly recognisable on the exam.

## Why this matters for the exam

Domain 1 is 27% of the exam, and the question stems will use Anthropic's own vocabulary. The seminal post — *Building Effective Agents* (Anthropic, Dec 2024, Erik S. & Barry Zhang) — defines the words the exam writers reach for first. If you can't tell **prompt chaining** from **orchestrator-workers** at a glance, you'll lose easy points on architecture-choice questions.

The other reason this lesson exists where it does: the rest of Module B and all of Module D are *instances* of these patterns. Lesson 03 was a tiny **agent**. Lesson 15 (coordinator pattern) is **orchestrator-workers**. Lesson 16 (parallel subagents) is **parallelization–sectioning**. Lesson 25 (validation retry) is **evaluator-optimizer**. Lesson 33 (independent-instance review) is **evaluator-optimizer with multiple evaluators**. Naming them now turns the rest of the course into recognition rather than discovery.

## The single most important distinction: **workflow vs. agent**

Anthropic categorises every LLM-plus-tools system as **agentic**, but draws a hard line *inside* that category:

- **Workflow** — LLM calls (and the tools they invoke) are orchestrated through **predefined code paths**. *You* write the control flow; the LLM fills in the cognitive work at each step. The structure is fixed before the user's question arrives.
- **Agent** — the **LLM dynamically directs its own process and tool usage**. The control flow is determined at runtime by the model's decisions. The structure of the trajectory is decided as the question is answered.

Lesson 03's `agentic_loop.py` is an agent: Claude decided whether to call `find_employee_id`, whether to follow up with `get_employee_details`, and when to stop. You wrote a `while`, but the *shape* of the conversation was Claude's call.

A workflow would have been: "always call `find_employee_id` first, then always call `get_employee_details` with its output, then synthesise." That is a two-step pipeline you could draw on paper before running it. No model-driven branching.

**Rule of thumb for the exam**: if a question describes a system where the steps are knowable in advance ("always X then Y"), it's a workflow. If steps are determined by the model based on intermediate results, it's an agent.

### When to reach for which

| | Workflow | Agent |
|---|---|---|
| Predictability | High | Low |
| Latency / cost | Lower | Higher (multiple turns, more tokens) |
| Best when | Task decomposes into known steps | Steps can't be predicted in advance |
| Failure mode | Brittleness on unexpected input | Compounding errors, runaway loops |
| Debugging | Easy — fixed code path | Harder — trajectories vary per run |

And one meta-rule the article and the exam both push: **start simple, add complexity only when it demonstrably helps.** A well-prompted single LLM call with retrieval beats a five-agent system on most tasks. Don't reach for an agent because the word sounds impressive; reach for it when you genuinely can't predict the steps.

## The building block: the **augmented LLM**

Before the patterns, name the atom. Every pattern below is built from one repeating unit Anthropic calls the **augmented LLM**: an LLM enhanced with three optional capabilities —

- **Retrieval** — fetch relevant information (RAG, search, lookups).
- **Tools** — invoke external functions (everything you built in Lessons 02–03).
- **Memory** — persist information across calls (case-facts blocks in Lesson 29, conversation history, etc.).

Each pattern below is one or more augmented LLMs arranged in a particular topology. Memorising the topologies is the work of this lesson.

## The five workflow patterns

These are the only five you need to know by name. Each gets one paragraph of "what it is", one paragraph of "when to use it", and a concrete example. Do **not** skim — the exam will use these names directly.

> **Mnemonic (all seven, in order):** *"**Charlie ran parallel** to the **orchestra evaluating** the **agent**."* (Ignore the filler "to / the".)
>
> | Word | Pattern |
> |---|---|
> | **Charlie** | prompt **chaining** |
> | **ran** | **routing** |
> | **parallel** | **parallelization** — covers *both* flavors: **sectioning** (split the work) and **voting** (split the vote / run K, aggregate) |
> | **orchestra** | **orchestrator**-workers |
> | **evaluating** | **evaluator**-optimizer |
> | **agent** | **agent** |
>
> The order also tracks **increasing autonomy** — from "you control the path" (chaining) to "the model controls everything" (agent).

### 1. Prompt chaining

**Shape**: a fixed sequence of LLM calls where call N's output is call N+1's input. Optionally with **gates** between steps — programmatic checks that abort or reroute if an intermediate result is malformed.

```
[user input] → LLM1 → [check?] → LLM2 → [check?] → LLM3 → [final output]
```

**When to use**: the task cleanly decomposes into fixed subtasks, and you're willing to trade total latency for higher per-step accuracy. Splitting a hard task into easier ones is the whole point — each LLM call sees a smaller, simpler prompt.

**Examples**:
- Write marketing copy → translate it into French.
- Outline a document → check the outline against criteria → write the document from the outline.
- Extract entities → validate against a schema → enrich each entity with a follow-up lookup.

**How it differs from an agent**: every step is in the code. The LLM doesn't decide whether to call LLM2; the code does.

### 2. Routing

**Shape**: a classifier (LLM or traditional) inspects the input and dispatches it to one of N specialised downstream handlers. Each handler is itself an augmented LLM with a prompt tuned for its category.

```
                        ┌─→ LLM_refund   (refund prompts, refund tools)
[user input] → router → ├─→ LLM_tech     (tech-support prompt, log access)
                        └─→ LLM_general  (FAQ prompt)
```

**When to use**: the input space has **distinct categories that are better handled separately**, and you can classify accurately. Without routing, one prompt has to handle all categories and inevitably gets worse at each as you tune it for the others.

**Examples**:
- Customer-service triage: general question vs. refund request vs. tech support.
- Cost optimisation: route easy/common queries to Haiku 4.5; route hard/unusual ones to Sonnet 4.5 or Opus. (This is the "cheap-default, escalate-when-needed" pattern that turns up in cost-optimisation exam questions.)

**Subtle point**: routing is a workflow because the **set of handlers** is predefined. An agent that decides which tool to call from a tool list is *not* routing in this sense — the structure is different.

### 3. Parallelization

**Shape**: multiple LLM calls run **simultaneously** and their outputs are **aggregated programmatically**. Two flavours:

- **Sectioning** — split the work into independent subtasks, run them in parallel, stitch the results. Each call sees a *different* slice.
- **Voting** — run the **same** task multiple times (often with prompt variations) and aggregate the answers (majority vote, any-flag, weighted, etc.). Each call sees the *same* slice.

```
Sectioning:                          Voting:
[input] → ┌─→ LLM_part1 ─┐           [input] → ┌─→ LLM_v1 ─┐
         ├─→ LLM_part2 ─┤→ stitch            ├─→ LLM_v2 ─┤→ aggregate
         └─→ LLM_part3 ─┘                    └─→ LLM_v3 ─┘
```

**When to use sectioning**: subtasks are genuinely independent (no data dependency between them) and parallelism either speeds things up or lets each prompt focus narrowly on one concern. Anthropic's recurring example: a **safety guardrail LLM** running in parallel with the **content LLM** — separating "is this query safe?" from "answer this query" gives better behaviour than asking one prompt to do both.

**When to use voting**: you want confidence through diversity. The same task is hard or high-stakes, and running it K times and aggregating reduces variance. Examples: K-prompt code-vulnerability review (flag if *any* prompt finds a bug); content-moderation with K independent moderators and a vote threshold to trade off false-positives and false-negatives.

**How it differs from orchestrator-workers** (next): in parallelization, the **subtasks are predefined** — you decided up-front to split into part1/part2/part3 or to run K voters. In orchestrator-workers, the subtasks are decided at runtime by the orchestrator.

### 4. Orchestrator-workers

**Shape**: a central **orchestrator LLM** receives the task, **dynamically decomposes** it into subtasks, dispatches each to a **worker LLM** (often with its own tools and prompt), then **synthesises** the worker outputs into a final answer.

```
                  ┌─→ worker_A
[input] → orch → ├─→ worker_B  → orch synthesises → [final]
                  └─→ worker_? (count and shape decided at runtime)
```

**When to use**: a complex task whose subtasks **cannot be predicted in advance**. The canonical example from Anthropic is a **coding agent making multi-file changes**: the orchestrator reads the task, decides *which* files need editing and *how* (which workers to spawn, what each should do), then assembles the diffs. You couldn't have hardcoded "split into 3 file-edits" up front — the task itself dictates the shape.

**Examples**:
- Multi-file code changes (the orchestrator decides which files; each worker edits one file).
- Research aggregation: the orchestrator decides which sources to consult; each worker fetches and summarises one source.

**How it differs from parallelization**: parallelization's subtasks are *fixed* by the developer; orchestrator-workers' subtasks are *chosen by the model* per-input. Topologically they look similar (one fan-out, one fan-in) — the distinction is **who decides the fan-out shape**.

**You will build this in Lesson 16** (the new numbering — coordinator pattern) and again in Lesson 17 (parallel subagent calls).

### 5. Evaluator-optimizer

**Shape**: one LLM **generates** an output, a second LLM **evaluates** it against criteria, and if the evaluator isn't satisfied, the generator runs again with the evaluator's feedback. Loop until the evaluator passes or you hit a cap.

```
[input] → generator → output → evaluator → pass? → [final]
              ▲                       │
              └──── feedback ─────────┘ (fail → regenerate)
```

**When to use**: you have **clear evaluation criteria**, *and* iterative refinement measurably improves quality, *and* an LLM can produce the kind of feedback that helps. The article's gold standard: literary translation, where the first pass misses nuance an evaluator can name (tone, register, idiom), and the next pass uses the critique productively.

**Examples**:
- Literary translation (evaluator critiques register; generator retranslates).
- Pydantic-validation-with-retry (Lesson 26 in the new numbering): generator emits structured output → validator checks the schema → on failure, generator retries with the validation error as feedback. The validator is "just" a Pydantic call, but the **pattern** is evaluator-optimizer.
- Multi-pass code review (Lesson 34 in the new numbering): one LLM proposes changes, another reviews against project conventions, loop until clean.

**How it differs from prompt chaining**: chaining is one-shot per step. Evaluator-optimizer is **a loop with a fail/retry edge** — the same generator may run multiple times with growing context.

## Pattern decision rubric

Memorise this. The exam will hand you a scenario and ask which pattern fits.

| If the task… | Pattern |
|---|---|
| …decomposes into a **fixed** sequence of known steps | Prompt chaining |
| …has **categorically different** inputs better served by specialised prompts | Routing |
| …splits into **predefined independent** subtasks (or needs K diverse attempts) | Parallelization (sectioning / voting) |
| …needs **runtime decomposition** because subtask shape depends on input | Orchestrator-workers |
| …has **clear pass/fail criteria** and benefits from iterative critique | Evaluator-optimizer |
| …has **no predictable path** at all, and the model must decide each next step | **Agent** (not a workflow) |

## The three principles (memorise verbatim)

When the post tells you how to *implement* agents, it gives three principles. These are exam-ready quotables:

1. **Maintain simplicity** in your agent's design. Don't add an evaluator just because evaluator-optimizer sounds clever — add it when single-pass quality is demonstrably insufficient.
2. **Prioritise transparency** by explicitly showing the agent's planning steps. (This is why Claude Code surfaces tool calls and plan-mode plans to the user — the user can audit reasoning, not just outputs.)
3. **Carefully craft the agent-computer interface (ACI)** — tool descriptions, parameter names, formats — with **as much rigor as you would the human-computer interface (HCI)**. This is the seed for Lesson 11 (tool-description craft) — when you get there, you'll see ACI is a much broader idea than just "write a good description".

## Why "don't build agents" is a valid answer

The exam will sometimes give you a scenario whose correct answer is **"do not build an agentic system at all — a well-prompted single LLM call with retrieval is sufficient."** Watch for these clues:

- The task has a **single, well-defined sub-problem** (summarise this doc; classify this email).
- Latency is critical (agentic loops add round-trips).
- The cost of compounding errors is high and the value of model-directed branching is low.
- A traditional rule-based or classifier-based solution would work; the LLM is being shoehorned in.

When in doubt: simpler is better, until the data says otherwise.

---

## Build — map your existing lessons onto the catalogue

There's no script for this lesson. Instead, fill in this table on paper or in `scratch-pad.md` — it forces you to apply the catalogue to systems you've already built or will soon build.

| Lesson | What it builds | Pattern name |
|---|---|---|
| L03 — `agentic_loop.py` | `find_id` → `get_details` chain driven by `stop_reason` | **Agent** (not a workflow — Claude decides whether and which tool to call) |
| L06 — Customer-lookup agent | Claude loops over *several* tools (lookup, orders, refunds), deciding which to call each turn, until it has enough to answer | ? |
| L15 — `tool_choice` | Forcing tool use vs. allowing free choice | (not a pattern — a *control* over the agent's choice) |
| L16 — Coordinator/subagent | A central agent dispatching subtasks to subagents | ? |
| L17 — Parallel subagents | Multiple subagent calls in one turn, results aggregated | ? |
| L26 — Pydantic validation + retry | Emit JSON → validate → on failure, retry with error feedback | ? |
| L34 — Independent-instance review | Generate code → independent reviewer flags issues → fix | ? |

(Answers, in order: **Agent** (multi-tool, model-driven — same shape as L03, just more tools; *not* orchestrator-workers, because there are no subagents, and *not* prompt chaining, because the call sequence isn't fixed by you); orchestrator-workers; parallelization–sectioning *if* the subtasks are predefined, else orchestrator-workers; evaluator-optimizer; evaluator-optimizer.)

The point of the exercise: by the time you reach those lessons, you'll already know what pattern they're an instance of, and you'll spend cognitive effort on the *details* of the implementation rather than re-deriving the architecture.

---

## Exercises (do these before moving on)

For each scenario, name the pattern (one of: prompt chaining, routing, parallelization–sectioning, parallelization–voting, orchestrator-workers, evaluator-optimizer, agent, **no agentic system needed**) and write one sentence justifying it.

1. A legal-document pipeline that (a) extracts clauses, (b) checks each clause against a list of forbidden patterns, (c) summarises the document. The three steps always run in that order.

2. A code-quality tool that runs three different LLM reviewers — security, style, complexity — and flags any file where two or more reviewers raise a concern.

3. A help-desk system that, on receiving a message, decides whether it's billing-related, technical, or general, and sends it to the appropriately-prompted handler.

4. A SWE-bench-style code agent that reads an issue, figures out which files to edit, edits each, and assembles a PR.

5. A translation tool where translation is generated by Haiku, then critiqued by Sonnet for register and idiom, then retranslated by Haiku with the critique as guidance.

6. A FAQ-answering system over a 200-document corpus, where each query is answered by retrieving the top 5 relevant docs and asking Haiku to answer based on them.

7. A research assistant that takes a question, decides at runtime which subset of (web search, internal docs, codebase grep, calendar) to consult, then synthesises a single answer.

Then answer in one sentence each:

1. What single distinction separates a **workflow** from an **agent**?
2. What single distinction separates **parallelization** from **orchestrator-workers** when both fan out and fan in?
3. Why is "start with a single well-prompted LLM call and only add complexity when it demonstrably helps" a defensible exam answer for many scenarios?
4. What does **ACI** stand for, and what does the three-principles framing claim about the effort that should go into designing one?

---

## What you now know

- **Workflow vs. agent** is the central distinction in agentic-systems vocabulary: workflows have predefined code paths; agents have model-directed control flow.
- The five canonical workflow patterns: **prompt chaining, routing, parallelization (sectioning / voting), orchestrator-workers, evaluator-optimizer**.
- The building block is the **augmented LLM** — an LLM with retrieval, tools, and/or memory. Every pattern is a topology of augmented LLMs.
- A complexity ladder for choosing: **single LLM call → workflow → agent**. Climb only when the lower rung is demonstrably insufficient.
- The three implementation principles: **simplicity, transparency, ACI rigor**.
- Most of the rest of the course is one of these patterns wearing a particular costume. You will keep meeting them.

## Up next

**Lesson 05 — Loop anti-patterns.** Back to agents specifically. Now that you can name the patterns, the next lesson tours the three wrong ways the exam will tempt you to terminate an agent loop (text-parsing, iteration caps as primary stop, "did it produce any text?" heuristic) — and proves with code why each one fails.

When you've worked through this lesson and the exercises, tick the box in `lessons/README.md` and tell me you're done — I'll write 05.
