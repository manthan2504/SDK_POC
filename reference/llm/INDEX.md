# Caliber AI Layer — Specification Suite

**This index routes with authority for everything the model layer does.** One file per
domain, global section numbers, one home per fact — other docs point, never restate. If a
claim here conflicts with `CLAUDE.md` §2, CLAUDE.md wins; if code conflicts with this suite
and no WORKLOG entry explains why, the code is wrong until proven otherwise.

| Need to know… | Read | Owns |
|---|---|---|
| **What runs THIS development cycle (Claude-only: models, auth, deltas)** | `dev-cycle.md` | §10 — **overrides §3/§9 where they disagree (ADR-0011)** |
| **How each agent is planned, and each agent's plan** | `../AGENT_PLANNING_PROCEDURE.md` · `../AGENT_WORK_DESIGN.md` | Per-agent design: PRD demands, prohibitions, schema, prompt, validators, eval contract, open decisions. PRD-first; local + Claude by construction |
| Why an AI layer, the behavior spec, the boundaries | `overview.md` | §1 |
| What the model may be asked to do — all 24 workloads, statuses, the arithmetic exclusion list | `workloads.md` | §2 |
| The fleet, API constraints, failure modes, calendar | `models.md` | §3 |
| How a request becomes a model call; gateway; prompt governance | `routing.md` | §4 |
| Eval contracts, gold sets, the judge's integrity stack, change rule | `evals.md` | §5 |
| Retrieval, embeddings, what may never be cached | `grounding.md` | §6 |
| Injection posture, the 8 properties, PII gates | `safety.md` | §7 |
| Trace sink, cost truth, gray-failure review cadence | `observability.md` | §8 |
| Build order, slice activation, open decisions | `roadmap.md` | §9 |
| Why any locked call was made | `../decisions/` (ADR-0001..0010) | — |
| The evidence behind all of it | `report.html` / the PDF + `research/p2_*.md`, `research/p3_*.md`, `research/p4_*.md`, `research/p5_agent_resources.md` (what the built agents need: tools, skills, internet, data) | — |

## Epistemic labels (used throughout; write nothing without one implied)

- **LOCKED** — user-ratified (Registry v2, Mapping v2, ADRs). Changed only by a new
  decision, never by drift.
- **PROVISIONAL** — locked-but-unproven: every model assignment until its named gating
  eval passes (FR-I4).
- **VERIFIED (date)** — checked against a primary source on that date; stale after major
  vendor news.
- **OPEN** — a listed decision with an owner (`roadmap.md` §9.5). Building on an OPEN item
  as if decided is a defect.

## The three sentences that govern everything

1. **Arithmetic owns dated facts; the model owns ambiguity; the app owns sequence.**
2. **The system proposes; the human decides.**
3. **No agent ships on vibes** — and no change to a prompt, model, rubric, or offset ships
   without a recorded eval result (`evals.md` §5.7).

## Current state (2026-09-01)

Phase 0A not started; every workload PROVISIONAL; `ant auth login` still owed (blocks all
real calls); the two agents partially built (CW-1, CW-3-clarify) ran on the fake provider.
First moves: `roadmap.md` §9.2.

*Suite created 2026-09-01 from the locked Registry v2 + Model Mapping v2 (WORKLOG Part 12,
plan `soft-kindling-pony`), the AI-Agent-Fleet reference study's documentation pattern, and
two fresh evidence passes (`research/p3_*.md`). Maintenance: update Status fields and §9.6
in the same change as the code they describe — status drift is the failure mode this suite
exists to prevent.*
