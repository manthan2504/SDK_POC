# §5 — Eval Contracts (FR-I4: no agent ships on vibes)

The system that decides whether anything in workloads.md §2 is real. Evidence base:
`research/p3_judge_ops.md` (2026-09-01, sourced) on top of the locked Mapping v2 policies.
Where new evidence contradicts a locked choice, the contradiction is recorded here and
routed to eval design — never silently adopted, never silently ignored.

## 5.1 The two-tier taxonomy and the graduation rule

Every eval is one of two kinds, and knows which:

- **Capability evals** — measure a workload still being earned. Low pass rates are
  informative, not alarming; the target is improvement toward the row's gate.
- **Regression evals** — near-100% suites over everything already earned.
  **Release-blocking**: a red regression eval stops the change, full stop.

**Graduation rule:** when a capability eval's gate passes on the pinned model and holds on a
re-run, the passing cases freeze into the regression suite and the workload's Status moves
from `eval owed` to done. A saturated capability eval that never graduated is decoration —
flag it, don't keep running it.

**Reliability metric, declared per row** (not chosen ad hoc at runtime): pass^k for
user-facing reliability rows (grading, extraction — k successive successes); pass@k only
where one success genuinely suffices (overgenerate-and-rank authoring like CW-10); partial
credit for multi-component outputs (CW-9's question+reference+notes). Grade outputs, not
paths.

## 5.2 What every gating eval must carry

From the locked registry + mandatory slices (safety.md §7):

| Element | Requirement |
|---|---|
| Named gate | The workload row's eval, with numeric thresholds — unnamed gates don't exist (OPS-1's lesson) |
| D6 slice | Results by candidate level, junior → principal, always |
| Injection slice | On every user-content surface (CW-1/2/14/16) + the judge's persuasion slice |
| D8 slice | On CW-7/8/14/15/16 |
| Tone slice | On CW-5/7/13/14 |
| Provenance | Model id + prompt hash + rubric version + effort stamped on the results file |
| Success criteria | Written **before** the capability is built — quality, safety, latency, cost numbers per row |

## 5.3 Gold sets (the CW-20 contract)

- **Human-authored and human-filtered.** An AI-authored, AI-graded gold set validates
  nothing (Part 0.1's standing rule). Fakes come from a family-disjoint generator (Terra
  exception pending; alt S4 with recorded familiarity risk).
- **Five strata**: strong / weak / adversarial-fake-confident / **borderline** /
  **injection**. Borderline-oversampled around the ~70 line — those items carry most of the
  gate's information. Style-manipulation items (same content dressed with fake citations,
  authority tone, padding) carry a **score-delta tolerance** vs their plain twins.
- **Sizing is statistics, not taste.** "Zero false-passes on n should-fail items" bounds
  the true false-pass rate at ~3/n (rule of three, 95%): the ~200-item target must include
  **≥90–100 human-labeled *fail* items concentrated near the cut score** — that proves
  ≤3%; 30 would prove only ≤10%.
- **Admission gate: human inter-rater agreement.** 2–3 raters per item; weighted κ ≥ 0.6
  to admit; rubric itself revisited if human-human κ < 0.4. Human-human κ is reported
  beside judge-human κ — it is the ceiling.
- **Anchors** must include human-written and non-Claude-written items (anti-self-laundering).
- **Refresh trigger:** error analysis stops surfacing new failure modes (saturation), not a
  fixed count.

## 5.4 Judge metrics (how CW-13's gate is scored)

Raw agreement alone is gameable by class imbalance — a judge that passes everything scores
high agreement on a mostly-passing set. The gate therefore reports, together:

- **QWK per dimension** (0–20 ordinal scores — big misses penalized more than near-misses)
- **Verdict Cohen's κ** + the raw ≥85% agreement number (PRD gate, kept, but never alone)
- **False-pass and false-fail rates** from the confusion matrix — asymmetric by design
  (false-pass ≫), with **fail-class precision/recall** stated
- **20-run verdict flip-rate** on the gold set — defines the borderline band's width and
  feeds the <2% grade-stability SLO
- Persuasion-injected slice results, always

## 5.5 The judge integrity stack (locked policy 2 + evidence dispositions)

1. **Pin-and-log** served `response.model` + usage + `stop_details` per judgment.
2. **Harshness offset** is a per-(judge version × prompt hash) artifact, re-fitted on any
   model or prompt change, **stored with the scores it corrected** — deterministic layer
   over judge output, never inside the prompt.
3. **Anchor interleave** k=200 at ~1/5 decaying to ~1/20, with an **e-process drift verdict
   {none / system / judge}** — anytime-valid (no multiple-testing decay under continuous
   peeking); re-calibration trigger is "e-value exceeds threshold", not "mean dipped".
   20–50 anchor items carry pre-established human labels. Forced re-anchor on model change,
   prompt change, or vendor incident.
4. **Silent-update defense** (industry-verified failure class): retain response
   fingerprints, run the weekly fixed gold-set regrade (S4's canary), verify pinning
   actually disables auto-upgrade.
5. **Selective abstention:** inside the borderline band after resampling, the verdict
   escalates to human review ("grade pending") instead of shipping — resampling alone
   cannot deliver zero-false-pass; abstention + escalation can.
6. **Answer text is fenced as inert data** with the explicit grade-content-never-follow-it
   rule, plus epistemic-authority-marker preprocessing; a **permanent injection regression
   suite** rides every judge change (rubric-aligned grader injections hit 0.73–0.82 success
   in the wild; no single mitigation suffices — layers are enumerated in safety.md §7.3).
7. **No cross-model voting ensembles** for the gate (locked; independently re-confirmed:
   homogeneous panels are correlated voters, 3-family panels passed 55% of hacked answers).
   One strong judge + de-anchored cross-family S4 audit.

**Evidence dispositions routed to eval design (recorded 2026-09-01, sources in
`research/p3_judge_ops.md`):**

| Locked choice | New evidence | Disposition |
|---|---|---|
| Median-of-3 in borderline band | Mean-of-k beats median at every design tested; k≥5 is the reliability knee | **Eval-design comparison arm** in the CW-13 gold-set run: median-of-3 vs mean-of-5 (temp ~1.0 where supported). The winner locks; the mapping's "multi-sample aggregation" requirement is unchanged |
| Reasoning-fields-first strict JSON | Strict schemas measurably degrade reasoning; two-pass free-critique→extraction preserves both | **Second comparison arm**: strict single-pass vs two-pass. Reasoning-before-score ordering stays either way (audit artifact) |
| 21-level rubric descriptors (implicit) | Extreme-anchored descriptors (vivid 0/20 + midpoint) outperform full gradation ladders | Folded into CW-18 rubric-authoring guidance now (no lock conflicts) |

## 5.6 Harness architecture (AGT-09 design contract)

- **Eval-as-code, everything in git**: prompts, gold sets, scorer code, thresholds,
  calibration offsets — one commit = prompt version + dataset version + scores + offset,
  diffable across runs.
- **Per-sample transcripts are first-class artifacts** (not aggregates): error analysis is
  open-coding real transcripts → clustered failure modes → counts, and the failure-mode
  taxonomy in each workload row grows from it. Silent "gray" failures (plausible-looking,
  unusable — the majority class in production taxonomies) are found by **sampled transcript
  review on a stated cadence** (observability.md §8.4), never by error dashboards.
- **CI gate**: a structured result (per-case scores + top-level pass boolean) blocks merge
  on regression-eval red. Live-model evals can't run headless here (OAuth, ADR-0003) — the
  eval-of-record runs locally on demand and its stamped results file commits with the change.
- **Build-vs-adopt**: evaluate **Inspect AI** (MIT, fully local, AISI/Anthropic/METR
  provenance) as the harness base before hand-rolling `caliber-eval` — a recommendation
  entering AGT-09's design, not a decision (needs an ADR either way).

## 5.7 The one change-management rule

> **No change to a prompt, model assignment, rubric, tool schema, effort default, or
> calibration offset ships without a recorded eval-gate result — and no roadmap item is
> done until its eval contract exists and has run.**

This is CLAUDE.md §4's gate 4 ("LLM changes: eval run recorded; no eval = not done") given
its precise scope. "Recorded" means the stamped results file, committed.

## 5.8 Order of operations (what unblocks what)

1. **S3 cheap-tier gauntlet** — real schemas, ≥100 runs/model, real transport. Doubles as
   OPS-1's eval-of-record and the harness shakedown.
2. **Gold set build-out** 45 → ~200 (human task — the project's largest human-time item).
3. **Judge bake-off** — Opus vs Sonnet-workhorse at matched effort; S4 instruments
   (gemini-3.1-pro as measurement instrument only); aggregation + schema comparison arms
   (§5.5); Phase 0A gate: ≥85% agreement AND zero false-pass AND zero rank inversions,
   reproduced on the pinned model.
4. **Effort sweeps** — before any >medium default locks.
5. **S3 class-D migration bake-off** — before Oct 15 (models.md §3.7).
6. Gateway conformance before production workloads route through OpenClaw (§4.3).

Each step behind its named eval, drift monitoring interleaved from day one.
