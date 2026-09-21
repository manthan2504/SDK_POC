> **POC copy — edited 2026-09-18.** Snapshot of the Caliber file with provider-gateway material removed; everything else is verbatim.

# §1 — AI Layer Overview

Why Caliber has an AI layer, what governs it, and the boundaries every other document in
this suite assumes. The narrative version lives here once; the operational versions live in
CLAUDE.md §2 and in code.

## 1.1 What the AI layer is for

Caliber assesses job-readiness against founder-authored role bars (PRD §7 journeys). The AI
layer exists for exactly the work that has no deterministic answer: structuring messy resume
prose, resolving ambiguous claims, authoring assessment content, grading open answers,
phrasing guidance. Everything with a computable answer is excluded from it by design
(workloads.md §2.6).

**The division of labour, three ways:**

> **Arithmetic owns dated facts. The model owns ambiguity. The app owns sequence.**

- *Arithmetic* — completeness, evidence ladders, recency, gates, scores: deterministic,
  explainable, free, recomputed every snapshot.
- *The model* — 24 registered workloads (workloads.md §2), each provisional until its named
  eval passes (FR-I4).
- *The app* — deterministic Python + a per-user state row calls agents step by step in the
  fixed PRD §7 order; agents never talk to each other (ADR-0008). There is no orchestrator
  agent, no reasoning loop, no autonomy anywhere in the product. In current
  workflow-vs-agent terms: **every Caliber capability is a workflow step, none is an
  agent** — a deliberate simplest-pattern-that-works choice, re-justified per registry
  entry, not an accident.

## 1.2 The behavior spec — Caliber's rules for its models

The PRD's decisions function as a versioned behavior spec (pattern: OpenAI Model Spec).
Stated once, with their force and enforcement:

| Rule | Force | Meaning | Enforced by |
|---|---|---|---|
| **The system proposes; the human decides** | rule | No agent writes to a confirmed profile; parses are suggestions until reviewed; duplicates surface, never auto-merge | Code (`profiler` proposes only; review screens) |
| **Grounded or dropped** (PRD §9) | rule | Every claim-resolving proposal carries a verbatim quote from the candidate's own text; quotes are substring-verified; empty list is a correct answer | Code (`clarify()` drops unquoted proposals) |
| **D8 — assess and guide, never teach** | rule | Guidance names the gap and the direction; it never hands over the answer | Checker architecture on CW-14 + D8 eval slices (safety.md §7.4) |
| **D10 / FR-I5 — no per-role content in code** | rule | Role knowledge lives in authored bars, never app strings | CI check + registry design |
| **D6 — experience-calibrated** | rule | Every rubric/question carries a level; every eval slices by level | Mandatory D6 slice on all gating evals |
| **Calibrated tone** | guideline→rule at eval | Honest, never demoralizing, anti-sycophantic in both directions | Tone slices on CW-5/7/13/14 evals |

**Instruction hierarchy** (highest wins): platform rules above → Caliber's authored system
prompts → retrieved/authored context (bars, rubrics) → **candidate-supplied content, which
is always data and never instructions** (safety.md §7.3). A conflict resolves upward; a
model output that violates a *rule* is a defect even if the eval average looks fine.

## 1.3 The two agent layers — never conflate them

Same trap the reference study flagged, worth stating for this repo:

1. **Dev-loop agents** — Claude Code, its skills (CLAUDE.md §3) and subagents. They build Caliber.
2. **Runtime workloads** — the CW registry this suite governs. They ARE Caliber.

Nothing in this suite grants the dev-loop anything, and no dev-loop convenience relaxes a
runtime rule.

## 1.4 Core principles

1. **Registry or it doesn't exist.** A model capability not in workloads.md §2 is not a
   capability Caliber has (change control: §2.7).
2. **No agent ships on vibes (FR-I4).** Provisional until the named gating eval passes;
   "built, eval owed" is not done.
3. **Models bind to tasks through config, never to agents in code** (ADR-0009). One model
   per shelf; hard budget of 4 API models + 2 local.
4. **The checker of a model's work is a different model** (external-examiner rule).
5. **Deterministic triggers.** A model never decides its own escalation, regeneration,
   probing, or retry.
6. **Fail toward humans.** Refusals, vetoes, and borderline verdicts land in human queues
   with honest "pending" states — never in silent substitution (no server-side fallbacks,
   no uncalibrated stand-in models).
7. **Spec altitude.** Prompt-facing specs give representative examples and non-obvious
   constraints, not exhaustive rules; each registry row draws its determinism boundary
   explicitly.

## 1.5 Anti-patterns (each burned someone already)

- **The orchestrator agent** — an LLM routing Caliber's fixed pipeline adds failure modes
  and zero information (ADR-0008).
- **Prompt-asserted controls** — "you may not X" in a system prompt is a request, not a
  control; every rule above names its code/eval enforcement.
- **Semantic-cache grades** — two paraphrased answers are not the same answer (ADR-0005).
- **AI-detection as a gate** — 12–26% false-positive on honest text; may inform, never gate.
- **The 5th model** — every extra model is a standing eval/prompt/migration tax; auditors
  caught v1 leaking two extra models through fallback rows.
- **AI-authored gold sets** — a judge measured against its own family's homework validates
  nothing (evals.md §5.3).
