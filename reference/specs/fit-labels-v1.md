# BAR-26 — Fit labels and the standing read (v1, DRAFT)

Sources: PRD §7.2 ("*Our honest read — from the real profile, Caliber recommends roles that
genuinely fit, each with a fit label: **Strong fit** (ready-ish), **Stretch** (reachable,
here's the work), **Not yet** (real distance, here's why)*"), §7.2 honesty-over-flattery and
the motivation guardrail, D6 (experience-calibrated), `docs/llm/workloads.md` CW-5.
Config: `config/scoring.yaml` → `fit`.

## 1. The one-sentence semantics

**The label is arithmetic; only the sentence around it is the model's.** A fit label is a
claim about a person, derived from their evidence against an authored bar. Nothing about
that is ambiguous, so nothing about it is generated — CW-5 narrates a label it is handed and
may not disagree with it.

## 2. Division of labour

| Step | Owner |
|---|---|
| Coverage, label, reach read, direction | **Arithmetic** (`role_fit.py`, this spec) |
| Saying it to a candidate in two or three honest sentences | **CW-5 (model)** |
| Deciding whether to act on it | **The candidate** |

## 3. Coverage

Computed over the gap map's in-scope rows at a given level:

```
attainable  = rows where required_depth > 0 and not assessment_only
denominator = sum(weight × required_depth)          over attainable
numerator   = sum(weight × min(demonstrated, required))  over attainable
coverage    = numerator / denominator                    # 0.0 … 1.0
```

Weighting by `weight × required_depth` means a heavily-tested deep requirement moves the
number more than a light shallow one, which is the whole reason the bar carries weights.

**`assessment_only` rows are excluded from the denominator, and they cap the label.**
Required depth 4 is "can defend under load", which `gapmap.py` records as earned only by
passing a probe. Scoring it as a failure at capture time would report a deficiency the
candidate has not been given the chance to disprove; scoring it as a pass would be a lie.
So it is excluded from the ratio **and** capped: while any unproven depth-4 requirement
remains, the best available label is **Stretch**. Strong fit is earned by demonstration, not
by capture — which is exactly the product's argument.

## 4. The labels

| Label | Rule |
|---|---|
| **Strong fit** | `coverage ≥ strong_min` **and** no `must_know` gap **and** no unproven `assessment_only` requirement |
| **Stretch** | `coverage ≥ stretch_min` |
| **Not yet** | below `stretch_min` |

Defaults: `strong_min = 0.85`, `stretch_min = 0.55`. **These are unvalidated starting
values.** They have no PRD basis and no outcome data behind them; D2 says the readiness
score is rubric-derived now and outcome-calibrated in Phase 2, and the same applies here.
They are config, not code, so they move without a deploy.

**"Not yet" is the floor of the vocabulary and it is deliberate.** §7.2's guardrail is
"never 'you're not good enough'". There is no fourth, worse label, and the copy that renders
it always carries the distance and the path — a label without a next step is a verdict, and
this product does not issue verdicts.

## 5. The no-bar rule

**When `role_matches_target` is false, there is no label at all.** Not "Not yet" — *none*.

A fit label computed against a different role's bar is the arithmetic equivalent of a
hallucination: confident, specific and about nothing. This has happened here before (a
Director of Product being told in detail what they must know about hallucination
mitigation), and `gapmap` already refuses to produce rows in that case. The label refuses
for the same reason, and the candidate is told plainly that no bar exists for their role yet.

The same holds when `years_experience` is unknown: no years means no calibration level (D6),
and a fit read at a level nobody derived is not a read.

## 6. The reach read (closes the `reach_gap` flag)

§7.2 requires framing as "realistic launch point **and** reach goal". Two coverages, not one:

- **calibrated** — at `calibration_level`, derived from years (D6). This is the honest read.
- **reach** — at `target_level`, when the candidate picked a different one. Computed only
  when the bar supports that level.

`direction` is then:

| Value | When | The sentence it licenses |
|---|---|---|
| `overshoot` | target level above calibration level | "you present as Senior; your demonstrated depth maps to Mid for this bar" |
| `undersell` | target level **below** calibration level | "you are aiming below what your evidence supports" |
| `aligned` | same level, or no target stated | the calibrated read alone |

**Undersell is first-class, not an edge case.** The PRD says the principle "cuts both ways",
and a system that only ever tells people they are short is not honest, it is merely harsh.

## 7. What the label may never do

| Never | Enforcement |
|---|---|
| Be produced from a bar for another role | §5, in `role_fit.py`; returns `None`, not a label |
| Be produced without a calibration level | §5; years is the only source (D6) |
| Read the bar at the candidate's *chosen* level | `calibration_level` is the only level the labels are computed at; `reach` is reported separately and labelled as ambition |
| Be changed by the model | CW-5 receives the label as input and its output has no label field |
| Say "not good enough" | The enum has three values and no fourth |

## Ratification checklist

1. Coverage is weighted by `weight × required_depth`, not a plain row count — ok?
2. `assessment_only` (depth 4) rows are excluded from the ratio and cap the label at Stretch until proven — ok?
3. `strong_min = 0.85`, `stretch_min = 0.55` as unvalidated starting values, moved by config — ok?
4. No label at all (not "Not yet") when the bar is for a different role, or when years are unknown — ok?
5. `undersell` is reported as prominently as `overshoot` — ok?
