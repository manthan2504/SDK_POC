# Caliber's sequential plan — stages, gates, pipeline rules, lessons

> Extracted 2026-09-18 from `D:\Caliber\docs\BACKLOG.md` (copied here as `BACKLOG.md`), `WORKLOG.md` (Part 0, Part 10
> and the sequencing sections) and `docs/llm/roadmap.md` (cleaned copy in `../llm/roadmap.md`). Provider-gateway
> material excluded. "B:n" = BACKLOG line, "W:n" = WORKLOG line (approximate). The last section translates it for the POC.

---

## 1. The stage / slice sequence (13 stages, 224 items; `!` = critical path)

| Stage | Goal | Exit gate (quoted, shortened only with …) | Activates |
|---|---|---|---|
| **P0 re-establish** | Turn the PRD's "S0 done / Phase 0 passed" claims back into files — or say honestly what is lost | "Every artifact §12 names has a recorded status. If any Phase 0 gold-set file is unrecoverable, the … row is downgraded to provisional … and the re-authoring cost … is entered as a scheduled item, not absorbed silently." (B:19). *Reality:* nothing recovered → rebuild; Phase 0 "reverts to un-passed" (W:14-22) | — |
| **P1 decisions & specs** (parallel with P0) | Settle every contradiction before code | "No open contradiction remains that two slices could resolve differently. Specifically: exactly one operational pass threshold on one named scale; exactly one topic-state enum with a full transition matrix; a written definition of 100% completeness …; a readiness formula whose denominator behaviour under plan regeneration is stated; and gate-charters for S1-S5 written before S1 starts." (B:34) | specs: GRD2-05 gate, ONB-02 completeness, ONB-03 state machine, BAR-01/02, PLN-04 topic states, PLN-07 regeneration, PRG-01 readiness, PRG-04 next action, PRG-06 recompute triggers, AGT-10 eval contract |
| **P2 humans & brand** | Line up the people gates need | "Two named candidates per gate … an independence rule … If no second senior is available … recorded as an S2 schedule risk with a stated fallback … rather than discovered at S2." (B:83) | — |
| **Phase 0A grader re-baseline — HARD GATE** | Prove the judge before anything uses it | "**≥85% verdict agreement AND zero false-pass AND zero rank inversions** on gold_set_v2, reproduced on a pinned model. Below that … an explicit no-go for wiring the grader live and **S3 does not start**. The passing run is committed as the frozen CI baseline." (B:99). Needs a slice of S0 first: provider client, runtime, prompt registry, eval harness | CW-13 baseline, harness, human gold set |
| **Phase 0B residuals** (parallel S1–S4, gates S5) | Close the ~11-pt harsh bias; independent holdout | Bias inside tolerance with agreement ≥85% and zero false-pass, plus an independent holdout ≥20 answers. "A calibration layer defaulting to identity must exist before S3." (B:119) | — |
| **S0 platform spine** | Provider → trace → cache → routing | Cold start by someone who didn't build it; every PRD enum defined once. Demo: "one traced request shows a span per agent step with provider, model, tokens and latency" (B:131). **AGT-05 orchestrator stage graph + failure semantics** (B:146) | — |
| **S1 onboarding + confirm** | Capture → completeness gate → confirm | "confirm refused at 99% and accepted at 100%, server-side as well as in the UI; both paths green end-to-end … with the parse stubbed; the §7.1 confirmation string byte-exact …; **S2 does not start on a fail**." (B:157). !ONB-16 confirm gate = single source of truth | Profiler (CW-1, CW-3 clarify) |
| **S2 role bar + plan** | Bar → gaps → plan (free tier ends) | "beachhead bar v1.0 is live with two recorded sign-offs …; **no topic can exist with an empty why-it's-here or unresolvable source_refs**; the paywall sits exactly at the end of the plan preview; the gap-analyst gold set clears its bar and **a deliberately degraded engine fails it** …" (B:202). !PLN-13 plan orchestration with retry, cache, model tiering | Role Analyst, Gap Analyst, Plan Builder (CW-3/4/5/6/7) |
| **S3 probe + grade** | Questions + judge | Entry: Phase 0A passed and the threshold + aggregation rule in config. Exit: "grader gold-set regression suite green …; **the verdict threshold in code equals the number in the decision record** (no-literals test); **two consecutive attempts on one topic never return the same variant**; **an answer with a blank reasoning field is rejected before any tokens are spent**; cost per graded topic recorded." (B:258) | Question Generator, Evaluator (CW-8–12, 13) |
| **S4 guidance + reassessment ("crown jewel loop")** | Gap → guide → fresh variant → pass | "guidance containing step-by-step instruction, a code block, or an over-cap mechanism explanation is rejected …; **the Appendix E exemplar passes unchanged**; every gap-open topic has retrievable guidance including skip-origin gaps; **a skipped topic still renders as an open gap after skip, session end and re-login**; the variant-freshness query returns zero repeats." (B:294) | Guidance, Adaptation (CW-14/15) |
| **S5 dashboard + honest leveling + first real user** | Readiness | "**the readiness score never decreases across a pass-only sequence with a fixed plan and bar version**; no 0-100 number renders while the numeric-score flag is false; …" (B:324) | no new workloads |
| Cross-cutting guardrails | Each armed by a named slice | "Each gate demonstrably bites once — a deliberate violation fixture fails it" (B:363) | — |
| Phase 2 / 3 | New roles, interviewer, outcome loop / library rollout | "no role reaches live without a passing per-role eval artifact and a named expert sign-off record" (B:385) | Interviewer, CW-22, Adaptation v2 |

---

## 2. Dependency rules

- **"Nothing here is built ahead of its slice."** The backlog is the master sequence (R:10-13). "Do not start S2–S5 tables or UI … a schema for a judgement that does not exist yet is a table nobody can fill." (W:551)
- **Gate chain:** each slice's exit gate blocks the next · Phase 0A blocks S3 · Phase 0B gates S5's numeric score · the identity calibration layer must exist before S3.
- **AI-layer build order — "harness before agents"** (R:21-32): credentials → provider spine + trace fields → **eval harness + cheap-tier gauntlet (≥100 runs/model)** → **human gold set 45 → ~200** ("cannot be delegated to AI") → judge re-baseline (Phase 0A) → effort sweeps + identity calibration → Haiku migration bake-off (before Oct 15).
- **Done rule** (R:17): a workload is done only when built behind the provider seam **and** its named gating eval ran on the pinned model with results committed. "`built, eval owed` is not done."
- Human dependencies: the gold set, the second senior for the bar (D5), an independent holdout grader. "An AI-authored, AI-graded gold set validates nothing." (W:21)
- Known graph defects (W:171-179): some items depend on later slices (e.g. S4's demo needs S5's readiness recompute → pull readiness into S4 or narrow the demo).
- Scale warning: 404–648 engineer-days vs the PRD's 10–15 (27–65×) — re-baseline or cut scope (W:153-169).

---

## 3. Orchestration and pipeline — what Caliber planned and learned

| Item | What | Slice | State |
|---|---|---|---|
| AGT-05 | Orchestrator **stage graph + failure semantics** (`agent_run` / `agent_stage` tables) | S0 | Not built; `runtime.py` covers run + cache + trace |
| AGT-04 | Runtime with schema-validated I/O + repair policy | 0A | Built: "**exactly one retry, feeding the validator's own complaint back. Not a loop**" (W:1689) |
| AGT-06 | Prompt registry, `prompt_version` + `prompt_hash` per call | 0A | Built (versioned files) |
| job_run | "Postgres is the system of record for jobs; Redis is transport only" — statuses queued / running / succeeded / failed / cancelled + attempts | S0 | Table built, no worker yet |
| ONB-19 | LLM parse as an **async job + status endpoint** | S1 | Not built — named twice as "the proper fix" |
| PLN-13 | Plan generation service: retry, cache key, model tiering | S2 | — |
| PLN-24 | Guidance service "with **idempotency** and an **explicit failure state**" | S4 | — |
| GRD2-22 | Grader failure, timeout, **degraded mode** (retry queue + degraded UI) | S3 | — |
| GRD2-29 | Reassessment loop with `attempt_policy.yaml` + attempt history | S4 | — |
| PRG-06 / PRG-13 | Recompute-trigger matrix ("trigger → what recomputes") and its orchestrator | P1 / S5 | — |
| PLN-28 | Adaptation agent + plan regeneration job | S4 | **Conflict:** roadmap defers the agent to Phase 2, menu-only |
| GRD-15 | Nightly role-agnostic run of the **whole pipeline** on a second-role fixture with no code branch | S4 | — |

**How the app sequences agents (WORKLOG):**
- App-governed orchestration: the app, never a model, owns sequence (ADR-0008).
- **The confirmed profile is the per-user checkpoint** — "the single source of truth for every downstream stage". A content fingerprint freezes it; editing un-confirms it; "a policy change alone must NEVER invalidate a confirmation".
- **Split long steps into committed phases** (ADR-0014): commit the input first (upload + extraction), run the model as a separate, cheaply retryable step.
- **Re-runs must be idempotent without destroying human input:** "clear what you own" erased user fields → replaced by **merge-not-replace** ("absence is never deletion").
- UI shows agent phases from **real requests, never timers**; a `stood-down` state = "could not take its turn, nothing lost".

---

## 4. Topic loop rules — decided vs open

| Topic | Decided | Open |
|---|---|---|
| Pass thresholds | **Two constants, not one** (W:30-49): per-answer verdict line ≈ **70** on 5 × 0–20 (bias-compensated: "70 + 11 ≈ 81 ≈ 80"); per-topic threshold **80%**, "unaffected by (a)" | **DEC-3** how answers combine into a topic verdict · **DEC-3c** how many of the 7 probes are graded (Appendix E generates 7, grades only the scenario probe; grading all 7 ≈ 7 premium calls/topic) |
| Judge aggregation | median-of-3 locked in the borderline band | mean-of-k (k≥5) is an eval arm — "the eval decides, the lock stands until it does" |
| Topic states | one enum with a full 5×5 transition matrix (PLN-04) is required | the state names and matrix are not yet written |
| Skip | "a skipped topic still renders as an open gap after skip, session end and re-login"; skip-origin gaps still get guidance | — |
| Reassessment | fresh variant every attempt ("two consecutive attempts never return the same variant"); hint use recorded on the attempt | attempt-policy numbers (max attempts, cool-down) |
| Readiness | **monotonic: never decreases across a pass-only sequence** with fixed plan + bar version; display gated until the harsh-bias residual closes | the formula, credit table, denominator under plan regeneration (PRG-01) |
| Next best action | exactly one `NextAction(verb, target_id, reason, is_terminal)` | the ordered rule set (PRG-04) |
| Adaptation / regeneration | triggers are arithmetic; bar-version bumps never downgrade retroactively; editing a confirmed profile invalidates it | the trigger list (PLN-07, PRG-06); agent in S4 vs Phase 2 |
| Chain | gap → topic → guidance links enforced (PLN-10); depth 4 earned only by a passed probe | — |

---

## 5. End-to-end acceptance tests

- **Appendix E loop test (PLN-31, S4)** with stubbed agent responses: "a buzzword-heavy RAG answer scores **21** and produces guidance naming the retrieval-vs-generation failure separation with no lesson body, the candidate re-attempts on a **fresh variant**, scores **86**, and the topic flips to passed with **readiness recomputed** and the **next topic unlocked**." The S4 gate requires it to pass unchanged.
- S1: confirm refused at 99%, accepted at 100%; the confirmation sentence byte-exact.
- S2: "Swapping the role-bar record changes the plan with no code change."
- S3: open a topic → see what it probes and why → 7 journey-grounded probes → 5 dimension scores + gaps + evidence quotes.
- Phase 0A: one command runs the gold set blind and prints agreement, false-pass count, faker catch, rank separation, bias — stamped with model and prompt hash.
- S0 "first green": a real call traced with `served_from=provider`, `cost>0`; an immediate repeat is a cache hit with cost 0.

---

## 6. Traps that affect sequencing (learned the hard way)

1. **Long model calls must be async jobs** — a 30 s proxy timeout returned 500 while the backend kept working (30–78 s local parses).
2. **The trace must survive the request.** A dying request rolled back both the parsed rows and the trace row, while the cache had already stored the reply; the retry then showed a 0 s cache hit that hid the loss. Rule: "the trace row for a completed model call must not depend on the request's transaction surviving" (write it in its own transaction / savepoint).
3. **Cache hazards:** key must include the provider (a fake reply was once served as billed); the cache stored replies that later failed validation (pins a refusal forever — cache *after* validation); a retry must change the prompt so the failed answer isn't replayed; never semantically cache grades.
4. **Retryable ⇒ merge, never delete on absence.**
5. **Capture `stop_reason`** — otherwise a truncation looks like a schema failure and burns the single repair retry.
6. **Durable state lives in the database**, not the queue/cache.
7. **No sampling parameters** on Opus/Sonnet 5 — stability comes from rubric anchoring, reasoning-first schemas, structured output, and a verdict-flip-rate probe (≤ 0.02).
8. **Gates catch invention, not omission**: "blind to omission, and blind to a true statement attached to the wrong subject." Only evals close this.
9. **Structure beats instruction:** remove a field rather than tell the model not to fill it; contradictory rules produce confident wrong answers; a helper's permissive default becomes a bug once it's used as a gate.
10. "A bug that repairs itself on the next request cannot be caught by looking at the next request."

---

## 7. Open decisions that touch sequencing

DEC-1 human gold set (start early) · DEC-2 second senior for the bar · **DEC-3 topic aggregation** · DEC-3b scope of "user-facing numeric score" · **DEC-3c probes graded per topic** · DEC-4 independent holdout · schedule re-baseline · R5 whole bar in context vs retrieval · R6 eval harness base (Inspect AI vs hand-rolled) · JD adjusts weights only vs depth (ratification) · **Adaptation timing (S4 vs Phase 2)**.

---

## 8. What this means for the POC (proposed — confirm per step)

| Caliber rule / lesson | POC translation |
|---|---|
| Harness before agents; `built, eval owed` is not done | Each agent step ends with offline tests; a small eval (Step 11) before calling an agent "done" |
| Confirmed profile = fingerprinted checkpoint | Step 3: `PipelineRun` stores a sha256 of the confirmed profile; downstream steps refuse to run unless confirmed; an edit un-confirms |
| Commit inputs before the model call; trace survives failure | Step 3 runner: write the `StepRun` row (status `running`) **before** calling the agent, update it after, in its own transaction; failures are recorded, not lost |
| `job_run` statuses + attempts | `StepRun.status ∈ queued / running / succeeded / failed` + `attempts` |
| One repair retry, redacted complaint, changed prompt | Our runner's retry (PRD: up to 2) feeds the validator's complaint back without echoing untrusted values |
| Capture `stop_reason` | Already in `CallMeta` |
| Merge-not-replace on re-runs | Profiler re-runs with answers produce a new draft; the app merges, never deletes candidate-typed fields |
| Two constants (≈70 per answer, 80% per topic) + DEC-3/3c open | POC: grade the scenario probe only (Appendix E); topic passes when that answer ≥ 70 (RULEBOOK §14). Record the per-topic 80% as not used |
| Readiness monotonic across passes | Step 10: a property test — readiness never decreases across a pass-only sequence |
| Skip stays an open gap | Step 10: a test that a skipped topic stays open and counts as a gap |
| Fresh variant every attempt | Step 7: a test that two consecutive questions for one topic differ |
| Blank reasoning rejected before tokens are spent | Evaluator input check before calling the model |
| Appendix E loop is the acceptance test | Step 12: run the full loop offline with a fake `query` (21 → guidance → fresh variant → 86 → pass → readiness up → next topic) |
| Adaptation: menu-only, app decides | Step 10 as planned |
