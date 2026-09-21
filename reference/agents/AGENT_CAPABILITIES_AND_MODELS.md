# Caliber agents — capabilities, workload mapping, models (consolidated)

> Built 2026-09-18 from `D:\Caliber` by four parallel read-only extractions:
> the Capability & Model Mapping Report (PDF + `report.html`), the AI Flow Quick Guide (PDF + `flow-guide.html`),
> the research notes `docs/llm/research/p2–p5`, `BACKLOG.md` / `OPEN-WORK.md` / `AGENT_WORK_DESIGN.md` / the UI agent roster,
> and facts (not code) from `api/src/caliber/llm/`.
> **Scope rules:** Claude models only (Caliber's current dev cycle, "Amendment A1" / ADR-0011). Non-Claude models are
> noted only as *deferred*. Provider-gateway/transport material is deliberately excluded.
> Snapshot — the source of truth stays in `D:\Caliber`. Where this file and `RULEBOOK.md` differ for the POC, the rule book wins.

---

## 0. The five governing rules (Mapping report §1)

1. **"Arithmetic owns dated facts; the model owns ambiguity."** (+ "the app owns sequence")
2. **"Models bind to tasks, never to agents."** A model is chosen per *workload* (CW-n), via config.
3. **"No agent ships on vibes" (FR-I4).** Every model assignment is a hypothesis until its named gold-set eval runs.
4. **"The system proposes; the human decides."** No agent silently edits a confirmed profile.
5. **"Small fleet, audited claims."** Hard budget of 4 API models (+ local embedder).

An **agent** is a job title (PRD §10.1). The **unit of design is the workload** (CW-1 … CW-22, EMB-1, OPS-1).
One agent can own several workloads with *different* models (e.g. Profiler: CW-1 on Haiku, CW-4 verdict on Opus).

---

## 1. The Claude fleet (dev cycle, verified 2026-09-02)

| Shelf | Model id | Price in/out $/MTok | Context / max out | Effort | Thinking | temperature/top_p/top_k | Cache min prefix | Retirement floor | Role |
|---|---|---|---|---|---|---|---|---|---|
| **S1 expert** | `claude-opus-5` | 5 / 25 | 1M / 128K | low · medium · **high (default)** · xhigh · max | adaptive, on by default | **400** if sent | **512** | Jul 24 2027 | Judge, high-stakes authoring, tone-bound narrative |
| **S2 worker** | `claude-sonnet-5` | 2 / 10 (permanent) | 1M / 128K | all 5 levels ("medium ≈ Sonnet 4.6 high") | adaptive | **400** | **1024** | Jun 30 2027 | Everyday generation — **never tone-bound work** |
| **S3 cheap** | `claude-haiku-4-5` (dated `claude-haiku-4-5-20251001`) | 1 / 5 | 200K / 64K | **not supported — errors** | `enabled` + `budget_tokens` (old style) | temperature accepted | **4096** | **Oct 15 2026**, no successor | High-volume structured jobs |
| local | `bge-small-en-v1.5` (384-d) | free | — | — | — | — | — | — | EMB-1 embeddings (Anthropic has no embeddings endpoint) |

- **Excluded:** Fable 5 / 5.1 (30-day retention, no ZDR, $10/$50) · Sonnet 4.6 (dominated) · Sonnet 4.5 (retires ~Sep 29 2026, vetoed).
- **Opus 4.8** — not assigned; within-family availability-fallback reference only ("Opus-5-low ≈ Opus-4.8-max").
- **Deferred with the cross-vendor plan:** S4 examiner (Gemini 3.7 Flash), GPT-5.6 alternates, local MiniCheck verifier.

**API facts that shape every agent**
- **Omitting effort = high** on Opus/Sonnet 5 ("'we didn't set effort' is already a high-effort policy"). Effort is the only depth control.
- **Never send effort to Haiku** — the API errors.
- `max` effort is **officially warned against for structured-output tasks** (overthinking). Never max: CW-5, CW-17, the judge.
- Effort data (Opus 5): medium ≈ 94% of peak quality at 29% of the spend; max ≈ xhigh quality at +32% tokens → *"effort, not model choice, is the biggest cost lever."*
- **Every default above medium needs a recorded low/med/high sweep first.**
- Changing effort invalidates the prompt cache → pin effort per workload.
- **Citations + structured output = HTTP 400** → any workload needing both is two-pass.
- Structured outputs are grammar-enforced on every current model → *"model choice affects content quality, not JSON validity"*; measure **value accuracy**, never parse success (schema compliance 97–99% vs value accuracy ≤83%).
- **Caching:** a shared prompt under 4,096 tokens *never* caches on Haiku (`cache_read_input_tokens` stays 0). Reads cost 0.1×.
- **Batch:** −50%; "Sonnet 5 batch ($1/$5) = Haiku live price" → near-free upgrade for batch-eligible work.
- **Haiku → Sonnet fallback is a parameter translation, not a model swap** (Haiku: `budget_tokens`, temperature OK, no effort · Sonnet 5: adaptive + `effort:"low"`, temperature 400). Real cost ≈ 2.5–3.5× per task (price × ~1.3× tokenizer × thinking).
- **Refusals** return `stop_reason: "refusal"` + a category → handle explicitly, route to a human; never silent substitution.

---

## 2. Capability taxonomy

### 2.1 Four capability clusters (Mapping report Part 2)

| Cluster | Workloads | What the evidence says | Consequence |
|---|---|---|---|
| **Extraction & grounding** | CW-1/2/3/4/6/7 | Cheap ≈ frontier on structured extraction (within ~1 pt; a fine-tuned 0.6B matches top tier on resumes). "Model size does not predict structured-output quality." Schema pressure causes fabrication ("structure snowballing"). Retrieval beats generation for skill linking (0.397 vs 0.221). Claude family scores *worse* on grounded faithfulness boards (9.8–10.9% vs 3.1% for a nano rival; Claude 5 unmeasured). | *"Eval-gated, not model-gated — validators and scaffolding buy more than model size."* S3 by default; reasoning fields first; exact-match gates stay |
| **Judging** | CW-13 (+ interview grading) | Opus 4.6 best absolute judge (κ≈0.875, lowest position bias); Opus 5 unmeasured → assignment is a hypothesis. Raw agreement overstates chance-corrected by 33.8–41.3 pp. Judges flip 1–2/7 items even at temp 0. All 14 judges inflated persuasive wrong answers; **CoT amplifies it**. Claude is the harshest family. Ensembles ≈ 2.18 effective votes; a 3-family panel still passed 55% of hacked answers. Commit-first auditing: false-pass 0.719 → 0.012. | One strong judge (Opus 5, high), multi-sample in the borderline band, persuasion slice in the gold set, harshness offset in code, no voting ensembles |
| **Generation** | CW-5, 8–12, 14, 17–19 | Sycophancy (990 cases): **Sonnet 5 9.1% — "worst of the major models"**; Opus 5 excluded ("evidence gap, not negative evidence"). D8 never-teach holds architecturally (leakage 0.05%). Rubric-bound small model beat GPT-4o on feedback. No head-to-head for question generation. 6.4% of one benchmark's answer key was wrong; judges accepted 63% of wrong reference answers → *"generator self-check is not verification."* | Never Sonnet on tone; D8 by schema + checker; blind independent solve for every reference answer/key; Guidance on the cheap shelf |
| **Dialogue, cheap tier, embeddings** | CW-15/16/22, EMB-1, OPS-1 | Multi-turn: −39% over long dialogues, early wrong assumptions never recovered, reasoning tokens don't help; persona drift 20–40% over 10–15 turns. Haiku 4.5 scored 100% (231/231) on a JSON benchmark. TTFT: Haiku ~0.8 s vs Sonnet 5 ~1.3 s. MTEB rank ≠ in-domain rank (ρ 0.225). | Haiku for latency-sensitive steps; external turn-summary ledger for the interviewer; in-domain embedding bake-off |

### 2.2 Eight cross-cutting properties (every agent)

1. **Injection robustness** — prompt injection *and* data injection (forged evidence). 41% of jobseekers admit hidden text; ~1% of real resumes carry injections. Deterministic hidden-text lint at ingestion; fencing ("spotlighting") cuts attack success >50% → <2%.
2. **Structured output** — *"Every schema'd call puts reasoning fields before the score/verdict fields. This ordering is load-bearing."*
3. **RAG grounding** — no near-miss context; for one role's assessment put the **whole bar in context**.
4. **Latency / cost / pass^k** — exact-key caching only for anything graded; **the judge is never served from cache**; no cascade-of-judges.
5. **AI-detection is a weak signal** (12–26% false positives) — may inform, never gate.
6. **D6 level slices** — every gating eval reports junior → principal.
7. **D8 never-teach** — enforced by a checker (owned by Guidance), not by model disposition. D8 slices on CW-7/8/14/15/16.
8. **Calibrated tone** — honest-not-demoralising *and* anti-sycophantic, both directions. Tone slices on CW-5/7/13/14.

### 2.3 Never a model (the arithmetic list)

Completeness gate · evidence-strength ladder · recency windows · seniority flags · depth scores · consistency checks · duplicate collapse · text-quality tiers · **gap formula + buckets** · **JD re-weighting** · **the ~70 pass gate** · harsh-bias offset · rubric sums · **topic state machine** · MCQ/practical auto-grading · **readiness score** · level computation · **adaptation/escalation triggers** · quote-substring checks · hidden-text lint · replay checks · eval measurement · routing, caching, paywall. *"A model never decides its own escalation."*

---

## 3. Agent roster at a glance

| # | PRD agent (code id) | UI label | Workloads (CW) | Code does the… | Model does the… | Caliber slice | Built in Caliber (2026-09-05) |
|---|---|---|---|---|---|---|---|
| 1 | Profiler (`profiler`) | Profiler | CW-1 resume parse · CW-2 elicitation · CW-3 skill normalise · CW-4 claim check | completeness, evidence ladder, recency, dates, grounding | reading prose, resolving ambiguous claims | S1 | CW-1/3/4 built, **evals owed** |
| 2 | Role Analyst (`role_analyst`) | Role analyst | CW-5 standing narrative · CW-6 JD decomposition · (CW-17/19 library, Phase 2) | level from years, fit label, coverage, direction, JD overlay applier | labelling JD segments, saying the standing read | S2 | CW-5/6 built (probe only), evals owed |
| 3 | Gap Analyst (`gap_analyst`) | Gap analyst | CW-7 gap prose | the **whole** gap map | plain-English reasons | S2 | not built (gap map arithmetic built) |
| 4 | Plan Builder (`plan_builder`) | Plan builder | CW-8 plan construct (+ regen) | topic set/order, regen triggers | shaping/explaining topics | S2 | not built (arithmetic plan built) |
| 5 | Question Generator (`question_generator`) | Question writer | CW-9 open Qs + ref answer + grading notes · CW-10 MCQ · CW-11 practical · CW-12 variants (· CW-15 probe) | freshness store, difficulty, triggers | writing items + reference answers | S3 | not built |
| 6 | Evaluator (`evaluator`) | Judge | CW-13 rubric grading | rubric sum, gate, offset, multi-sample, abstention | scoring with reasoning + quotes | S3 (after Phase 0A gate) | not built |
| 7 | Guidance (`guidance`) | Guidance | CW-14 guidance + Socratic hint (· CW-15) | D8 checker | what to learn and why | S4 | not built |
| 8 | Adaptation (`adaptation`) | *(hidden from UI)* | "menu-only; the triggers are arithmetic" (CW-15 / CW-8 regen adjacent) | triggers, menu, applying the choice | choosing from the menu | S4 (ADR-0008: deferred) | not built |
| 9 | Interviewer (—) | reserved | CW-16 (P2) | ledger, scoring via CW-13 | 30–60-turn dialogue | Phase 2 | "do not plan ahead" |

Library-time (human-gated, not candidate-facing): CW-17 role-bar authoring · CW-18 rubric authoring · CW-19 bar drift · CW-20 gold-set fakes · CW-21 expert-review assist · CW-22 outcome ingestion (P2) · EMB-1 embeddings · OPS-1 liveness probe.

---

## 4. Per agent

Format per workload: **model · effort** — why · checker · escalation (class C = deterministic trigger only, restart with a clean context) · eval gate · cost.

### 4.1 [1] Profiler

**Capabilities the model needs** (AGENT_WORK_DESIGN §1.5, hardest first; "Claude" = Haiku 4.5 + structured output):

| # | Capability | Local 4B | Claude | Evidence |
|---|---|---|---|---|
| C1 | Attribute bullets/projects to the right role in a multi-role resume | **struggles** (seen live: project on wrong employer) | mostly passes; still the top content-error class | ExtractBench resumes 18.4% field-pass even on frontier |
| C2 | Emit null instead of a plausible guess under schema pressure | **fails without help** (0.8–26B models fabricated 60–100%) | Haiku 4.5 refused rather than fabricate (0%); **Sonnet fabricated ~90%** | PhantomFill |
| C3 | Copy a verbatim quote that survives an exact substring check | unmeasured; expect worse | ~90% verbatim after normalisation | |
| C4 | Copy names, titles, dates exactly as written | passes when raw-string-shaped | passes | |
| C5 | Recognise role / project / skill boundaries | passes on conventional layouts | passes | |
| C6 | Produce schema-valid JSON | grammar-guaranteed (with fail-open caveats) | guaranteed by constrained decoding | validation stays mandatory |
| C7 | Follow a short positive instruction set | ≤ ~15 rules; collapses by ~80 | same curve, higher ceiling | |

→ C1–C3 are carried by **shape** (schema order, nullable fields, raw-string copying) and **code** (substring gates, cross-field validators), not by prompting. **Dates are copied, never normalised by the model.**

| Workload | Model · effort | Why | Checker / escalation | Eval gate | Cost |
|---|---|---|---|---|---|
| **CW-1** resume → schema | **Haiku 4.5 · none** | cheap ≈ frontier on extraction; Haiku refused to fabricate | date-span fidelity gate (code); C: 1 clean retry → Sonnet 5. Scanned PDFs only: Sonnet 5 native PDF | planted-absence fabrication rate (right answer = null), date exact-match, degraded-scan set, **injection slice**; ≥40 synthetic CVs | ~$0.01/candidate |
| **CW-2** elicitation (wording the asks) | **Haiku 4.5 · none** | missing fields are **computed**; model only phrases. All models under-clarify; reasoning models over-ask | C: dialogue depth ≥6 or stall → Sonnet 5, fresh context | scripted personas: invented-demand rate + coverage; small live A/B | $0.02–0.05 |
| **CW-3** skill normalise | **Haiku 4.5 · none**, retrieve → constrained-select | "frontier spend here buys nothing measurable" | validator: canon ∈ candidates (hallucinated canon = 0); C: widened candidates → Sonnet 5 | join-key stability ×10 paraphrases | <$0.01 |
| **CW-4** claim–evidence verdict | **Opus 5 · high** for the verdict (+ Sonnet 5 citations pass → two-pass because citations × structured = 400) | hardest Profiler task; a false "demonstrated" is unrecoverable | verbatim substring check in code; **demote-only**; every "demonstrated" re-adjudicated by Opus on fresh context while the local verifier is deferred | asymmetric cost-matrix gold set; quote survival | $0.05–0.15 (dominant) |

- **Resources:** hidden-text ingestion lint (deterministic, pre-model) — *"never send the model a document that failed the lint unannounced"*; local OCR only for scans; synthetic-CV generator (seed = ground truth); EMB-1 + a skill canon seeded from the bar's sub-skill keys/aliases (CW-3).
- **Must not have:** web search / URL fetch (completes the lethal trifecta), Agent Skills, memory tool.
- **Known defect class (D10):** a *real* quote about something else (Terraform rated "demonstrated" on "I ran the schema migrations") — substring checks prove a quote is real, not that it is **about** the skill.
- **Caliber decisions:** "one agent, three workloads"; re-parse merges, never replaces; a confirmed profile is frozen.

### 4.2 [2] Role Analyst

**Capabilities** (AGENT_WORK_DESIGN §2.5):

| # | Task | Local 4B | Evidence |
|---|---|---|---|
| 1 | Decide whether one JD segment states a requirement | should pass | bounded per-segment labelling |
| 2 | Pick the right sub-skill from ~23 options | should pass | grammar enum → canon error impossible |
| 3 | Copy a verbatim span | passes | shipped behaviour |
| 4 | Exhaustively enumerate a whole document | **fails** (GPT-4o 19%, Llama-8B 0% exact-set) | hence per-segment, never "list the requirements" |
| 5 | Hold recall as schema complexity rises | **degrades** (0.428 → 0.193) | one flat schema per chunk |
| 6 | Commit to a seniority level honestly | **not trustworthy** (human–GPT-4 κ 0.02–0.23 vs human–human 0.79) | level is arithmetic; model only narrates |
| 7 | Resist flattery while doing 6 | unmeasured | Sonnet 5 barred; Opus 5 conditional |

| Workload | Model · effort | Why | Checker / escalation | Eval gate | Cost |
|---|---|---|---|---|---|
| **CW-5** "where you stand" narrative | **Opus 5 · medium–high, never max** — *conditional* on the sycophancy eval | must commit to a level ("hedging is its own failure"), anti-sycophantic both ways incl. **undersell**; **never Sonnet 5** (9.1%); Opus 5 flagged *overconfident* | numbers-verbatim, level/direction echo, label pinned per sentence; human review until the eval passes; A: retry/defer | 990-case sycophancy run + paired-persona level invariance + undersell + **overconfidence slice**; tone + D8 slices. **Claude only — a local run is not evidence** | $0.05–0.15 ("do not economize here") |
| **CW-6** JD decomposition | **Haiku 4.5 · none** + coverage validator | recall-first extraction; sub-skill enum built from the loaded bar | every segment mapped or discarded (four-cell scoring: recall and discard-precision reported separately); C: shortfall → Sonnet 5 | seeded JDs with buried/compound requirements: drop rate, ≥0.80 cluster recall; **injection slice** | ~$0.01/JD |
| CW-17/18 bar & rubric authoring *(Phase 2)* | Opus 5 · high, never max; human-gated | over-authoring risk → reviewers primed to **cut** | per-criterion citations (two-pass); sign-off bound to content hash; **beachhead bar never agent-authored** | citation-support rate + scope drift | $1–3/job |
| CW-19 bar drift *(Phase 2)* | Sonnet 5 · medium; human-gated | diff-shaped updates | human | as CW-17 | — |

- **Model never emits a number**: JD emphasis is an ordinal (`leading / required / mentioned`); config maps it to a multiplier. CW-6 never sees the candidate.
- **Resources:** the role bar is the whole context. JD-from-URL is **not now**; later only as an allow-listed app-layer fetch the candidate confirms — **never a model web tool**. Web search/fetch belongs only to library-time CW-17/19.

### 4.3 [3] Gap Analyst

| Workload | Model · effort | Why | Checker / escalation | Eval gate | Cost |
|---|---|---|---|---|---|
| **CW-7** gap-explanation prose | **Haiku 4.5 · none** | models collapse on *computing* numbers but can restate given ones; all arithmetic is upstream | **numbers-verbatim validator** (every number in the prose appears in the input, incl. spelled-out); C: fail → Sonnet 5 | numeric exact-match + contradiction check vs the gap JSON; tone + D8 slices | $0.01–0.03 |

- The gap map itself (gap size, priority, bucket) is code. A deterministic **reason template per (bucket, gap size)** ships first and never disappears; the agent may only enrich it.
- Resources: precomputed gap JSON; no tools, no web.

### 4.4 [4] Plan Builder

| Workload | Model · effort | Why | Checker / escalation | Eval gate | Cost |
|---|---|---|---|---|---|
| **CW-8** plan construction | **Sonnet 5 · medium** | "frontier not indicated"; frontier models expand scope. D8 holds by architecture (leakage 0.05%) | D8 by schema + checker; C: escalation → Opus 5 **with explicit scope-freeze** | D8 red-team: teaching-content leakage + scope drift vs the bar | $0.05–0.10 |
| CW-8 regeneration | **Haiku 4.5 · none** | cheap, bounded; **regen triggers are arithmetic**; never re-litigates passed topics | as above | | ~$0.01 |

- Backlog: every topic needs a rationale + `source_refs` (GRD-28 "no black box"); plan-builder gold set ≥20 cases, ≥2 roles, ≥2 levels.

### 4.5 [5] Question Generator

| Workload | Model · effort | Why | Checker / escalation | Eval gate | Cost |
|---|---|---|---|---|---|
| **CW-9** journey-grounded open questions **+ reference answer + grading notes** | **Opus 5 · high** | stakes; no head-to-head evidence exists (confidence low–med, capped "provisional") | reference answer verified by **Sonnet 5 blind-solve, commit-first** (answers before seeing the key) + human SME gate; B: Sonnet 5 + heavier SME gate | psychometric pilot: SME validity-at-level → live difficulty/discrimination | $0.15–0.40/assessment |
| **CW-10** MCQ + distractors + key | **Haiku 4.5 · none**, overgenerate ×5–10 and rank | pipeline > model; the key is the risk | **Opus 5-low blind key solve** (mismatch → reject); B: Sonnet 5 if distractors fail. Temperature diversity works **only on Haiku** | distractor choice share + point-biserial; key-mismatch rate | — |
| **CW-11** practical / design challenge | statement + reference solution **Opus 5 · xhigh** (coding sweet spot); harness **Haiku 4.5** in an execution-verify loop | self-verifying harness | harness must **pass the reference and fail a mutant** | harness validity | $0.50–2.00/challenge |
| **CW-12** fresh variant + equivalent reference answer | **Sonnet 5 · medium**, contrast-and-filter pipeline | "architecture > model"; parallel-forms evidence is weak → provisional | **Opus 5-low difficulty check**; A: Haiku + bigger filter budget | paired-variant IRT difficulty delta + reference-answer equivalence | $0.02–0.05 |
| **CW-15** mid-assessment deeper probe | **Haiku 4.5 · thinking off**, one call: menu choice + probe | latency (~1 s); trigger is arithmetic | B: Sonnet 5-low if probe quality fails; D: pre-authored probe bank | paired-preference probe quality + P95 latency; D8 slice | — |

- 7-question probe set per topic (know it · how it works · why · implemented · challenges · scenario · from your own project). Exit criterion: two consecutive attempts never return the same variant.

### 4.6 [6] Evaluator / Judge

| Workload | Model · effort | Why | Checker / escalation | Eval gate | Cost |
|---|---|---|---|---|---|
| **CW-13** rubric grading (5 × 0–20, gate ~70) | **Opus 5 · high, pinned + versioned, never max**; adaptive thinking on; **multi-sample in the borderline band** (median-of-3 locked; mean-of-k k≥3/prefer 5 is an eval arm); sweep effort **down** (medium arm) | best-evidence judge family; assignment is a *hypothesis* until the gold set says otherwise. Sonnet 5 "workhorse" is a live bake-off (wins only with QWK parity; factor its +30% tokenizer) | **no server-side fallbacks, ever**; never cached; within-family fallback only with its own fitted offset, else "grade pending"; refusal → human queue as grade-of-record; abstain + human review inside the borderline band after resampling; weekly Sonnet 5 fixed-set regrade (weak canary) + anchors + **human transcript review as primary audit** | gold set 45 → ~200 (≥90–100 human-labelled fails near the cut; 2–3 raters, κ ≥ 0.6): QWK per dimension + verdict κ + false-pass/false-fail + **persuasion slice** + 20-run flip rate (<2% SLO) + interview + design-artifact slices. **Phase 0A gate: ≥85% agreement AND zero false-pass AND zero rank inversions** | ~$0.055/judgment; $55–83 per 1k answers all-Opus ($30–40 if the Sonnet workhorse wins) |

- **Haiku never grades** — except an interview-mode ~150-token *screen* used only for steering, never the gate.
- **Integrity stack:** log served model + usage + stop details every call · harshness offset (~11 pts) is a deterministic layer re-fitted per model version **and** prompt hash · answer fenced as inert data + authority-marker flagging + permanent injection regression suite (rubric-aligned injections succeed 0.73–0.82) · reasoning before score (free-text critique then extraction is an eval arm) · ~200 anchors interleaved with an e-process drift monitor · no voting ensembles.

### 4.7 [7] Guidance

| Workload | Model · effort | Why | Checker / escalation | Eval gate | Cost |
|---|---|---|---|---|---|
| **CW-14** gap guidance + Socratic hint | **Haiku 4.5 · none**, rubric-bound, grounded in the specific gap, behind the **D8 checker**; **senior (D6-high) → Opus 5** (conditional on the CW-5 tone eval) — **never Sonnet on tone** | "frontier capability does not buy better formative feedback; rubric-binding, grounding, and withholding discipline do" (8B rubric-bound beat GPT-4o). *"The premium workload in this CW is the checker, not the generator."* | D8 checker rejects step-by-step instruction, code blocks, over-long mechanism explanations | D8 leakage rate + specificity (generic-phrase rate, gap-reference rate, actionability) + perception pilot; tone slice | — |

- Works only from the saved Grade (never sees the Evaluator's prompt). May name the *kind* of resource; never a lesson.

### 4.8 [8] Adaptation

- **ADR-0008 / Mapping report:** *"The Adaptation agent is deferred. … when it comes, it will suggest from a menu and the app will decide. Its adaptive triggers are already arithmetic."*
- No model is assigned in Caliber. Closest workloads: CW-15 (Haiku, menu + probe) and CW-8 regeneration (Haiku).
- Hidden from the UI roster ("a candidate should never see it work").
- Backlog: PLN-28 (S4) adaptation + plan regeneration job; PLN-07 regeneration policy (triggers, re-confirmation, denominator rule).

### 4.9 [9] Interviewer (Phase 2 — do not build)

- CW-16: 30–60-turn dialogue — *"the hardest published failure mode for every current model."* Mid shelf, not frontier ("size-vs-drift evidence argues against it"): **Sonnet 5 · low** under Claude-only; post-mortem Sonnet 5 · high (batch); **external turn-summary ledger** re-injected each turn; Haiku screen for in-conversation steering; the real grade is CW-13, async.
- **EU AI Act Art. 5(1)(f):** no inferring affect from face/voice/video.

---

## 5. Cross-cutting rules

**Standing model rules**
- Hard budget: 4 API models; every extra model is a standing eval/prompt/migration tax.
- **Runway rule:** nothing durable on a model with < ~9 months guaranteed runway without a named migration owner + rehearsed fallback (Haiku 4.5: Oct 15 2026 bake-off obligation).
- **External-examiner rule:** the checker of a model's work is a different model (within family under Claude-only: Sonnet checks Opus's reference answers; Opus-low checks MCQ keys and variant difficulty).
- **Never Sonnet 5 on tone-bound work** (CW-5, CW-14 escalation).
- **Never effort on Haiku.**
- **Escalations restart clean** — forwarding a failed chain measurably poisons the stronger model (up to −34.8 pts).
- *"A grade from an unmeasured model is worse than a late grade."*

**Resources and the lethal trifecta** (p5_agent_resources)
- **No runtime agent gets tools, Agent Skills, memory, or internet** — every capability is a single schema'd call ("None — DECIDED").
- Runtime agents already hold private data + untrusted content; adding a channel out (web) completes the **lethal trifecta** and turns hidden-text injection into exfiltration.
- **Five-question test** for any new resource: Q1 does it move dated facts/numbers to the model? · Q2 does PII leave the vendor boundary? · Q3 does it add an attacker-controlled input? · Q4 does it break the offline `fake` path? · Q5 is it registered (workload row or ADR)?
- Internet has exactly two legitimate homes: an allow-listed app-layer ATS fetch (later), and library-time CW-17/19.

**Structured output design** — reasoning first · null over guess · evidence before label · validators: canon ∈ candidates, exact-substring quotes, numbers verbatim, JD coverage, date spans exact.

**Cost envelope** — candidate journey CW-1..7 ≈ **$0.10–0.25** (dominated by the CW-4 Opus verdict) · grading **$55–83 / 1k answers** · assessment authoring **$0.50–2.50** · library authoring $1–3/job.

**Calendar** — ~Sep 29 2026 Sonnet 4.5 retires · **before Oct 15 2026** S3 (Haiku) migration bake-off (fallback: Sonnet 5-low via parameter translation).

---

## 6. How Caliber's code actually routes today (facts, `api/src/caliber/llm/`)

| Agent | Tier | Default model | max_tokens |
|---|---|---|---|
| `probe` | cheap | `claude-haiku-4-5` | 1024 |
| `profiler`, `role_analyst`, `gap_analyst`, `plan_builder`, `question_generator`, `guidance` | generator | `claude-sonnet-5` | 4096 |
| `evaluator` | grader | `claude-opus-5`, effort `high` | 8192 |
| `adaptation` | cheap | `claude-haiku-4-5` | 1024 |

- **Known mismatch:** binding is **per agent**, not per workload — so CW-1/3/4 all run on Sonnet (registry says Haiku for CW-1/3, Opus for CW-4) and **CW-5 runs on Sonnet 5, the model the registry bars**. The fix Caliber itself names is a `cw → shelf` map.
- Prices: Opus 5 $5/$25 · Sonnet 5 $2/$10 · Haiku 4.5 $1/$5; an unknown model logs `unknown_model_for_pricing` and costs $0 — "a costing hole", never silent. Cost is computed from the **served** model id.
- Trace per call (`agent_call`): agent · provider · model · effort · served_from · outcome · request_hash · prompt · context · response · error · tokens in/out · cost · latency · **cw** · **prompt_version** · **prompt_hash**. `stop_reason` is captured but **not** traced or checked (a refusal/truncation looks like a schema failure and burns the retry).
- **Repair policy:** exactly **one** corrective retry ("One, not a loop"), feeding back the validation complaint with the rejected value **redacted** (untrusted text must not escape its fence). Second failure raises.
- **Cache:** exact-match only, key = agent + provider + model + prompt + system + effort + json_schema + cw; 24 h; **`evaluator` never cached**; stores only after a successful call.
- Prompts: versioned files `prompts/<agent>/<cwN_name>.vN.md`, hash = sha256 of the exact text; a change is a new file.

---

## 7. What this means for the POC (proposed — confirm per step)

The POC binds models **per workload through each `AgentSpec`** (already true: every spec names its own model), which avoids Caliber's per-agent mismatch.

| POC step | Workload(s) we implement | Model · effort (Caliber dev-cycle mapping) | POC note |
|---|---|---|---|
| [1] Profiler | CW-1 + a CW-4-style verdict, **in one call** | Haiku 4.5 · none | **Deviation:** Caliber puts the CW-4 verdict on **Opus 5 · high** (two-pass). Our code-side cap + weaker-wins compensates; an optional Opus verdict pass is an open decision |
| [2] Role Analyst | CW-5 narrative (+ CW-6 if a JD is given) | CW-5 **Opus 5 · medium** (never Sonnet, never max) · CW-6 Haiku · none | label/level/direction computed in code and handed in |
| [3] Gap Analyst | CW-7 | Haiku 4.5 · none | numbers-verbatim validator; template reasons first |
| [4] Plan Builder | CW-8 | **Sonnet 5 · medium** | topic set fixed by code; D8 checker |
| [5] Question Generator | CW-9 (+ CW-12 for retries) | CW-9 **Opus 5 · high** · CW-12 **Sonnet 5 · medium** | reference answer + grading notes included; blind-solve check optional |
| [6] Evaluator | CW-13 | **Opus 5 · high, pinned**, never cached, no fallback model | median-of-3 in the borderline band; harshness offset 0 for now |
| [7] Guidance | CW-14 | Haiku 4.5 · none (senior+ → Opus 5 · medium) | D8 checker in code |
| [8] Adaptation | menu choice (CW-15-like) | Haiku 4.5 · none | app builds the menu and decides |

**SDK translation:** `model=` from `app/config.py`; `effort=` only for Opus/Sonnet (our `AgentSpec` already refuses effort on Haiku and refuses `max`); no `fallback_model` on the Evaluator; `tools=[]`, no web tools anywhere (lethal trifecta); thinking settings are past the SDK learning boundary — leave the model defaults.
