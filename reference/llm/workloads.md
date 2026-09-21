> **POC copy — edited 2026-09-18.** Snapshot of the Caliber file with provider-gateway material removed; everything else is verbatim.

# §2 — Workload Registry (v2, LOCKED 2026-09-01)

The registry is the AI layer's single directory of **what the model is allowed to be asked to
do**. 22 workloads (CW-1..22) + 2 infrastructure entries (EMB-1, OPS-1), derived from PRD §7
journeys, §9 anti-hallucination, and §10 entities by a five-researcher decomposition and
verified by a two-auditor traceability cycle (186 PRD requirements traced, 5 uncovered gaps
found and fixed; corrections log in plan `soft-kindling-pony`). Anything not in this registry
and not on the arithmetic exclusion list (§2.6) is **not an AI capability Caliber has** —
adding one is a registry change (§2.7), not an implementation detail.

Model/shelf assignments are summarized here for one-page readability; `models.md` §3 owns the
fleet and `routing.py` owns the binding. **Every assignment is provisional until its named
gating eval runs (FR-I4)** — the Status field tells the truth per row.

Status legend: `built` (code exists) · `eval owed` (built, FR-I4 not discharged — not done) ·
`partial` · `not built` · `P2` (later product phase).

---

## 2.1 The workload entity

Every registry row answers, unambiguously:

| Field | Meaning |
|---|---|
| Anchor | The product moment (PRD §7 journey stage) that triggers it |
| Does / Never | One-line mandate and its negative space |
| In → Out | What it consumes and produces (structured; schema'd calls are reasoning-fields-first — safety.md §7.2) |
| Shelf / effort | Quality tier per ADR-0009; effort per the discipline in models.md §3.4 |
| Fallbacks | Overrides to the four default classes (§2.5) |
| Gating eval | The named eval that graduates it from provisional (evals.md §5) |
| Slices | Which mandatory eval slices apply: D6 (always), injection, D8, tone |
| Status | Honest build + eval state |

## 2.2 Request-time workloads (CW-1..16)

### CW-1 — Resume/document extraction
Turns extracted resume text into the structured profile schema. **Never fabricates under
schema pressure — emits null rather than guess**; date spans copied verbatim (dedicated
fidelity gate). Vision-model variant is a *fallback for scanned PDFs only*, never the default.
- Anchor: onboarding Path A upload · In: `extraction.py` text → Out: profile schema
- Shelf: S3 (interim vision fallback: S2 native-PDF; vision eval cell pinned at eval design — no call before pinning)
- Fallbacks: C — one clean retry → S2 · **D: NOW** (fleet S3 migration, §9.4)
- Eval: planted-absence fabrication rate + date exact-match + degraded-scan set · Slices: D6, injection
- Status: **built (v2, 2026-09-03), eval owed** — `resume_parse.py`: reasoning-first schema, verbatim `*_raw` copying with code-side date normalisation, substring grounding gate, versioned prompt (`profiler/cw1_resume_parse.v1`), traces as `profiler` with `cw=cw-1`. Design: `docs/AGENT_WORK_DESIGN.md` §1. First local measurement (Qwen3.5-4B, 4 independent samples, 2-role fixture): 0 fabricated fields, second role dropped in 2/4 — recall, not fabrication, is the local failure mode; measuring it is the eval's job

### CW-2 — Guided elicitation dialogue
Phrases the questions that fill genuine profile gaps, both paths (Path B full flow, Path A
post-parse follow-up). **Which fields are missing is arithmetic** (`completeness.py` /
`textquality.py`, already shipped) — the model only words the ask; never invents demands.
- Anchor: onboarding Q&A · In: injected missing-fields list → Out: question phrasing
- Shelf: S3, effort low · Fallbacks: C — depth ≥6 or stall → S2 fresh context
- Eval: scripted personas (invented-demand + coverage) **+ small live-user A/B** (simulated users flatter results) · Slices: D6, injection
- Status: not built (today's onboarding asks are deterministic UI copy)

### CW-3 — Skill extraction & normalization
Maps free-text skills onto the canonical taxonomy by **constrained selection from
retrieval-supplied candidates** — the chosen canon must exist in the candidate set
(validator-enforced, canon-hallucination = 0); writes clarification questions for vague terms.
- Anchor: profile build · In: free-text skill + candidate set → Out: canonical key + clarify question
- Shelf: S3, effort low, retrieve→constrained-select · Fallbacks: C — widened candidates → S2
- Eval: join-key stability ×10 paraphrases; canon-hallucination exactly 0 · Slices: D6
- Status: **built (v2, 2026-09-04), eval owed** — reasoning-first schema (`analysis` → `quote` → `skill` → `confidence` enum), versioned prompt (`profiler/cw3_clarify.v1`), fenced JSON-encoded project text, `cw=cw-3` + prompt hash on every trace, grounded-or-dropped through the shared normaliser. Design: `docs/AGENT_WORK_DESIGN.md` §1. Live on Qwen3.5-4B: 2/2 quotes verbatim when the text names tools; empty list returned on both the implies-nothing and supports-nothing cases. **Constrained selection over a retrieved canon (the row's actual mandate) still needs EMB-1** — until then `skill` is free text checked by code, not a `Literal` the grammar enforces

### CW-4 — Claim–evidence verification + seniority read
Resolves ambiguous prose ("led" vs "participated"), ties claims to **verbatim quotes** that
must survive an exact substring check; applies the bar's education-weight policy (from CW-17
via the `policy.py` `education_weight()` seam). The evidence-strength *rating* is arithmetic.
- Anchor: profile analysis · In: prose + education-weight policy → Out: verdicts + quotes
- Shelf: **two-pass: S2 citations pass → S1 verdict (effort high)** + local MiniCheck-class
  veto on "demonstrated" (pending ratification, ADR-0009). Two-pass is *chosen*, citations +
  structured output = HTTP 400 (recorded alternative: tool-use JSON sans strict format + exact-match gate).
- Fallbacks: C — veto → S1 re-adjudicate fresh context
- Eval: asymmetric cost-matrix gold set (false-"demonstrated" ≫ false-"claimed") + quote survival · Slices: D6
- Status: **partial (2026-09-05) — claim–evidence verification built, eval owed; the
  education-weight half not built.** `claim_check.py` asks one question per (project, skill):
  what do these words show? Reasoning-first schema (`analysis` → `quote` → `verdict` →
  `confidence`), versioned prompt (`profiler/cw4_claim_check.v2`), fenced JSON-encoded project
  text, `cw=cw-4` + prompt hash on every trace, grounded-or-dropped through the shared
  normaliser.
  **Deviation from the shelf, taken knowingly:** the row prescribes two passes (S2 citations →
  S1 verdict) *because* citations × structured output is a 400. This is the row's own recorded
  alternative — structured JSON plus an exact-match gate — chosen because it is the only one of
  the two that runs unchanged on the local runtime, and because it is the shape CW-1/3/5/6
  already use. Revisit when Claude credits return and the citations pass is affordable.
  **The safety property is code, not prompt:** `apply()` returns the weaker of the arithmetic's
  rating and the model's verdict and can never return a stronger one, floored at `mentioned`
  because whether a tool is in a stack list is a dated fact. Tested as a property over the full
  4×4 ladder. The asymmetric cost matrix the eval names is why: a false "demonstrated" is
  unrecoverable, a false "claimed" becomes a probe.
  Live on Qwen3.5-4B (2026-09-05): correctly pulled `led` → `mentioned` on a title-claims-lead
  + "We moved…" project, and on two stack-only tools; held `led` where the prose said "I owned
  the Python ledger service end to end"; ignored an injection planted in the candidate's own
  summary. **v1 was defective and is superseded**: it defined `none` two ways three lines
  apart, and the model obeyed the wrong one — see WORKLOG 2026-09-05.
  The education-weight seam (`policy.education_weight()`) is still a documented placeholder;
  its input is CW-17's per-level policy, which does not exist. Design: `AGENT_WORK_DESIGN.md` §1.

### CW-5 — Fit ranking + honest-leveling narrative
Writes "where you stand for this role" in **both regimes** (selection-time and
post-assessment update), including the **undersell direction**. Must commit to a level —
hedging is its own failure. Calibrated tone: honest, never demoralizing, anti-sycophantic.
- Anchor: role fit & level read-out · Shelf: S1, effort med-high **never max** — conditional:
  Opus 5 has no current sycophancy measurement · **Never Sonnet 5 (9.1% sycophancy)**
- Fallbacks: A — retry/defer (dormant alt Sol requires ratification + D5)
- Eval: 990-case sycophancy run + paired-persona level-invariance, both regimes + undersell · Slices: D6, tone
- Status: **partial (2026-09-04) — built, eval owed.** `role_fit.py` computes the label,
  coverage, the reach read and the direction; `standing.py` narrates a label it is handed and
  cannot disagree with (no label field in its schema). Validators: level and direction echoed
  and checked, each label pinned to its own sentence, `standing` forbidden from naming the
  target level, numbers-verbatim across every prose field including spelled-out numerals.
  Design: `AGENT_WORK_DESIGN.md` §2; contract: `docs/spec/fit-labels-v1.md`.
  **The named sycophancy/level-invariance eval has not run, and on the local 4B the narrative
  is refused intermittently** — 3 of 4 live runs accepted, the fourth rejected for stating a
  gap count it was not given.

### CW-6 — JD decomposition
Breaks a pasted job description into structured requirements for the gap engine. **Recall
first** — a coverage validator maps every sentence (mapped or explicitly discarded).
- Anchor: role targeting · Shelf: S3, effort low · Fallbacks: C — shortfall → S2
- Eval: seeded-JD drop rate (planted buried/compound requirements) · Slices: D6, **injection**
- Status: **partial (2026-09-04) — decomposition built, eval owed, applier not built.**
  `jdsanitize` -> `jdsegment` -> `jd_decompose`: deterministic versioned segmentation, one
  verdict per segment, `sub_skill` a grammar-enforced `Literal` built from the loaded bar
  (canon hallucination structurally impossible — no EMB-1 needed here), quotes verified
  verbatim against their own segment, four-cell coverage scoring. The *applier* is blocked
  on ratifying `docs/spec/jd-overlay-v1.md`. Design: `AGENT_WORK_DESIGN.md` §2.
  Injection slice added 2026-09-04: `safety.md` §7.1 names pasted
  JDs an attacker-controlled surface and this row listed D6 only, while `evals.md` §5.2's
  injection list omitted CW-6 entirely — a contradiction inside the suite. A JD steers what a
  candidate is assessed on. Design: `AGENT_WORK_DESIGN.md` §2.14

### CW-7 — Gap-explanation prose
Narrates precomputed gap numbers in plain language. **All arithmetic upstream; every number
in the prose must appear verbatim in the input** (validator). Never teaches (D8).
- Anchor: readiness dashboard · Shelf: S3 + numbers-verbatim validator, effort low
- Fallbacks: C → S2 · cross-vendor nano-class eval cell (ID pinned at eval design)
- Eval: numeric exact-match + contradiction check · Slices: D6, D8, tone
- Status: not built (S2 slice)

### CW-8 — Assessment-plan construction (+ regeneration)
Builds the topic plan from bar + gaps with traceability links. Regeneration mode
(mid-assessment) never re-litigates passed topics; **regeneration triggers are arithmetic**.
- Anchor: assessment start / mid-assessment · Shelf: S2 med; regen mode S3
- Fallbacks: C — Opus + explicit scope-freeze
- Eval: D8 red-team (teaching-content leakage + scope drift vs bar) · Slices: D6, D8
- Status: not built (S3 slice)

### CW-9 — Open question generation + reference answer + grading notes
Writes open-ended questions grounded in the candidate's journey — **and the reference answer
and grading notes the judge grounds on** (v2's most consequential correction: nobody else
owned those). Reference answers verified by the S4 blind-answer check — a generator's
self-check is not verification.
- Anchor: assessment · Shelf: S1, effort high · Honest gap: no AIG model comparison exists — confidence low-med
- Fallbacks: B — S2 + heavier SME gate (dormant alt Terra: ratification + D5)
- Eval: psychometric pilot (SME validity-at-level → live difficulty/discrimination) · Slices: D6
- Status: not built (S3 slice)

### CW-10 — MCQ + distractors + key
Generates MCQs with plausible distractors and a key **checked by a blind solver that never
sees it** (S4, authoring-time, batchable). Overgenerate-and-rank ×5–10.
- Anchor: assessment · Shelf: S3, effort low · Fallbacks: B — S2 if distractor bar fails
- Eval: distractor stats (choice share, point-biserial) + key-mismatch rate · Slices: D6
- Status: not built (S3 slice)

### CW-11 — Practical/design challenge + harness
Authors practical challenges with reference solution (S1, **xhigh — the coding sweet spot**)
and the scoring harness (S3, in an execution-verify loop): harness must pass the reference
and fail a deliberate mutant — self-verifying.
- Anchor: assessment · Shelf: split S1-xhigh / S3 · Fallbacks: A — retry (dormant alt Sol)
- Eval: harness validity (pass-ref/fail-mutant) — near-free · Slices: D6
- Status: not built (S3 slice)

### CW-12 — Fresh-variant equivalence
Produces an equally difficult fresh variant for retakes/anti-replay — **and ships an
equivalent fresh reference answer**. The registry's biggest unevidenced bet (documented
counter-evidence on parallel-forms claims): ships instrumented with grader anchors, or not at all.
- Anchor: retakes · Shelf: S2, CrossQG-style contrast+filter, effort med; S4 difficulty check (authoring-time)
- Fallbacks: A — S3 + higher filter budget
- Eval: paired-variant IRT difficulty-delta + reference-answer equivalence · Slices: D6
- Status: not built (S3 slice)

### CW-13 — Rubric grading (the judge) — crown jewel
Scores open answers against the rubric, **reasoning first, score second**. The 80%-gate
decision rides on it. Dual metric: expert agreement AND false-pass. Grade-stability SLO at
the gate: <2% verdict flip, via **median-of-3 multi-sampling in the borderline band** around
the ~70 line (xhigh re-samples run in a dedicated lane with their own cache prefix — an
effort change invalidates cache). The harsh-bias offset is a **deterministic layer over
judge output**, re-fitted per model version AND prompt hash.
- Anchor: every graded answer · Shelf: S1 Opus 5, effort **high, PINNED + versioned** (change ⇒ gold-set re-run)
- **Never server-side fallbacks. Never served from cache.**
- Fallbacks: A — within-family with OWN fitted offset, else "grade pending" · B — refusal
  (`stop_details`) → human queue as grade-of-record, S4 commit-first advisory attached ·
  D — anchor-stream judge-verdict freezes gating
- Eval: gold set 45 → ~200 borderline-oversampled: QWK + verdict κ + false-pass +
  persuasion-injected slice + 20-run flip-rate (defines band width) + interview-mode +
  structured-design-artifact slices · Slices: D6, tone
- Confidence: **Hypothesis** (contrarian rule 1); Sonnet-5-workhorse hypothesis in bake-off
- Status: not built — **gated by Phase 0A** (`BACKLOG` GRD2-04); no judge ships before the gold-set gate passes

### CW-14 — Gap guidance + Socratic hint
Turns confirmed gaps into specific actionable guidance and in-flow hints. **Owner of D8:
assess and guide, never teach the answer — enforced by a checker architecture, not model
disposition** (frontier inversion: withholding beats capability).
- Anchor: post-assessment coaching · Shelf: S3, rubric-bound, grounded, behind the D8 checker
- Escalation: D6-high → **S1** (conditional on CW-5 tone eval) — **never Sonnet on tone**
  (audit fix: the prior S2 lane predated S2=Sonnet rebinding; would also have 400'd effort on Haiku)
- Eval: D8-leakage + specificity rubric + perception pilot · Slices: D6, injection, D8, tone
- Status: not built (S4 slice)

### CW-15 — Deeper-probe content
When **arithmetic triggers** a deeper probe mid-assessment, picks from a bounded menu and
writes one probe question. Latency-sensitive; one call.
- Anchor: mid-assessment · Shelf: S3 one-call menu+probe
- Fallbacks: B — S2-low if probe quality fails · D — pre-authored probe bank
- Eval: paired-preference probe quality + P95 latency · Slices: D6, D8
- Status: not built (S3/S4 slice)

### CW-16 — Interviewer dialogue + post-mortem (P2)
30–60-turn mock interview + post-mortem report (scoring → CW-13 slice; reported outcomes →
CW-22). State/persona consistency over that horizon is the hardest published failure mode
for every current model — hence the **external turn-summary ledger** (class-D fallback).
- Shelf: S2-class **bake-off** (Terra vs Gemini 3.7 Flash vs Sonnet-5-low — class-transfer
  until our own 40–60-turn sim); screen: Haiku thinking-off ~150 tok (steering only, never
  the gate); post-mortem: S2 high, batch
- Eval: scripted-candidate simulator — rubric-state consistency + persona probes +
  under-probing rate + TTFT P95 · Slices: D6, injection, D8
- Status: **P2** — do not build ahead of slice

## 2.3 Library-time workloads (CW-17..21) — all human-gated

### CW-17 — Role-bar authoring (PRD §7.3 + D5 + FR-I3 + §9 — the existential-risk artifact)
Drafts per-role/per-level expectation bars from retrieved evidence, **per-criterion citation
required**; reviewers primed to CUT (frontier models over-author). Output carries the
per-level **education-weight policy** consumed by CW-4 (U1 resolved through `policy.py`).
- Shelf: S1, effort high never max · Fallbacks: A — retry (Sol dormant) · B — S2 + stronger SME
- Eval: citation-support rate + scope-drift count + education-weight presence · Slices: D6, D8
- Status: not built (**Phase 2 slice** — corrected 2026-09-04: PRD §12 puts agent-generated role
  expansion in Phase 2 and scopes S2 to the founder-authored seed; BAR-34/35/36 agree. The old
  "§14" citation was loose — §14 is Risks & mitigations, which supplies the risk framing but not
  the authoring mandate. D5 dual-authoring applies; the beachhead bar is never agent-authored)

### CW-18 — Rubric authoring
As CW-17, **plus a rubric-refinement loop against the gold set** — published gains up to
+0.403 QWK from rubric wording alone; rubric text is tuned like code.
- Shelf: S1, effort high · Eval: CW-17 gates + QWK gain per revision · Status: not built (S3 slice)

### CW-19 — Bar drift / versioning refresh
Diff-shaped, human-gated bar updates from market drift + the CW-22 outcome signal. Bounded,
reviewable diffs — never silent rewrites.
- Shelf: S2, effort med · Fallbacks: A — S3 + higher review · Eval: CW-17 citation/scope gates · Status: not built

### CW-20 — Gold-set generation (the FR-I4 meta-workload)
Generates labeled gold answers **including convincing fakes** (persuasion-laced,
Consistency+Identity template stack), every item human-filtered. Fakes must not share a
model family with the judge — family-disjointness cannot be satisfied inside the fleet,
hence the **GPT-5.6 Terra offline exception (ratification pending; alt: S4 Gemini with
familiarity risk)**. Human-primacy inversion noted for non-founder roles.
- Shelf: out-of-fleet, OFFLINE library tool only, human-gated, NO routing.py entry
- Eval: judge false-pass per generator × technique; cells fooling ≥20% become the standing adversarial slice
- Status: not built — **but the gold set itself is Phase 0A's human task** (see §9.2; AI-authored gold sets validate nothing)

### CW-21 — Expert-review assist
Drafts summaries/suggestions for human reviewers; **human primacy — assists, never decides**.
Honestly flagged: the one synthesis-derived row with no Phase-2 research behind it —
ratification item: accept or commission research.
- Shelf: S2, effort med · Fallbacks: B — human queue · Eval: reviewer-acceptance rate · Status: not built

## 2.4 Outcome loop + infrastructure

### CW-22 — Outcome-loop ingestion (P2)
Normalizes candidate-reported real interview questions → maps to bar topics (schema-validated),
feeding CW-19. Async; **batch API (−50%)**; EMB-1 retrieval shortlists, model adjudicates top-k.
- Shelf: S3 batch, effort low · Fallbacks: B — low-confidence → S2 · D — embedding-only + human queue
- Eval: ~200 real reported questions — mapping F1 + schema-invalid rate · Status: **P2**

### EMB-1 — Embedding & re-index pipeline
Local embedding model behind all similarity search (skills ↔ JD ↔ bar topics) in pgvector
(ADR-0004). **A model swap is a migration**: blue/green dual-column re-embed; old and new
vectors never share an index. Incumbent `bge-small-en-v1.5`; challenger
`granite-embedding-small-english-r2` (Apache-2.0, 384-d drop-in); deferred arms recorded
(Qwen3-0.6B offline-index-only; EmbeddingGemma if legal clears).
- Eval: in-domain TalentCLEF-B-style set (~300 queries) — NDCG@10 + recall@50 + CPU P50/P95 · Status: not built (S2 slice, AGT-13/ARC-24)

### OPS-1 — Probe liveness agent
The tiny scheduled call proving the LLM path (credential, provider) is alive before
a user hits it. **Must exercise the production path — a probe that takes a shortcut proves
nothing.** Eval-of-record = the S3 cheap-tier gauntlet (FR-I4: no unnamed gates).
- Shelf: S3 through the production path · Status: **partial** — `POST /api/v1/_probe/llm` exists; scheduling + gauntlet owed

## 2.5 Fallback classes (defaults for every row; rows list only overrides)

| Class | Trigger | Default |
|---|---|---|
| **A** availability | Provider/model unavailable | Within-family retry, then output-pending — **never an uncalibrated result from an unmeasured model** |
| **B** refusal | Model declines (`stop_details`) | Retry-with-repair, then human queue (judge: human queue IS grade-of-record) |
| **C** escalation | Quality shortfall | **Deterministic triggers only** — arithmetic decides, never the model; escalations restart with clean context |
| **D** migration | Model retirement/price event | Named owner + date + rehearsed fallback config, recorded as registry fields |

Price events (Sol Nov 21 · Gemini Flash Jan 1) are cost-modeling items, not migrations.

## 2.6 The arithmetic exclusion list (never a model)

Deterministic code, much of it shipped and regression-tested (275 tests green). The mapping
audit confirmed no registry row leaks any item to a model:

- **Profile understanding:** completeness gate + graded credit units; evidence-strength
  ladder; recency windows; seniority flags; per-skill depth score; consistency cross-checks;
  duplicate collapse; text-quality tiers incl. gibberish detection (`textquality.py`).
- **Assessment math:** gap formula/buckets; JD re-weighting; 80% / ~70-line gate; harsh-bias
  calibration offset (deterministic layer over judge output); rubric sum; topic state
  machine; MCQ/practical auto-grade; readiness score; level computation; adaptive-routing triggers.
- **Integrity:** quote-substring verification; hidden-text/data-injection lint at ingestion
  (PhantomLint-style, pre-model); answer-similarity/replay checks; eval measurement itself.
- **Platform:** routing, caching, paywall; education weight as a `policy.py` value behind
  `education_weight()` until CW-17 supplies role-aware weights.

Standing rule: **escalation, regeneration, probe, and adaptation triggers are always
arithmetic** — a model never decides its own escalation.

## 2.7 Registry change control

Adding a workload or model slot requires, in the same change: workload evidence, the named
gating eval, a migration owner, and an ADR if it moves an architectural boundary. The
checker-of-its-work must be a different model (external-examiner rule, ADR-0009). Registry
edits bump this file's version line and land with a WORKLOG entry.

## 2.8 Standing ops flag

~~Resume-parse and clarify both trace under agent name `"profiler"` today~~ **Closed 2026-09-03 for CW-1:** `agent_call.cw` exists (migration `b7e2c4d1a9f3`) and the resume parse stamps `cw-1` + `prompt_version` + `prompt_hash`. CW-3 followed on 2026-09-04: both workloads now carry their own `cw` tag, `prompt_version` and `prompt_hash`, so their cost and eval attribution are finally separable.