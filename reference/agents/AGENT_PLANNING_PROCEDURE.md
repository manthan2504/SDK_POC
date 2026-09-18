# Agent Planning Procedure — how every Caliber agent gets designed

**Status:** standing instruction (user, 2026-09-03). Applies to every agent in
`docs/AGENT_WORK_DESIGN.md`, present and future. Read this before planning any agent;
re-read it when confused. It is written as a reusable brief so the same procedure runs
for the Profiler, the Role analyst, the Gap analyst, the Plan builder, the Question
generator, the Evaluator, the Guidance agent, the Adaptation agent and the Interviewer.

---

## 0. The two rules that override everything else

1. **Single source of truth: the PRD.** `Caliber-PRD-v1.6.pdf` decides product behaviour.
   Check it **before** planning, **every time**, and **whenever confused**. The AI-layer
   spec suite (`docs/llm/INDEX.md`) is the PRD's operational reading; where they
   disagree, the PRD wins and the suite gets corrected in the same change.
2. **Dual-provider by construction: local + Claude.** Console credits are unresolved, so
   development runs on a local model (ADR-0015). The day credits land, the switch back to
   Claude is **one config value**. Therefore every design, prompt, schema, validator,
   eval and line of code for an agent must work on BOTH, unchanged. A plan that only
   works on one is not a plan. Concretely:
   - one system prompt, one schema, one validator set — no per-provider forks in prompt
     text or call-site code; the provider seam absorbs the differences;
   - the schema is sent where the provider can constrain decoding and validated
     everywhere (the `run_structured` seam);
   - nothing the agent relies on may be a Claude-only or a llama.cpp-only feature unless
     the plan names the provider-neutral fallback;
   - evals run on both, reported separately, never pooled; the eval-of-record is the
     pinned Claude model (FR-I4), the local run is development evidence only.

## 1. Read-first order (before writing a word of the plan)

| Order | Read | For |
|---|---|---|
| 1 | The PRD, in full for a new agent; the relevant §7 stage, §9, §10, §10.1, §14 for a revisit | What the product needs |
| 2 | `docs/llm/workloads.md` — the CW rows the agent owns | What is registered; the arithmetic exclusion list (§2.6) |
| 3 | `docs/llm/overview.md` §1.2 behaviour spec, `safety.md` §7, `evals.md` §5, `grounding.md` §6 | The rules, the injection posture, the eval contract |
| 4 | `docs/llm/dev-cycle.md` §10 + `models.md` §3 | The model mapping and its constraints |
| 5 | The existing code for the agent, if any (`api/src/caliber/`) and `api/STATUS.md` | What is built vs claimed |
| 6 | `docs/BACKLOG.md` — the agent's items | Its slice; nothing is built ahead of it |
| 7 | `docs/AGENT_WORK_DESIGN.md` — earlier agents' sections | Decisions already taken that bind this one |

## 2. Research (spawn agents; use the internet where it earns its place)

Run these in parallel as separate research agents, each returning an evidence-backed
brief with source URLs. Prefer primary sources and 2025–2026 material. Mark anything
unverified as UNVERIFIED. Be skeptical of vendor marketing.

| Agent | Question it answers |
|---|---|
| **PRD traceability** | Every PRD requirement, rule, "never", entity field and risk that bears on this agent, cross-checked against the registry and the code (honoured / partial / not built / violated, with file:line) |
| **Task-domain research** | How this class of task is best prompted and constrained; known failure modes of small models vs frontier models on it; published evals and benchmarks; grounding and anti-fabrication techniques; injection risk on this agent's input surface |
| **Dual-provider research** | What differs between the local runtime and Claude for this agent's needs (schema subset both accept, caching, sampling, parameter shapes, thinking modes) and the design rules that keep one prompt and one schema portable |
| *(as needed)* | Anything the agent's domain adds: retrieval design for bar-grounded agents, psychometrics for question generation, judge-integrity literature for the Evaluator |

## 3. What every agent's plan must contain (the section template)

Write the agent's section in `docs/AGENT_WORK_DESIGN.md` with exactly these headings,
in this order. Missing headings mean the plan is not done.

1. **Identity** — PRD name and §10.1 one-liner; the CW rows it owns; its place in the
   §7 journey; the agent name in `routing.py` and the `cw` tag(s) it must emit.
2. **What the PRD demands** — the traceability table (requirement → obligation → status).
3. **What it must never do** — every "never", quoted from the PRD, each with its
   enforcement (code check, validator, eval slice). A "never" enforced only by the prompt
   is not enforced (overview §1.5).
4. **The determinism boundary** — what is arithmetic and stays out of the prompt
   (§2.6); what is genuinely the model's; the exact inputs the model gets (no profile
   dumps — grounding §6.4) and the exact outputs it may produce.
5. **Capabilities required of the model** — the cognitive tasks, ranked by difficulty,
   and which the local model is expected to pass, struggle with, or fail (with evidence).
6. **Output schema** — the Pydantic model(s): field by field, type, optionality, why.
   Reasoning fields before verdict fields (safety §7.2 property 2). Must sit inside the
   JSON-Schema subset BOTH providers accept.
7. **System prompt** — the full text, versioned. Structure: stable prefix (role, rules,
   schema description) first; volatile content (the candidate's text) last, fenced as
   inert data. Provider-neutral: no thinking-mode tokens, no vendor names, no features
   one side lacks. Length noted against the Claude cache minimum for the target shelf.
8. **Instructions and few-shot policy** — what the prompt instructs, what it deliberately
   does not, whether examples are used and why (examples must match the target
   distribution and never contradict the rules).
9. **Skills and tools** — whether the agent needs retrieval, a tool, or a skill; almost
   always no (every Caliber capability is a workflow step, none is an agent — overview
   §1.1). If yes, the ADR that authorises it.
10. **Validators and repair** — the code-side checks after the model returns (verbatim
    substring, canon ∈ candidates, numbers-verbatim, coverage), and the repair policy
    (one retry, fed the validator's complaint).
11. **Provider mapping** — shelf and model on Claude; model on local; parameters each
    side needs (thinking off locally; effort where allowed; sampling); the config lines
    that switch them; what the trace must record.
12. **Eval contract** — the named gating eval (evals §5.2): metric, threshold, gold-set
    size and strata, D6 / injection / D8 / tone slices as applicable, pass^k vs pass@k,
    and the rule that local results never gate.
13. **Failure semantics** — refusal, unavailability, schema failure, context overflow:
    class A/B/C/D per workloads §2.5, and what the user sees.
14. **Cost and latency budget** — tokens in/out per call on each provider; expected wall
    time locally; what is acceptable for the UX at that stage.
15. **Open decisions** — anything the plan could not settle, with the recommended
    reading and who decides.
16. **Build checklist** — the ordered implementation steps, each mapped to a backlog item
    and the CLAUDE.md §3 skills it requires. Nothing is built ahead of its slice.

## 4. Standing constraints (from CLAUDE.md §2, restated so no plan forgets them)

- Local-only native Windows; no Docker, no WSL2, no cloud services.
- LLM auth is Claude OAuth via `ant auth login`; never an API key; never
  `ANTHROPIC_BASE_URL`.
- HUM-3: synthetic fixtures only. No real resume touches this box.
- D8: assess and guide, never teach. D10 / FR-I5: no per-role content in code.
- Arithmetic owns dated facts; the model owns ambiguity; the app owns sequence.
- The system proposes; the human decides.
- No agent ships on vibes (FR-I4).

## 5. Output of the procedure

- A new or updated section in `docs/AGENT_WORK_DESIGN.md`.
- A WORKLOG entry naming the decisions taken and the research briefs consulted.
- If the plan changes an architectural boundary, an ADR in `docs/decisions/`.
- **No code.** Planning and building are separate steps; the user greenlights the build.

## 6. The original instruction, kept verbatim so intent never drifts

> Create a dedicated plan for each agent, what decisions we are taking. Every
> design/logical/code-base-related design must be compatible with our local model as
> well as, once the credit issue gets solved, we do a simple switch to Claude and are
> back to the original Claude plan — local + Claude, this duo must be in mind while
> planning as well as developing. Start with the Profiler agent first; further agents
> follow in the same file. Single source of truth: always our PRD. Check and understand
> the PRD every time before planning, and whenever confused. For each agent: research +
> plan based on the PRD — its capabilities, how we must design it, what system prompt to
> give it, whether it requires any skill, what to instruct it, what its constraints are,
> everything. Spawn multiple research agents, studying across the internet where required.
