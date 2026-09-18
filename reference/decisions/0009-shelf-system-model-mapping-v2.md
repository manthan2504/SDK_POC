# ADR-0009: The shelf system and Model Mapping v2

## Status
Accepted (LOCKED) — 2026-09-01 · every assignment provisional until its named gating eval runs (FR-I4)

## Context
Caliber needs different quality/cost tiers for 24 registered workloads without binding any
model name into agent code (D10/FR-I1: routing is config, not code). Six parallel researchers
evidenced the candidate models; two auditors (27 findings, zero fabrications) corrected the
v1 mapping before the user locked v2.

## Decision
**A shelf is a quality/cost tier with exactly one model behind it, bound in configuration
(`routing.py` tiers + settings), never in agent code.** Workloads name a shelf; the settings
file names the model; swapping a model touches one line and triggers that shelf's eval suite.

| Shelf | Model today | Role |
|---|---|---|
| S1 | `claude-opus-5` | Crown-jewel judgment + high-stakes authoring |
| S2 | `claude-sonnet-5` | Everyday generation — **never tone-bound work** (9.1% sycophancy) |
| S3 | `claude-haiku-4-5` | High-volume structured jobs — never send `effort` (errors) |
| S4 | `gemini-3.7-flash` (provisional) | Cross-vendor auditor — non-blocking in grading audit; blocking only at authoring time |
| local | `bge-small-en-v1.5` (EMB-1) | Embeddings, CPU, no network |
| local | MiniCheck-class verifier | CW-4 grounding veto — **pending user ratification** |

Standing rules locked with the mapping: **hard budget of 4 API models** (+2 local); the
**external-examiner rule** (the checker of a model's work is a different model); the
**runway rule** (nothing durable maps to <~9 months guaranteed runway without a named
migration owner and rehearsed fallback); **no cross-model voting ensembles** for the gate;
**no server-side fallbacks for the judge, ever**; dormant alternates (GPT-5.6 Sol/Terra)
and the CW-20 Terra offline exception are bench items requiring explicit ratification + the
D5 cross-vendor data gate before first use.

Full mapping table, fallback classes A–D, effort discipline, and cost model:
`docs/llm/03-models.md` and `docs/llm/04-routing.md` (the operational versions).

## Alternatives considered
- **Per-agent fixed models.** Rejected: model churn would become code churn ×24 workloads.
- **More models / best-tool-per-task.** Rejected: every extra model is a standing
  eval/prompt/migration tax; auditors caught v1 leaking a 5th/6th runtime model via fallbacks.
- **Fable 5 for the judge.** Disqualified: above budget ($10/$50) and mandatory 30-day
  retention with no ZDR — fails the PII posture.

## Consequences
- A dated obligation exists: **S3 class-D migration bake-off before Oct 15, 2026** (Haiku
  retirement floor). Owner + rehearsed fallback config are registry fields, not intentions.
- Price events are calendar items (Sol promo ends Nov 21; Gemini 3.7 Flash doubles Jan 1 —
  already modeled at post-promo rates).

## Enforced by
`routing.py` tier map + `_PRICES` (unknown model warns, never silently $0); FR-I4 gate —
no assignment graduates from provisional without its named eval; `docs/llm/09-roadmap.md`
tracks the bake-off deadlines.

## Sources
Plan `soft-kindling-pony` §§ Mapping v2 (LOCKED) + corrections log; `docs/llm/report.html`;
`docs/WORKLOG.md` Part 12.
