# Lesson 16 — Coordinator/subagent build (orchestrator-workers)

**Time**: ~15 minutes
**Prerequisites**: L15 (you can define an `AgentDefinition`, grant `"Task"`, and pass context down a delegation prompt). You'll lean on L04 (orchestrator-workers — pattern #4) and L11 (`description` as the selection signal).
**Goal**: Build a **coordinator** that delegates to **two different** subagents and decides *which* to use per request. L15 proved one parent → one worker. L16 is the real pattern: a parent with a *roster* of workers, **routing by their `description`s**, then **synthesising** the workers' results into one answer. By the end you'll have watched the same coordinator pick *different* workers for *different* inputs — selection you didn't hard-code.

## Why this matters for the exam

This is **Domain 1's "coordinator/subagent architecture"** task statement made concrete — the heart of the 27% domain. L15 was the mechanism (how one agent spawns another); L16 is the *architecture* (a coordinator owning multiple specialists). The exam tests whether you understand three things that only appear once there's **more than one worker**:

1. **Routing is description-driven, not code-driven.** The coordinator reads each subagent's `description` and picks — there's no `if request_type == "math"` in your code. (This is exactly L11's "the description *is* the selection signal," now one level up.)
2. **The coordinator synthesises.** Workers return partial results; the coordinator composes the final answer. That composition step is the orchestrator's job and is what separates orchestrator-workers from plain routing.
3. **Each worker still gets isolated context** — the L15 discipline doesn't go away just because there are now two of them. The coordinator must hand *each* worker exactly what it needs.

> **L04 callback.** This is **orchestrator-workers** (pattern #4) — the central LLM "dynamically decomposes" a task and "dispatches each subtask to a worker." L15 built the dispatch machinery; L16 builds the *decomposition + synthesis* around it.

---

## The one-sentence version

> **A coordinator is a parent agent whose job is to read a request, pick the right worker(s) from its roster by their descriptions, hand each the context it needs, and stitch the results into one answer.**

---

## Concept 1 — Routing vs orchestrating (don't conflate them)

L04 listed these as two *different* patterns, and the distinction matters here:

- **Routing** (pattern #2): classify the input, send it down **one** of N fixed paths. One worker fires. No synthesis — the chosen path's output *is* the answer.
- **Orchestrator-workers** (pattern #4): the coordinator may fire **one or several** workers, *and* it composes their outputs. The decomposition is **dynamic** — the coordinator decides at runtime how many subtasks there are.

A coordinator with two subagents that only ever picks one is doing routing. The moment it can decompose ("for this request I need the researcher *and* the summarizer") and merge, it's orchestrating. We'll build the roster so you can see both behaviours from the *same* code, depending on the request.

---

## Concept 2 — The roster: two workers with sharp, non-overlapping descriptions

The coordinator's whole routing ability rests on the `description`s being **distinguishable**. This is the L11 poka-yoke principle: if two workers' descriptions overlap, the coordinator delegates to the wrong one (or dithers). Give each a tight, bounded job:

```python
agents={
    "researcher": AgentDefinition(
        description="Answers factual questions about a topic in 2-3 sentences. "
                    "Use when the request needs information or explanation.",
        prompt="You are a researcher. Answer the question factually in 2-3 sentences. "
               "If you don't know, say so plainly. No preamble.",
        tools=[], model="haiku",
    ),
    "wordsmith": AgentDefinition(
        description="Rewrites a given piece of text in a requested tone or style. "
                    "Use when the request is to rephrase, shorten, or restyle existing text.",
        prompt="You are a wordsmith. Rewrite the text you are given per the instruction. "
               "Output only the rewritten text.",
        tools=[], model="haiku",
    ),
}
```

Notice the descriptions answer **different questions about the input**: "is this asking for *information*?" → researcher; "is this asking to *transform text I already have*?" → wordsmith. Non-overlapping selection signals are the entire reliability story.

---

## Concept 3 — The coordinator's system prompt does the decomposing

The subagents are defined; what makes the *parent* a coordinator is **its own system prompt** telling it to delegate rather than answer directly. Without this, a capable parent will often just answer the question itself and never spawn anyone.

```python
options = ClaudeAgentOptions(
    model="claude-haiku-4-5",
    setting_sources=[],
    allowed_tools=["Task"],
    permission_mode="bypassPermissions",
    system_prompt=(
        "You are a coordinator. You do NOT answer requests yourself. "
        "For each request, delegate to the most appropriate subagent, then "
        "present its result as the final answer. If a request has two parts "
        "(e.g. find a fact AND restyle it), delegate to each in turn and combine."
    ),
    agents={...},  # the roster from Concept 2
)
```

That "you do NOT answer yourself" line is load-bearing. It's the difference between a parent that *could* delegate and a coordinator that *will*. (Exam framing: a coordinator that answers directly has collapsed back into a single agent — the orchestration is only real if the workers actually run.)

---

## Concept 4 — Synthesis: the coordinator owns the final composition

When the coordinator fires **two** workers (the "find a fact AND restyle it" case), each returns a partial. The coordinator's last turn — *after* both tool results land — is where it merges them. You'll see this in the stream as: two `Agent` tool calls, two tool results, then a final `TextBlock` that is the *composed* answer (not a verbatim copy of either worker's output).

This is the step people forget exists. Routing has no synthesis; orchestrator-workers does. If you only ever see one delegation and a passthrough of its result, you built a router, not a coordinator.

---

## Your build

Create `lessons/scripts/coordinator_lab.py`. Build **one coordinator** with the **two-worker roster** above and run **three** requests through the *same* options to watch the coordinator route — and, once, decompose — on its own.

1. **Define the roster** (`researcher` + `wordsmith`) and the **coordinator `system_prompt`** exactly as in Concepts 2–3. `tools=[]`, `model="haiku"` on both workers.

2. **Request 1 — routes to `researcher`.** Prompt: *"Why is the sky blue?"* Expect one `DELEGATE → researcher` in the stream, then the factual answer.

3. **Request 2 — routes to `wordsmith`.** Prompt: *"Rewrite this in a pirate accent: 'Please submit your report by Friday.'"* Expect one `DELEGATE → wordsmith`. Same coordinator, **different worker** — selection you didn't hard-code.

4. **Request 3 — decomposes to BOTH.** Prompt: *"Find out what the tallest mountain is, then rewrite the fact as an excited tweet."* Expect **two** delegations (`researcher` then `wordsmith`) and a final composed answer. This is orchestration, not routing.

5. Print each request's `ResultMessage.total_cost_usd`. Request 3 costs the most (parent + two children). A few cents total across all three — **don't loop it.**

> Reuse the L15 stream-reader so you can see *which* worker fires:
> ```python
> for block in message.content:
>     if isinstance(block, TextBlock):
>         print("TEXT:", block.text)
>     elif type(block).__name__ == "ToolUseBlock":
>         print("DELEGATE →", block.input.get("subagent_type"),
>               "| prompt:", block.input.get("prompt"))
> ```
> Build the `ClaudeAgentOptions` **once** and pass it to all three `query()` calls — the point is that *the same coordinator* routes differently per input. (Each `query()` is still its own fresh parent conversation; reusing the options object doesn't share context between requests — it shares *configuration*.)

---

## Exercises

1. **Routing vs orchestrating, in one line each.** Using your three requests as evidence, state which were *routing* and which was *orchestrating*, and what observable difference in the stream told them apart.

2. **Break the routing on purpose.** If you changed `wordsmith`'s description to "Helps with text" (vague), predict what happens to Request 1 and Request 3 — and name the L11 principle you just violated.

3. **Who synthesises?** In Request 3, the final tweet combines a fact (from `researcher`) with a restyle (from `wordsmith`). *Which* agent produced the final combined text — the coordinator or one of the workers? Explain how the stream proves your answer.

4. **Forward-link to L17.** In Request 3 the coordinator ran the two workers *one after another* (researcher's result fed wordsmith). Could it have run them **at the same time**? Why or why not — and what *kind* of two-worker task *would* be safe to run in parallel? (That's L17.)

---

## What to remember

- **Coordinator = parent that routes by `description` and synthesises results.** The routing logic lives in the descriptions + coordinator system prompt, **not** in your Python.
- **Routing fires one path; orchestrating decomposes and merges.** Same machinery (L15), different coordinator behaviour driven by the request.
- **Sharp, non-overlapping worker descriptions are the reliability story** — L11, one level up.
- **The coordinator's "do not answer yourself" instruction is what makes delegation actually happen.**
- **Isolation still holds per worker** — each gets only what the coordinator puts in its prompt (L15).
