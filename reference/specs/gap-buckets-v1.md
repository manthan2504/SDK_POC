# BAR-04 — The five gap buckets and their classification rules (v1, DRAFT)

Sources: PRD §7.3 ("*Bucketed: must-know (for their experience), should-know (for the
role/JD), claimed-but-unproven, optional/beneficial, AI-landscape additions the market now
expects*"), FR-B4, Appendix D (the sample bar's bucket examples), §7.1 ("*Claimed-but-weak →
flagged probe area, targeted first*"), `SkillClaim.probe_first` (policy s1.2). Config:
`config/scoring.yaml` → `buckets`.

## 1. The canonical enum

`GapBucket` — added to `enums.py` on ratification; consumed by BAR-09/BAR-10 models and the
gap-map API. Order is the PRD's own order (FR-B4) and is also the **display order**:

| Order | `bucket` | PRD name | One-line meaning for the candidate |
|---|---|---|---|
| 0 | `must_know` | must-know (for their experience) | "Expected at your level; not demonstrated" |
| 1 | `should_know` | should-know (for the role/JD) | "The role — or this posting — asks for it" |
| 2 | `claimed_but_unproven` | claimed-but-unproven | "You claim it; your evidence doesn't yet show it" |
| 3 | `optional` | optional / beneficial | "Nice to have; depth bonus" |
| 4 | `ai_landscape` | AI-landscape additions | "The market expects awareness of this now" |

## 2. Where a bucket comes from — two inputs, one rule table

A sub-skill's bucket is decided by **the bar** (what tier it is at the candidate's level)
and **the profile** (whether the claim is unproven). Neither is a model output.

### 2.1 Tier — derived from required depth, overridable by the author

The bar's depth matrix already says how much a level needs; the tier falls out of it, which
keeps buckets level-calibrated automatically (D6) without a second matrix to author:

| `required` depth at calibration level | Derived tier |
|---|---|
| 3 or 4 | `must_know` |
| 2 | `should_know` |
| 1 | `optional` |
| 0 | out of scope — never appears |

An author may pin `tier` explicitly per (sub-skill × level) when the derivation is wrong for
a specific case (e.g. a depth-2 sub-skill that is nonetheless the interview's opening
question). Overrides are visible in the bar diff and counted by the linter (BAR-12): more
than 25 % overridden rows fails the lint, because at that point the depth matrix is lying.

### 2.2 Landscape — an explicit list, not a tier

`ai_landscape` items come only from `rolebars/<role_key>/<version>/landscape.yaml` (BAR-33),
each with a dated source. They are sub-skills like any other (they have depth + weight) but
carry `landscape: true`. A tier override can never move a landscape item, and a landscape
item cannot be promoted by a JD.

### 2.3 Precedence (first match wins)

```
1. sub_skill.landscape            → ai_landscape        (shown only if gap_size > 0)
2. claim.probe_first              → claimed_but_unproven (shown even if gap_size == 0)
3. gap_size == 0                  → PROVEN — not in the map; listed under "proven"
4. tier(required, override)       → must_know | should_know | optional
```

Rule 2 is the only case where a sub-skill with **no arithmetic gap** enters the map: a
claim rated `led` by a thin project the probe-first flag distrusts is exactly what "§7.1:
targeted first — mirroring what a real interviewer attacks" means. The gap row's reason
says so plainly ("*Rated 'led' on one project with little depth captured — the assessment
will verify this first*").

### 2.4 Probe-first is the profile's signal, not the bar's

`probe_first` is set by the evidence ladder (policy s1.2: claimed high, evidenced low; vague
or single-thin-project support; consistency flags). The bucket rule reads it; it never
recomputes it. One source of truth for "unproven".

## 3. Ordering and counts

- Buckets render in enum order. Within a bucket: `priority` desc, then weight, then bar
  order (gap-scoring §3.2).
- `claimed_but_unproven` sorts by evidence rank desc (the loudest unproven claim first),
  since its priorities are often 0.
- The headline count the UI shows is **must_know + claimed_but_unproven** — the two the
  assessment will open with. Optional and landscape are never counted against the
  candidate in any "% ready" figure (§7.8 weights by role-bar importance, and importance
  means must/should).

## 4. Explainability contract (FR-B3)

Every row carries: bucket, `reason` (plain English), `source_ref` (resolvable pointer into the
bar version: `senior_ai_engineer@1.0#llm_eval.judge_calibration`), the three numbers
(required, demonstrated, gap), and the forward link to the plan topic (PLN-10 chain). The
reason has a **deterministic template per (bucket, gap_size) cell** (BAR-24's "fallback
templates"); the gap-analyst agent may replace the template with a grounded sentence, but
the template ships first and never disappears — a row can never be reasonless because a
model was unavailable.

## Ratification checklist

1. Five buckets, PRD order = display order — ok?
2. Tier derived from required depth (3–4 must, 2 should, 1 optional, 0 out of scope) with an author override capped at 25 % of rows — ok?
3. Precedence landscape → probe-first → proven-excluded → tier — ok?
4. Probe-first rows appear even at gap 0 — ok?
5. Headline count = must_know + claimed_but_unproven; optional/landscape never count against "% ready" — ok?
6. Deterministic reason templates per cell, agent may enrich but never replace with nothing — ok?
