# Lesson 17 — Parallel subagent calls in one turn (parallelization–sectioning)

**Time**: ~15 minutes
**Prerequisites**: L16 (you can build a coordinator with a roster and watch it route/decompose). You'll lean on L04 (parallelization — pattern #3, the *sectioning* flavor) and L15's isolation discipline.
**Goal**: Make a coordinator fan out to **several subagents at once** — multiple `Agent` tool calls in a **single** assistant turn, run **concurrently** — and internalize the two disciplines that only matter once work is parallel: **you must invite parallelism explicitly**, and **you must treat the results as unordered**. By the end you'll have watched one turn spawn three workers side-by-side and matched each result back to the request that produced it.

## Why this matters for the exam

This is **L04's parallelization pattern (#3), *sectioning* flavor** — "break a task into independent subtasks, run them simultaneously, combine." L16 ran workers *one after another* (Request 3: researcher's fact fed the wordsmith). L17 is the case where the subtasks **don't depend on each other**, so running them in sequence just wastes wall-clock. The exam tests whether you know:

1. **When parallel is legal.** Only when subtasks are **independent** — no subtask needs another's output. (Dependent subtasks → you're back to chaining/sequential orchestration from L16.)
2. **How it actually happens.** Parallelism is **model-driven**: the coordinator emits *multiple* `Agent` tool-use blocks in **one** assistant turn, and the SDK runs them concurrently. There is **no "parallel=True" flag** — you get fan-out by having independent work *and prompting for it*.
3. **The ordering trap.** Parallel results come back **unordered**. Code that assumes result[0] belongs to request[0] is buggy. You match results to requests by identity, not position.

> **L04 callback.** Parallelization has two flavors (L04, pattern #3): **sectioning** (split the *work* — different subtasks, this lesson) and **voting** (split the *vote* — same task run K times, aggregate). L17 is sectioning. Voting shows up later when we do evaluator/quality patterns.

---

## The one-sentence version

> **If subtasks are independent, a coordinator can emit several `Agent` calls in a single turn and the SDK runs them at once — but you have to ask for it, and you must not assume the results come back in the order you sent them.**

---

## Concept 1 — Sequential vs parallel decomposition (the dividing line is *dependency*)

In L16's Request 3, the two steps were **dependent**: the wordsmith couldn't restyle the fact until the researcher *produced* it. Dependency forces sequence — there was nothing to parallelize.

Now picture a different task: *"Summarize each of these three articles."* The three summaries have **nothing to do with each other**. Article B's summary doesn't need article A's. These are **independent subtasks** — the textbook case for sectioning. Running them one-at-a-time would triple your wall-clock for no reason.

> **The litmus test:** *Does subtask N need the output of subtask M?* If **no** for every pair → safe to parallelize. If **yes** for any pair → that edge must stay sequential (L16 territory). Many real tasks are mixed: a parallel fan-out, then a sequential synthesis of the results.

---

## Concept 2 — How parallel fan-out actually happens (model-driven, not a flag)

Here is the mechanism, and it's worth getting exactly right because the exam can probe it:

- The coordinator decides — **in one assistant turn** — to call the `Agent` tool **multiple times**. That's just **parallel tool use** (the standard Anthropic behavior: a model may emit several `tool_use` blocks in a single turn) applied to the delegation tool.
- The SDK/harness then runs those subagents **concurrently** and feeds all their results back.
- **There is no `parallel=True` setting** on `AgentDefinition` or `ClaudeAgentOptions`. You don't *configure* parallelism — you *enable the conditions for it*: independent subtasks + a prompt that invites simultaneous delegation.

What you'll see in the stream is the tell: a **single `AssistantMessage` whose `.content` holds several `ToolUseBlock`s**, each `name="Agent"` with a different `subagent_type`/`prompt`:

```
AssistantMessage.content = [
    ToolUseBlock(name="Agent", input={"subagent_type": "summarizer", "prompt": "...article A..."}),
    ToolUseBlock(name="Agent", input={"subagent_type": "summarizer", "prompt": "...article B..."}),
    ToolUseBlock(name="Agent", input={"subagent_type": "summarizer", "prompt": "...article C..."}),
]
```

Three `Agent` blocks in **one** turn = fan-out. Three blocks across **three** turns = sequential. The number of *assistant turns* is how you tell them apart in the stream.

> **Note (verify when you run it).** The exact concurrency ceiling (how many run truly simultaneously before the rest queue) and the precise field name used to attribute a result back to its spawning call are runtime details that have shifted across SDK versions. Don't memorize a magic number for the exam — memorize the *shape* (multiple `Agent` blocks, one turn, concurrent execution, unordered results). Confirm the live specifics in your own run; that's the build below.

---

## Concept 3 — You have to *invite* parallelism (prompting matters)

The model parallelizes **conservatively**. Give it three independent articles and a flat *"summarize these,"* and it may still plod through them one subagent per turn. To reliably get fan-out, the request (or the coordinator's system prompt) must **say the subtasks are independent and may run at once**:

- **Reliably parallel:** *"Summarize these three articles. They are independent — spawn one summarizer subagent per article in parallel, in a single step."*
- **Often serial:** *"Summarize these three articles."*

The model still respects real dependencies — if you ask for parallelism but task B genuinely needs task A, it will serialize that edge anyway. You can *invite* parallelism; you can't *force* it onto dependent work. That's correct behavior, not a limitation.

---

## Concept 4 — Results are unordered: match by identity, not position

This is the discipline that separates working parallel code from subtly-broken parallel code:

> **When N subagents run concurrently, the order their results arrive is NOT guaranteed to match the order you spawned them.** The third one you dispatched might finish first.

So **never** assume `results[0]` is the summary of `article[0]`. If you need to know *which* result belongs to *which* request, you must carry an identifier — put a label *inside each subagent's prompt* ("Begin your summary with the tag `[A]`") so the returned text self-identifies, and/or attribute results back to their spawning `Agent` tool call by its id. The point for the exam: **parallel results are a set, not a sequence.** Position-based matching is the classic bug.

(Contrast L16's sequential case, where ordering *was* implicit — the researcher always finished before the wordsmith started, because the wordsmith depended on it. Remove the dependency and you remove the ordering guarantee along with it.)

---

## Your build

Create `lessons/scripts/parallel_lab.py`. Build a coordinator with **one** reusable `summarizer` worker and fan it out across **three independent blurbs** in a single turn — then prove both disciplines (invite-it, unordered).

1. **One worker, one coordinator.** Reuse the L16 conventions: `model="claude-haiku-4-5"`, `setting_sources=[]`, `allowed_tools=["Task"]`, `permission_mode="bypassPermissions"`. Define a single `summarizer` `AgentDefinition` (`tools=[]`, `model="haiku"`, prompt = "You are a summarizer. Return exactly one sentence capturing the core point of the text you are given. Begin that sentence with the tag you were given in square brackets, e.g. `[A] ...`."). Coordinator `system_prompt`: "You are a coordinator. You do not summarize yourself — you delegate."

2. **Three independent blurbs.** Put three short 2–3 sentence paragraphs in the script (`A`, `B`, `C`) on unrelated topics (e.g. photosynthesis, the printing press, tides). Tag them so you can track them.

3. **Invite the fan-out.** One parent prompt that includes all three blurbs and says, explicitly: *"These three texts are independent. Spawn one summarizer subagent per text, in parallel, in a single step. Tell each subagent its tag (`[A]`, `[B]`, `[C]`)."* Use the L15/L16 stream-reader so you can **count the `DELEGATE →` lines in each assistant turn** — three in one turn = fan-out.

4. **Prove unordered.** Print the subagents' results in the order they arrive and confirm the `[A]/[B]/[C]` tags let you re-associate them regardless of arrival order. (If they happen to arrive in order this run, that's luck — the tag is what makes your code *correct* either way.)

5. Print `ResultMessage.total_cost_usd`. One parent + three children ≈ a few cents — **don't loop it.**

> Stream-reader (counts delegations per turn so you can see fan-out vs serial):
> ```python
> async for message in query(prompt=parent_prompt, options=options):
>     if isinstance(message, AssistantMessage):
>         delegations = [b for b in message.content if type(b).__name__ == "ToolUseBlock"]
>         if delegations:
>             print(f"--- assistant turn: {len(delegations)} delegation(s) ---")
>             for b in delegations:
>                 print("DELEGATE →", b.input.get("subagent_type"), "| prompt:", b.input.get("prompt")[:60])
>         for b in message.content:
>             if isinstance(b, TextBlock):
>                 print("TEXT:", b.text)
>     elif isinstance(message, ResultMessage):
>         print("COST: $", message.total_cost_usd)
> ```
> If you see `--- assistant turn: 3 delegation(s) ---`, you got real fan-out. If you see three separate `1 delegation(s)` turns, the model went serial — strengthen the parallelism invitation in your prompt and re-run.

---

## Exercises

1. **The litmus test.** Give one concrete task that is **safe** to parallelize and one that is **not**, and state the single question you asked to tell them apart.

2. **Diagnose the serial run.** A teammate fans out 5 "research this competitor" subagents but they execute one per turn, tripling the runtime. The subtasks are genuinely independent. Name the *most likely* cause and the one-line fix. (Hint: it's not a code bug.)

3. **The position bug.** Someone writes `for i, result in enumerate(results): print(f"Summary of article {articles[i]}: {result}")` after a parallel fan-out, and the summaries are mislabeled. Explain why, and give the fix in terms of Concept 4.

4. **Sectioning vs voting.** L04's parallelization had two flavors. Your build did **sectioning** (3 different texts). Describe the *same machinery* used for **voting** instead — what would the three subagents be doing, and what would the coordinator do with their three results?

5. **Mixed pipeline.** Sketch (in words) a task that is **parallel then sequential**: a fan-out step followed by a synthesis step that depends on all of the fan-out results. Which part is L17 and which part is L16?

---

## What to remember

- **Parallelize only independent subtasks.** The litmus test is "does any subtask need another's output?" — if yes, that edge stays sequential.
- **Fan-out is model-driven, not a flag:** multiple `Agent` tool-use blocks in **one** assistant turn → the SDK runs them concurrently. Count delegations-per-turn in the stream to tell parallel from serial.
- **You must invite parallelism explicitly** — the model is conservative; a flat request often runs serial.
- **Parallel results are a set, not a sequence.** Match by an identity tag (or the spawning call's id), never by array position.
- **Sectioning** (split the work) and **voting** (split the vote) are the two parallelization flavors — this was sectioning.
