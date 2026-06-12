# Lesson 11 — The Agent-Computer Interface (ACI): tool descriptions, format, poka-yoke

**Time**: ~15 minutes
**Prerequisites**: Lesson 10 (you built `support_server.py` — a FastMCP tool whose **docstring became its description** and whose **type hints became its input schema**). This lesson is about making that docstring *exam-grade*, and about the design choices around a tool that determine whether the model uses it correctly at all.
**Goal**: Internalise the **Agent-Computer Interface (ACI)** — the idea that a tool's *description, name, input/output shape, and failure modes* are an interface you design for a model the same way an API is an interface you design for a programmer. By the end you'll know the three levers the exam tests: (1) **descriptions** as the primary tool-selection mechanism, (2) **format/output shape** as a design choice, and (3) **poka-yoke** — making tools hard to misuse.

## Why this matters for the exam

This is **Domain 2, Task 2.1** ("Design effective tool interfaces with clear descriptions and boundaries") — and D2 is **18%** of the exam. The guide is blunt about the central claim:

> *"Tool descriptions [are] the primary mechanism LLMs use for tool selection; minimal descriptions lead to unreliable selection among similar tools."*

The testable skills it lists are concrete and we hit each one:
- writing descriptions that differentiate **purpose, inputs, outputs, and when-to-use-vs-alternatives**;
- **renaming** tools to eliminate overlap (`analyze_content` → `extract_web_results`);
- **splitting** a generic tool into purpose-specific ones (`analyze_document` → `extract_data_points` / `summarize_content` / `verify_claim`);
- spotting **keyword-sensitive system-prompt wording** that overrides good descriptions.

And one line you'll see again in L12, here as motivation:

> *"Enhancing MCP tool descriptions … preventing the agent from preferring built-in tools (like Grep) over more capable MCP tools."*

A weak description doesn't just *underperform* — it makes the model fall back to a built-in and never call your tool.

---

## Concept 1 — the description IS the tool selector (proved, not asserted)

You already know from L10 that the docstring becomes the description. Here's *why that sentence carries so much weight*. When the model decides which tool to call, it is **not** running your code, reading your types, or knowing your intent. It sees a list of `{name, description, input_schema}` objects and picks from text. **The description is the entire basis for selection among similar tools.**

To make that real, here is a verified experiment (run on `claude-haiku-4-5`). Two tools, a task that clearly wants exactly one of them, and `tool_choice="any"` so the model is *forced* to pick:

**Round A — identical descriptions, neutral names:**
```python
reader_a: "Read a resource and return its contents."
reader_b: "Read a resource and return its contents."   # identical
```
**Round B — differentiated descriptions and names:**
```python
extract_web_results:  "Extract structured results from a live WEB PAGE or URL.
                        Use ONLY when the input is a URL... Do NOT use for local
                        files — use read_local_document for those."
read_local_document:  "Read and extract text from a LOCAL FILE already on disk...
                        Use ONLY for files on the local machine... Do NOT use for
                        URLs — use extract_web_results for those."
```

Same prompt to both: `"Pull the key results out of this file: /Users/rich/reports/q3.pdf"` — unambiguously a **local file** task.

### Verified output

```
PROMPT: 'Pull the key results out of this file: /Users/rich/reports/q3.pdf'
(A local-file task. Correct target = the local-document tool.)
AMBIGUOUS (reader_a vs reader_b, identical descriptions): model picked -> ['reader_a']
DIFFERENTIATED (extract_web_results vs read_local_document): model picked -> ['read_local_document']
```

And across **10 runs** of the ambiguous round, the picks were: **9× `['reader_a']`, 1× `['reader_a', 'reader_b']`**.

Read what that distribution is telling you — this is the exam point in one breath:

- With **identical descriptions**, the model has *nothing to reason over*. It doesn't pick the "right" tool because there is no right tool to distinguish — it collapses to an **arbitrary default** (the first one in the list, `reader_a`, 9/10) and occasionally fires **both** tools (1/10). That is the guide's *"unreliable selection among similar tools"* made literal: not reasoned routing, just a positional coin-flip.
- With **differentiated descriptions** — each stating its purpose, its input format, *and* an explicit "do NOT use for X, use the other tool instead" boundary — selection is **10/10 correct**. The model routed on the words.

> The differentiating ingredient wasn't length for its own sake. It was: **purpose** (web page vs local file), **input format** (URL string vs filesystem path), **a concrete returns clause**, and an **explicit negative boundary** pointing at the sibling tool. Those four are exactly the guide's checklist.

This is why renaming `analyze_content` → `extract_web_results` (the guide's own example) is a *fix*, not cosmetics: the name and description together stop it overlapping with `analyze_document`. **Overlap is the bug; differentiation is the fix.**

---

## Concept 2 — output format / shape is a design choice (callback: Ada's team)

Remember **Lesson 03's Ada's-team experiment**? When you added `list_team_members`, we stopped and asked whether it should return an interpolated *string*, parallel *arrays*, or a list of *objects* — and you landed on the trade-off yourself: **a thin tool output forces more follow-up calls; a fat output puts more in context per call but spares the chain.** That instinct *is* this concept. You're now formalising it.

The ACI lesson: **the shape of what a tool returns is part of its interface, and it shapes the agent's behaviour downstream.**

- Return a bare string (`"pro: $20"`) → the model must re-parse it, and if it needs the seat count next, it calls again. **Thin tool → longer chains.**
- Return a structured object (`{"plan": "pro", "price": 20, "seats": 5, "support": "email"}`) → the model has every field already. **Fat tool → shorter chains, bigger payload per call.**

This is exactly why, back in L10, `lookup_plan` returns a **dict** and the `catalog://plans` **resource** returns the whole catalog up front: each is a deliberate shape choice to *eliminate exploratory round-trips*. The exam frames the resource side of this as *"content catalogs … to reduce exploratory tool calls"* — same principle, applied to read-only content.

There's no universal "right" shape — it's a context-vs-chain-length trade-off you make per tool. The exam-relevant skill is **knowing it's a choice and being able to justify it**, which you already did in L03. (We'll see the format-mismatch failure mode again in Module F with few-shot examples and JSON-schema enforcement.)

---

## Concept 3 — poka-yoke: design tools that are hard to misuse

*Poka-yoke* (Japanese, "mistake-proofing") is the manufacturing idea of a part that **physically can't be installed wrong** — a USB-A plug only seats one way. Applied to the ACI: **shape the tool so the invalid call is impossible or obvious, instead of relying on the model to "be careful."**

The guide's own example (Task 2.3) is pure poka-yoke even though it doesn't use the word:

> *"Replacing generic tools with constrained alternatives (e.g., replacing `fetch_url` with `load_document` that validates document URLs)."*

A `fetch_url(url)` tool can be pointed at anything — internal admin endpoints, file URIs, a malformed string. A `load_document(path)` tool that only accepts validated document paths **removes the foot-gun from the interface**. The model literally can't misuse it the same way.

Levers you have for mistake-proofing a tool (several you've already used):
- **Constrain inputs with the schema.** An `enum` (like L08's `sentiment: ["positive","negative","neutral"]`) makes an invalid value unrepresentable — the model can't pass `"angry"`. Tight types are poka-yoke.
- **Narrow the tool's job.** Split a generic `analyze_document` into `extract_data_points` / `summarize_content` / `verify_claim` (guide's example). Each has a contract too specific to misapply — and as a bonus, the narrower descriptions differentiate cleanly (Concept 1).
- **Structured, categorised errors** so a wrong call fails *informatively* instead of silently — which is **Lesson 07's** `is_error` + error-category work. (Task 2.2 is the whole "structured error responses" objective; you've already built it.)
- **Explicit negative boundaries in the description** ("do NOT use for URLs") — the soft version of poka-yoke when you can't enforce it in the schema.

Poka-yoke and good descriptions pull together: the more the *structure* prevents misuse, the less the *prose* has to beg the model to behave.

---

## Concept 4 — the "prefer my tool over Grep" problem (bridge to L12)

One specific failure the guide calls out (Task 2.4):

> *"Enhancing MCP tool descriptions to explain capabilities and outputs in detail, preventing the agent from preferring built-in tools (like Grep) over more capable MCP tools."*

Picture an MCP server exposing `search_tickets` over your support DB. If its description is just *"Search tickets."*, an agent in Claude Code — which *also* has the built-in `Grep` — may just `Grep` the repo and never call your tool, because `Grep` is a known, general hammer and your tool's value isn't legible. The fix is **not** code; it's the description: spell out **what it can do that the built-in can't** ("searches the live ticket DB including closed tickets and SLA metadata, not just files on disk; returns structured ticket objects with status and assignee"). You're competing for selection against built-ins, and the description is your only pitch. This is the same Concept-1 mechanism — differentiate or lose the routing — now against a built-in instead of a sibling MCP tool. L12 wires this exact server into `.mcp.json`; the description quality you write here is what makes it actually get used.

---

## Build — make `lookup_plan`'s description exam-grade

Open your `lessons/scripts/support_server.py` from L10. Here's the L10 docstring vs an exam-grade rewrite. **Don't just paste it — read the diff against the Concept-1 checklist.**

**Before (L10 — fine for a demo):**
```python
@mcp.tool()
def lookup_plan(plan_name: str) -> dict:
    """Look up the price, seat limit, and support tier for ONE plan by name."""
```

**After (exam-grade):**
```python
@mcp.tool()
def lookup_plan(plan_name: str) -> dict:
    """Look up ONE subscription plan's price, seat limit, and support tier by its exact name.

    Use this when the customer names a specific plan ("how much is Pro?"). For
    discovering WHICH plans exist, do NOT call this repeatedly — read the
    catalog://plans resource once instead.

    Input: plan_name — one of: "free", "pro", "business" (case-insensitive).
    Returns: {plan, price (USD/month), seats, support}. Unknown name returns
    {"error": ..., "known": [...]} listing valid names — do not retry with a guess.

    Example: lookup_plan("Pro") -> {"plan": "pro", "price": 20, "seats": 5, "support": "email"}
    """
```

Trace what each addition buys you, mapped to the guide's checklist:
- **purpose + when-to-use** ("when the customer names a specific plan") → selection signal;
- **explicit boundary vs the alternative** ("do NOT call repeatedly — read `catalog://plans`") → stops the exploratory-call anti-pattern, differentiates the tool from the resource;
- **input format** (the enum of valid names, case-insensitivity) → fewer invalid calls (poka-yoke in prose; you *could* harden it further with a typed enum);
- **returns clause + the error shape** → the model knows what comes back and that the error is **non-retryable** (callback to L07: structured, categorised failure);
- **a concrete example** → few-shot grounding (the guide: *"including input formats, example queries, edge cases"*; Module F goes deep on examples).

Re-run your L10 client (`uv run python lessons/scripts/support_client.py`) after editing — the tool still works identically; you changed the **interface the model reads**, not the behaviour. That's the whole point: the ACI is a layer you tune independently of the implementation.

---

## Exercises (do these before moving on)

1. **The core claim in one sentence.** Why does giving two tools *identical* descriptions produce unreliable selection — and what specifically did the model do in the verified 10-run experiment when it couldn't tell them apart? (Name both behaviours it fell back to.)

2. **Fix an overlap by renaming.** You have two tools: `get_data(query)` "Get data." and `fetch_data(query)` "Fetch data." An agent keeps calling the wrong one. Rewrite **both** names and descriptions so a model could route a *"find recent error logs in the last hour"* request to exactly one. State which guide skill you just applied (renaming-to-eliminate-overlap, or splitting-a-generic-tool — and why that one).

3. **Split a generic tool.** `analyze_document(doc)` currently "analyzes a document." Following the guide's example, split it into **three** purpose-specific tools with one-line descriptions each. For one of them, give the input/output contract. Which Concept-3 benefit (besides clarity) does splitting also deliver?

4. **Poka-yoke a foot-gun.** A tool `run_query(sql)` takes arbitrary SQL against production. Without changing what it fundamentally does, propose **two** mistake-proofing changes — one at the **schema/input** level and one at the **error-response** level (callback: which lesson gave you the error-response pattern?).

5. **Format choice, justified (callback).** Your `lookup_plan` could return `"pro: $20/mo, 5 seats, email support"` (a string) or the dict it currently returns. Pick one **for an agent that will often need to compare two plans' seat counts**, and justify it in the thin-tool/fat-tool language from your own L03 Ada's-team experiment.

6. **Beat the built-in.** Your MCP `search_tickets` tool is losing to Claude Code's built-in `Grep` — the agent keeps grepping instead. You may only edit the **description**. Write one that would win the routing, naming at least two capabilities `Grep` does **not** have.

---

## What you now know

- **The ACI is a real interface you design.** A tool's name, description, input schema, output shape, and error contract are to a *model* what a function signature + docs are to a *programmer* — and the model selects tools on the **description text alone**.
- **Descriptions are the primary selector** — proven: identical descriptions collapse selection to an arbitrary positional default (or double-firing); descriptions stating **purpose / input format / returns / explicit boundary-vs-alternatives** routed 10/10 correctly. **Overlap is the bug; differentiate, rename, or split to fix it.**
- **Output format/shape is a deliberate choice** — thin output → longer chains, fat output → bigger context per call (your own L03 Ada's-team trade-off, now named). Resources extend this to "load reference content up front to kill exploratory calls."
- **Poka-yoke**: make misuse impossible or obvious — constrain inputs (enums/typed schemas), narrow the tool's job (split generics), and return structured categorised errors (L07), so structure carries the safety the prose otherwise has to beg for.
- **You compete against built-ins**: a vague MCP tool loses routing to `Grep`; a description that spells out what it can do that the built-in can't is the only fix — and it's pure Concept-1 differentiation.

## Up next

**Lesson 12 — Wiring your server into Claude Code: `.mcp.json`, project vs user scope, env-var credentials.** You've now got a server (L10) with an exam-grade tool interface (L11). L12 makes it *live in Claude Code*: project-scoped `.mcp.json` (committed, shared with the team) vs user-scoped `~/.claude.json` (personal/experimental) — the two tiers you already started probing in L09 — plus `${ENV_VAR}` expansion so credentials never get committed. The "prefer my tool over Grep" description work from this lesson is what makes the server you wire up actually get *used*. That closes Module C (MCP Deep Dive).

When you've worked through this lesson and the exercises, tick the box in `lessons/README.md` and tell me you're done — I'll write 12.
