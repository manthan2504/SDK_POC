# BAR-06 — Role-bar versioning, pinning and migration policy (v1, DRAFT)

Sources: PRD §7.3 ("*Versioned — the bar drifts; updated as the market moves and (Phase 2)
as real captured interview questions refine it*"), §10 (RoleBar; AssessmentPlan → Topic;
Progress), §7.10 outcome loop, D5 (two-senior sign-off), §7.8 ("% ready" weighted by bar
importance), the confirmation-freeze precedent in `confirmation.py` (a policy change alone
must never invalidate what a candidate confirmed). Implemented later by BAR-32.

## 1. Version scheme

`MAJOR.MINOR`, per `role_key`. Two numbers because two different things drift:

| Bump | What changed | Examples |
|---|---|---|
| **MINOR** | Content that does not change *identity* | wording of a sub-skill, weight values, rubric anchors, reference answers, landscape.yaml refresh, tier overrides |
| **MAJOR** | Anything that changes what a sub-skill *is* or the depth matrix | add / remove / rename a competency or sub-skill key; any change to `required` depth at any level; competency restructure |

The YAML **format** itself carries a separate `schema_version` (BAR-12) so a format change
is not confused with a content change.

## 2. Status lifecycle and the publish gate

```
draft ──▶ in_review ──▶ published ──▶ retired
   ▲           │
   └───────────┘  (review findings)
```

**Publish gate for any version** (this is the D5 sign-off made mechanical):
1. Linter passes (BAR-12): every sub-skill has a key, a depth for every supported level, a
   weight, a `how_tested`; no tier override above 25 %; every landscape item has a dated
   source; no key collides across competencies.
2. **Two sign-off records** on this exact version hash — founder + the second senior (D5).
   For the beachhead v1.0 this includes the recorded inter-author agreement rate (BAR-18).
3. The gap-analyst gold set (BAR-29) passes against this version once it exists; for v1.0
   the S2 exit gate stands in.
4. Semver check: the diff against the previous published version classifies as the bump
   claimed (a "minor" that touches a depth cell is rejected).

Draft versions (`0.x`) are never served to a candidate. Exactly one `published` version per
`role_key` is the **current** version; earlier published versions stay queryable forever.

## 3. Pinning — what records the version it was built on

| Record | Pins `bar_version` | Mutable after? |
|---|---|---|
| `GapMap` | yes | No — a new map is a new row |
| `JDOverlay` | yes | No |
| `AssessmentPlan` | yes | No |
| `Attempt` | yes (inherited from plan) | No |
| `Progress` / readiness score | computed against the plan's pinned version | — |

The principle is the confirmation-freeze one: **a bar change must never silently re-score
something a candidate already did.** An attempt graded against v1.0's rubric anchors stays
graded against them.

## 4. Migration decision matrix (what BAR-32 implements)

| Candidate state | MINOR bump | MAJOR bump |
|---|---|---|
| Has a gap map, no plan yet | Recompute lazily on next view; show "*your bar was updated (v1.1)*" with a diff summary | Same, plus the map is marked stale until viewed |
| Plan generated, assessment not started | Plan keeps its pin; notice offers "*regenerate on v1.1*" (free tier, D3) | Plan marked stale; regeneration offered; the old plan stays viewable |
| Assessment in progress | Plan **keeps its pin until completion**; notice only | Keeps its pin; **passed topics carry forward** to a regenerated plan iff the sub-skill key is unchanged; retired keys → topic archived, not counted either way |
| Assessment complete | Nothing changes; readiness score stays computed on the pinned version, labelled with it | Same; "reassess on the current bar" is offered as a new plan |

Two rules cut across every cell:
- **Never reduce credit retroactively.** A topic passed at v1.0 is passed. If v2.0 raises the
  required depth, the *new* plan may re-open it — as a new topic on the new version, never as
  a silent downgrade of the old result.
- **Never hide the version.** Every map, plan and score surface shows `senior_ai_engineer
  v1.1`; comparability across versions is a labelled caveat, not an assumption.

## 5. Retirement

Retiring a version (e.g. after a major bump has been current for a defined window) stops new
plans on it; existing pins keep resolving. `source_ref`s (gap-buckets §4) resolve against the
pinned version forever — a citation that stopped resolving would break FR-B3.

## 6. Provenance

Every published version records: author(s), sign-off records with timestamps, the linter
report hash, the gold-set eval result (when applicable), and — from Phase 2 — the outcome-
loop signals (CW-19/CW-22) that motivated the bump. This is the audit trail that makes
"the bar drifts as the market moves" a claim someone can check.

## Ratification checklist

1. `MAJOR.MINOR` with MAJOR = identity/depth-matrix change, MINOR = content — ok?
2. Publish gate = linter + two sign-offs on the version hash + eval (v1.0: S2 exit) + semver check — ok?
3. Gap map / overlay / plan / attempt pin their version, immutably — ok?
4. Migration matrix as tabled; passed topics carry forward on unchanged keys; never retroactive downgrade — ok?
5. Versions never disappear; citations resolve forever — ok?
