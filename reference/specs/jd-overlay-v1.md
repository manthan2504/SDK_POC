# BAR-05 — JD overlay semantics and bounds (v1, DRAFT)

Sources: D7 ("*JD present → assessment built around the JD; no JD → built around target
role + experience level*"), PRD §7.3 ("*JD overlay — a supplied JD re-weights the bar toward
what that role asks for*"), §7.2 JD branch, §7.5 ("*a supplied JD shifts emphasis*"),
D6, FR-I5, `docs/llm/workloads.md` CW-6 (JD decomposition — LLM, S3 shelf, coverage-
validated). Config: `config/scoring.yaml` → `jd_overlay`.

## 1. The one-sentence semantics

**A JD changes emphasis, never the bar and never the level.** It re-weights sub-skills the
posting stresses and may promote a tier one step; it cannot invent a sub-skill, deepen a
requirement, or move the candidate's calibration level. The PRD says "shifts emphasis" and
"re-weights" — both are weight words — and D6 makes depth a function of *years*, which a
posting does not change.

## 2. Division of labour

| Step | Owner | Notes |
|---|---|---|
| Decompose the JD into requirement statements and map each to bar sub-skills | **CW-6 (model)** | Recall-first with a coverage validator; every sentence mapped or explicitly discarded (workloads.md) |
| Turn those mappings into an overlay and **apply** it | **Arithmetic** | This spec. The model's output is an input record; the app decides what it is allowed to change |
| Show the candidate what the JD changed | UI | "Emphasized by your posting" chip on the affected rows; the unmapped list |

## 3. The `JDOverlay` record

```yaml
role_key: senior_ai_engineer
bar_version: "1.0"          # the overlay is built against one bar version (BAR-06)
jd_sha256: …                # identity of the pasted text
entries:
  - sub_skill: llm_eval.judge_calibration
    weight_multiplier: 1.6  # clamped 0.5 … 2.0
    tier_promote: true      # one step up only
    evidence: "…own the evaluation harness and judge calibration…"   # verbatim JD quote
unmapped_requirements:
  - text: "…experience with Vertex AI Agent Builder…"
    note: "Not on this bar yet"
```

`evidence` is mandatory and must be a verbatim substring of the JD (the same grounded-or-
dropped rule the Profiler enforces in code); an entry without one is dropped before apply.

## 4. Field-level change matrix — what an overlay may touch

| Bar field | May change? | Bound | Why |
|---|---|---|---|
| `weight` (via `weight_norm`) | **yes** | multiplier clamped to **[0.5, 2.0]**; result clamped to [0.1, 1.0] | "Re-weights toward what that role asks for" |
| `tier` | **yes, up one step** | `optional → should_know`, `should_know → must_know`; never onto/off `ai_landscape` or `claimed_but_unproven` | A posting that leads with a skill makes it should/must for *this* opportunity |
| `required` depth | **no** | — | D6: depth is a function of level, not of the posting |
| calibration level | **no** | — | D6 |
| sub-skill set (add / remove) | **no** | — | A JD cannot bypass the authored, dual-signed bar; unmapped needs are *recorded*, not injected |
| `landscape` flag | **no** | — | Sourced list (BAR-33), not per-posting |
| Number of touched sub-skills | — | ≤ **40 %** of the bar's in-scope sub-skills | Beyond that the "overlay" is a different bar — surface it as bar-drift input (CW-19) instead |

Multipliers below 1.0 are allowed (a posting that de-emphasizes something) but **never
push a `must_know` row below `should_know`** — de-emphasis lowers priority, not the level
expectation.

## 5. Application order

```
weight_norm' = clamp(weight_norm × multiplier, 0.1, 1.0)
tier'        = promote(tier) if tier_promote and tier ∈ {optional, should_know}
priority     = gap_size × weight_norm' × recency_factor        # gap-scoring §3.2
bucket       = rule table (gap-buckets §2.3) using tier'
```

Gap size is computed **before** the overlay and is unaffected by it — the candidate's
distance from the bar is a fact; the posting only reorders what to close first.

## 6. Lifecycle

- No JD → identity overlay (no record); the plan is "built around the target role + level".
- An overlay is built once per (JD sha256 × bar version) and cached; editing the JD text
  rebuilds it.
- A **major** bar bump invalidates the overlay (sub-skill keys may have changed); a minor
  bump keeps it (BAR-06 migration matrix).
- `unmapped_requirements` are shown to the candidate ("*this posting also asks for X, which
  isn't on our bar yet*") and queued as CW-19 drift signal — they are never silently lost,
  and never silently turned into gaps.

## 7. What the candidate sees (§7.2 / §7.4 surfaces)

The confirm step already states the branch ("*built around the job description you
pasted*"). On the gap map: rows the overlay touched carry an "emphasized by your posting"
marker with the quote on hover/expand; unmapped requirements appear as a short list under
the map. No black box (§7.4 transparency principle).

## Ratification checklist

1. JD changes **emphasis only** — weights (×0.5–2.0, one-step tier promotion), never depth, level or the sub-skill set — ok?
2. Every overlay entry needs a verbatim JD quote, else dropped — ok?
3. ≤ 40 % of in-scope sub-skills may be touched; beyond → drift signal, not overlay — ok?
4. De-emphasis never demotes a must_know below should_know — ok?
5. Unmapped JD requirements shown to the candidate and fed to bar drift (CW-19), never injected as gaps — ok?
