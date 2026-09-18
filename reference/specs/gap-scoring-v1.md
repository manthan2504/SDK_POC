# BAR-02 / BAR-03 — Gap scoring v1: ordinals, gap size, weights, recency, priority (DRAFT)

Sources: PRD §7.3 ("*gap size = required − demonstrated → priority = gap size × weight ×
recency*"; depth ladder "*aware → can build → can design → can defend under load*";
"*claimed-but-unproven skills are tagged probe-first regardless of score*"), §7.1 evidence
ladder (none / mentioned / demonstrated / led — `EvidenceStrength.rank`), D6, FR-A5, FR-B2,
`policy.py` s1.2 (`RECENT_WINDOW_MONTHS = 36`, recency classes `current | recent | dated |
None` produced by `signals.py`). Config: `config/scoring.yaml`.

**Design stance:** everything in this file is integer-or-simple arithmetic on values the
system already produces. No model touches a number here. Where the PRD's one-line formula
leaves a term undefined, this spec defines it and says why.

---

## §1 Ordinals and gap size (BAR-02)

### 1.1 Depth ordinals — what the bar *requires*

| Ordinal | `depth` | Meaning (§7.3 ladder) | Provable by |
|---|---|---|---|
| 0 | `none` | Not expected at this level | — |
| 1 | `aware` | Knows it exists, can name when it applies | capture (mentioned) |
| 2 | `can_build` | Has built with it under guidance or spec | capture (demonstrated) |
| 3 | `can_design` | Chooses it, shapes it, owns the trade-offs | capture (led) |
| 4 | `can_defend` | Defends it under load: failure modes, scale, cost — an interviewer's push-back | **assessment only** |

The bar's depth matrix (BAR-16) states one ordinal per (sub-skill × level). Ordinal 0 at a
level means the sub-skill is out of scope for that level and is excluded from that
candidate's gap map entirely.

### 1.2 Evidence ordinals — what the profile *demonstrates*

Exactly `EvidenceStrength.rank`, unchanged: `none 0 · mentioned 1 · demonstrated 2 · led 3`.
These are already derived per skill on every snapshot by the evidence ladder (policy s1.2)
and are never self-reported.

### 1.3 The crosswalk and the capture ceiling

```
demonstrated_depth = evidence_to_depth[evidence_strength]
                   = { none: 0, mentioned: 1, demonstrated: 2, led: 3 }
```

The mapping is the identity on ordinals — deliberately. The ladders were designed in
parallel (§7.1 vs §7.3) and line up one-to-one, and inventing a non-identity mapping would
be a judgement nobody has evidence for.

**The capture ceiling (load-bearing):** onboarding can prove at most depth 3. Depth 4 —
*can defend under load* — is only ever earned by passing the topic's probe (an `Attempt`
with verdict pass, S3+). This is D8's boundary written into arithmetic: the profile can say
"I designed it"; only the assessment can say "and it holds up". So at levels whose required
depth is 4 (staff+ per anchor), **every** such sub-skill starts as a gap of at least 1,
which is exactly the PRD's "you present as Senior, but…" made computable.

### 1.4 Gap size

```
required          = bar.depth[sub_skill][calibration_level]        # 0..4
demonstrated      = evidence_to_depth[profile.evidence[sub_skill]] # 0..3 (4 after a pass)
gap_size          = max(0, required − demonstrated)                # 0..4
```

- `gap_size = 0` → proven at this level; **not a gap**, excluded from the map (FR-C2:
  the plan skips proven skills). It is still listed in the plan's "proven" summary so the
  candidate sees credit, not silence.
- Unmatched sub-skill (the resolver, BAR-19, finds no profile skill) → `demonstrated = 0`.
- **Reach gap** (target level above calibration): computed a second time at
  `target_level` and shown as a separate "reach" figure, never merged into the primary map
  (BAR-01 §3.3).
- Probe-first (`SkillClaim.probe_first`) does **not** alter gap size; it alters the bucket
  (BAR-04). "Regardless of score" means regardless of this number.

### 1.5 What deliberately stays OUT of gap size

The per-skill `depth_score` (0–100, policy s1.2) blends corroboration, quantified impact and
recency into one number. It is **not** used in gap size: gap size must stay an ordinal
difference a candidate can read ("*the bar wants design-level; your evidence shows
build-level*"). `depth_score` is displayed alongside as the evidence-strength explainer it
already is, and recency enters priority instead (§3).

---

## §2 Weights (BAR-03)

### 2.1 Authored scale

Each sub-skill carries an integer `weight ∈ {1,2,3,4,5}` per bar (not per level — how
heavily a role tests something is a property of the role; how deep is the property of the
level). Authoring guidance in BAR-12: 5 = the interview turns on it; 3 = expected, probed
once; 1 = nice to see.

### 2.2 Normalization — fixed divisor, not max-in-bar

```
weight_norm = weight / 5          # 0.2 … 1.0
```

Fixed divisor so that a weight of 3 means the same thing in every bar and every version. A
max-in-bar normalization would let one 5 in v1.1 silently re-scale every other sub-skill's
priority and would make cross-version readiness comparisons (§7.8) meaningless.

### 2.3 JD re-weighting

A JD overlay (BAR-05) multiplies `weight_norm` by a bounded factor before priority is
computed. It never touches `required` depth.

---

## §3 Recency and priority (BAR-03)

### 3.1 The recency factor — evidence staleness raises urgency

The PRD's `× recency` is read as: **stale evidence is weaker evidence, so a gap backed only
by dated work is more urgent to probe.** The factor is ≥ 1 and multiplies priority; it never
changes `gap_size` (which stays an honest ordinal difference).

| `recency` class (from `signals.py`) | Factor | Why |
|---|---|---|
| `current` | 1.00 | In use today |
| `recent` (≤ 36 months) | 1.00 | Same window `policy.RECENT_WINDOW_MONTHS` already treats as fresh |
| `dated` (> 36 months) | 1.25 | The demonstrated depth was real once; whether it still holds is exactly what a probe finds |
| `null` (undated role) | 1.10 | Unknown is between fresh and stale; the undated flag already nudges for dates |
| evidence `none` | 1.00 | Nothing to decay |

`recent_window_months` in `scoring.yaml` **must equal** `policy.RECENT_WINDOW_MONTHS`; a
unit test pins the two together so the 36 cannot fork.

A continuous half-life form (`factor = 1 + 0.5·(1 − 2^(−months/36))`) is recorded in the
config as `mode: continuous`, **off** for v1: piecewise is explainable in one sentence to a
candidate; a half-life is not, and explainability is FR-B3.

### 3.2 Priority

```
priority = gap_size × weight_norm × recency_factor      # 0 … 5.0, rounded to 2 dp
```

Ordering within a bucket: `priority` desc → `weight` desc → bar authoring order. Ties are
therefore decided by the author's own ordering, never arbitrarily.

### 3.3 Worked example (Ravi, senior, calibration = senior)

| Sub-skill | required@senior | evidence | demonstrated | gap | weight | recency | priority |
|---|---|---|---|---|---|---|---|
| RAG design & failure modes | 3 | led | 3 | 0 | 5 | current | — (proven) |
| LLM evaluation & judge calibration | 3 | mentioned | 1 | 2 | 5 | current | 2 × 1.0 × 1.00 = **2.00** |
| Multi-agent orchestration defense | 3 | none | 0 | 3 | 4 | — | 3 × 0.8 × 1.00 = **2.40** |
| Observability of LLM systems | 2 | demonstrated | 2 | 0 | 3 | dated | — (proven; staleness noted) |
| Guardrails in layers | 2 | mentioned | 1 | 1 | 3 | dated | 1 × 0.6 × 1.25 = **0.75** |

Matches persona §6: "strong on building, weak on eval/observability and multi-agent
orchestration defense" — the top two priorities are exactly those.

---

## Ratification checklist

**BAR-02**
1. Depth ordinals 0–4 with `can_defend` (4) provable **only by assessment** — ok?
2. Evidence→depth crosswalk is the identity (none 0 · mentioned 1 · demonstrated 2 · led 3) — ok?
3. `gap_size = max(0, required − demonstrated)`; gap 0 = proven and excluded from the map — ok?
4. `depth_score` stays out of gap size (display only) — ok?
5. Reach gap computed separately at target level, never merged — ok?

**BAR-03**
6. Weights 1–5 per sub-skill per bar (not per level), normalized by fixed `/5` — ok?
7. Recency factor ≥1 on **priority** (current/recent 1.0 · dated 1.25 · unknown 1.10), piecewise on the existing 36-month window — ok, or different numbers?
8. `priority = gap × weight_norm × recency`, tie-break weight then author order — ok?
