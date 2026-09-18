# ADR-0007: Grading stability comes from structure, not sampling parameters

## Status
Accepted — 2026-08-31 (constraint C-3) · elaborated by Model Mapping v2 (ADR-0009)

## Context
PRD §9 prescribes "low temperature for grading". That is permanently unimplementable on the
adopted judge models: `temperature`, `top_p`, `top_k`, `budget_tokens`, and assistant prefill
are **removed** on Claude Opus 5 / Sonnet 5 and return HTTP 400. `output_config.effort` is
the only depth control. There is no swap-back — this is the API's direction, not a gap.

## Decision
Judge determinism is engineered where it actually lives now:

1. **Rubric anchoring** — graded exemplars in the rubric, not vibes.
2. **Reasoning-fields-first JSON** — the schema orders `reasoning` before any score field on
   *every* schema'd call (structure-snowballing mitigation; standing constraint, policy 7).
3. **Structured output** — `output_config.format` / strict tools; never prose parsing.
4. **Multi-sample aggregation** — median-of-3 in the borderline band (replaces the dead
   low-temperature assumption; per Mapping v2 the xhigh re-samples run in a dedicated lane
   with their own cache prefix, because an effort change invalidates the cache).
5. **Pinned effort, versioned** — the judge's effort value is pinned per session and a change
   forces a gold-set re-run.
6. **Drift instrumentation** — 20-run verdict flip-rate measured on the gold set defines the
   borderline band; anchor-item interleaving watches production drift (`docs/llm/05-evals.md`).

## Alternatives considered
- **Grade on an older model that still accepts temperature.** Rejected: trades the strongest
  judge for a deprecated knob, and Sonnet 4.5-class models retire ~Sep 29.
- **Single-sample + hope.** Rejected: the PRD's own gate (zero false-pass) makes verdict
  stability load-bearing.

## Consequences
- Judge cost includes the borderline re-sample lane (≈$55–83/1k answers all-Opus; the
  Sonnet-workhorse hypothesis in bake-off could cut this — ADR-0009).
- PRD §9's temperature clause is formally superseded; the PRD is not edited — this ADR and
  `docs/WORKLOG.md` carry the correction.

## Enforced by
`docs/llm/03-models.md` (parameter table — what 400s where); `docs/llm/05-evals.md` (judge
integrity stack); GRD2-11 backlog item (multi-sample implementation).

## Sources
`docs/TECH_STACK.md` Constraints (2026-08-31); plan `soft-kindling-pony` Mapping v2 CW-13.
