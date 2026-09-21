# Caliber — Backlog (224 items, dependency-ordered)

Generated from `Caliber-PRD-v1.6.pdf` by a 22-agent decomposition (9 lenses -> work items -> merge & sequence -> completeness / sequencing / contradiction critics). See `WORKLOG.md` for the findings that qualify this plan — **read Part 3 before scheduling from it.**

325 items were authored; 101 were merged as true cross-lens duplicates; **224 survive** and every one is placed in exactly one stage (verified: no orphans, no double-placement).

Effort key: S=small, M=medium, L=large, XL=extra-large. `!` marks an item on the critical path.

---

## Pre-build P0 (re-establish)  ·  Pre-build  ·  2 items

**Goal.** Turn the PRD's two biggest assertions - 'S0 done, proven end to end, code in caliber/' and 'Phase 0 PASSED, evidence in phase0-grader/' - back into files on disk, or declare honestly what is lost. Nothing else in this plan can start until the working directory contains something other than a PDF.

**Demo.** A cold checkout brings up Next.js -> FastAPI -> Postgres 17/pgvector and makes one live LLM call through the provider abstraction; alongside it, docs/S0-BASELINE-AUDIT.md and phase0-grader/PROVENANCE.md state, per artifact, recovered-verbatim / rebuilt / lost, with checksums and a recovery source.

**Entry.** Greenlight given (PHS-01's owner and restart condition). Access to wherever the author's caliber/ and phase0-grader/ trees exist - machine, remote, or backup.

**Exit.** Every artifact §12 names has a recorded status. If any Phase 0 gold-set file is unrecoverable, the §14 'grader not credible - RETIRED' row is downgraded to provisional in the risk register and the re-authoring cost (45 hand-graded answers) is entered as a scheduled item, not absorbed silently.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| !ARC-01 | Re-establish caliber/ monorepo and re-verify the S0 skeleton end to end | caliber/ monorepo (apps/web, services/api, packages/shared) + docs/S0-BASELINE-AUDIT.md + /health, /health/db,… | L | high | §12 Phase 1 S0, §11 Architecture & stack |
| !GRD2-01 | Recover or reconstruct the phase0-grader evidence bundle with provenance | phase0-grader/ directory in-repo: FINDINGS.md, gold_set_v1.json (15 answers, 1 role), gold_set_v2.json (30 ans… | L | high | §12 Phase 0, §15 Status, §14 grader row |

## Pre-build P1 (decisions, specs and contracts)  ·  Pre-build  ·  36 items

**Goal.** Close every contradiction and unstated rule that would otherwise be decided twice, differently, inside two slices - above all the 80-vs-70 pass threshold, the topic-state enum stated three ways, the free/paid cut point, the guide-vs-teach line, the readiness formula, and the completeness definition that is S1's own acceptance criterion.

**Demo.** A binder a second engineer can build from without asking a question: one register of D1-D10 and the seven non-goals, ~15 ADRs/specs each naming the PRD sentence it supersedes, one enum dictionary, one event taxonomy, one per-agent eval contract, and the Phase-1 schedule with its descope ladder.

**Entry.** None for most items - this stage runs in parallel with P0 from day one. GRD2-05 and PRG-01 want GRD2-03's bias numbers to be defensible, so they may be drafted here and ratified after Phase 0A.

**Exit.** No open contradiction remains that two slices could resolve differently. Specifically: exactly one operational pass threshold on one named scale; exactly one topic-state enum with a full transition matrix; a written definition of 100% completeness with worked fixture percentages two people compute identically; a readiness formula whose denominator behaviour under plan regeneration is stated; and gate-charters for S1-S5 written before S1 starts.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| GRD-01 | Build machine-readable decisions + non-goals register with PR decision-impact gate | docs/decisions/decisions.yml + docs/decisions/non_goals.yml + docs/decisions/README.md (reopen process) + .git… | M | low | §0 D1-D10, §5 Non-goals, §15 Decisions log |
| GRD-03 | Write ADR-002 defining what counts as hard-coded per-role content (FR-I5) | docs/decisions/adr/ADR-002-no-hardcoded-role-content.md | S | medium | §8 FR-I5, §0 D10, §1.2 |
| GRD-04 | Write ADR-003 fixing the exact free/paid cut point and its Phase-1 enforcement | docs/decisions/adr/ADR-003-paywall-cut-point.md | M | high | §0 D3, §5.1, §7.4 |
| GRD-05 | Write ADR-004 defining the operational guide-vs-teach line for D8 | docs/decisions/adr/ADR-004-guide-not-teach-line.md | M | high | §0 D8, §7.6, §7.7 |
| GRD-06 | Publish PRD v1.7 errata patch fixing broken cross-refs and misaligned tables | docs/prd/PRD-v1.7-errata.md + corrected Caliber-PRD-v1.7 source with a changelog row | S | low | §0 D2 rationale, §5.1, §4 |
| ARC-02 | Write the 8 ADRs that resolve the PRD's blocking data-model ambiguities | docs/adr/0001-pass-threshold.md through 0008-multi-role-journeys.md + docs/DATA-MODEL.md (ERD with cardinaliti… | M | medium | §7.5, §7.7, §10 |
| !GRD2-05 | Write the gate decision spec: reconcile 80% vs ~70 and define topic aggregation | docs/decisions/D11-gate-thresholds-and-aggregation.md + config/grading/thresholds.yaml + config/grading/aggreg… | M | high | §7.7, FR-D4, Appendix C |
| ONB-01 | Write capture field dictionary + shared enum module (py + ts) | docs/capture-field-dictionary.md + caliber/backend/app/domain/capture/enums.py + generated web/src/lib/enums.t… | M | medium | §7.1 (work-experience block, project block, signals derived, cross-check mechanism), FR-A5, Appendix B |
| ONB-02 | Specify completeness scoring: define 100%, 'thin', and the per-entity rollup | docs/completeness-gate-spec.md + caliber/backend/app/domain/capture/completeness_rules.yaml | M | high | §7.1 Completeness gate, Appendix B (per company/project), FR-A3 |
| ONB-03 | Author the onboarding state machine + post-confirmation edit contract | docs/onboarding-state-machine.md (state diagram + full transition table) + onboarding_state enum entry in enum… | M | high | §7.0 items 1-2, §7.1 Path A / Path B / Completeness gate, §7.4 |
| !BAR-01 | Lock beachhead role identity and the experience-level band taxonomy | docs/spec/beachhead-role-and-levels-v1.md + config/experience_levels.yaml (ordered level enum, year boundaries… | M | medium | §7.3, §3, §6 |
| !BAR-02 | Specify depth/evidence ordinal encoding and gap-size arithmetic | docs/spec/gap-scoring-v1.md §1 + config/scoring.yaml (depth_ordinals, evidence_ordinals, evidence_to_depth cro… | M | high | §7.3, §7.1, FR-A5 |
| BAR-03 | Specify weight normalization and the recency decay function | docs/spec/gap-scoring-v1.md §2-3 + config/scoring.yaml (weight_scale, normalization rule, recency half-life, m… | M | medium | §7.3, §7.1, §7.8 |
| BAR-04 | Canonicalize the five gap buckets and write the classification rules | docs/spec/gap-buckets-v1.md + the canonical bucket enum consumed by BAR-09/BAR-10 (must_know / should_know / c… | M | medium | §7.3, FR-B4, Appendix D |
| BAR-05 | Specify JD overlay semantics and its bounds | docs/spec/jd-overlay-v1.md + the JDOverlay field-level change matrix consumed by BAR-11 and BAR-23 | S | medium | §7.3, D7, §7.2 |
| BAR-06 | Write the role-bar versioning, pinning and migration policy | docs/spec/rolebar-versioning-v1.md + the migration decision matrix implemented later by BAR-32 | M | medium | §7.3, §10, §7.10 |
| PLN-02 | Spec the free/paid field boundary for the assessment plan | docs/decisions/D3-plan-free-paid-fields.md plus plan_visibility.yaml (field -> free/paid) consumed by the plan… | S | medium | §5.1, §0 D3, §7.4 |
| PLN-04 | Write the topic state machine transition spec (FR-C4) | docs/specs/topic-state-machine.md containing a 5x5 transition matrix, an event list, and a store-state -> disp… | S | medium | FR-C4, §10, §7.8 |
| PLN-05 | Decide the guidance resource policy (kind-of-resource vs real links) | docs/decisions/guidance-resource-policy.md plus resource_kinds.yaml (role-agnostic enum consumed by the guidan… | S | medium | Appendix E.5, §7.7, FR-E1 |
| PLN-06 | Encode the §7.4 ten-facet plan-coverage checklist as a spec artifact | plan_coverage_facets.yaml (10 entries: id, verbatim text, criterion/section, mapped gap bucket) plus docs/spec… | S | medium | §7.4 (The plan covers), FR-C2, §7.5 |
| PLN-07 | Write the plan regeneration and versioning policy (FR-C5) | docs/specs/plan-regeneration.md defining triggers, versioning, re-confirmation rule, denominator rule and orph… | S | medium | FR-C5, §10.1 (Adaptation agent), §7.5 (Adaptive) |
| PRG-01 | Write the normative readiness-score formula spec (v1) | docs/specs/readiness-score-v1.md (formula, credit table, denominator policy, monotonicity policy) with a worke… | M | high | §7.8, FR-G2, §7.3 |
| PRG-04 | Specify the next-best-action ranking rule and terminal states | docs/specs/next-best-action.md with an ordered rule set, tie-breakers, the copy string for each of the three v… | S | medium | §7.8, §7.3, §7.7 |
| PRG-05 | Define the honest-leveling read output contract and copy templates | docs/specs/honest-leveling-read.md + schemas/honest_leveling_read.schema.json + copy/leveling_read_templates.y… | M | high | §7.2, §7.5, §7.8 |
| PRG-06 | Specify Progress keying and the full recompute-trigger matrix | docs/specs/progress-state-and-recompute.md — Progress keying decision plus a trigger table (trigger → what rec… | M | high | §10 Data model, §12 Phase 1 scope, §7.3 (versioned bar, JD overlay) |
| PRG-07 | Define streak semantics and seed the badge catalogue | docs/specs/engagement-mechanics.md + config/badges.yaml catalogue seed with machine-checkable award predicates | S | low | §7.8, FR-G1, §10 Progress |
| AGT-10 | Specify the per-agent eval metric, threshold and gold-set size table | docs/eval-contract.md with one row per agent/prompt: metric, scorer module, threshold, minimum cases, owner, C… | M | high | §9 Eval harness, FR-I4, §11 Eval/CI |
| PHS-01 | Write the greenlight decision + Phase-1 schedule and descope policy | docs/process/phase1-plan.md — greenlight owner + restart condition, day-by-day S1-S5 schedule with named revie… | S | medium | Header / Status, §15 Status, §12 Phase 1 |
| PHS-04 | Publish the glossary, enum dictionary and approved-copy register | docs/glossary.md (Appendix B terms), docs/enums.md (nine canonical enums with exact string values), docs/copy/… | M | low | Appendix B, Appendix C, FR-C4 |
| PHS-06 | Define the holistic-review ritual that gates every Phase-1 slice | docs/process/holistic-review.md — reviewer roles, 60-90 minute agenda, standing checklist (vertical completene… | M | low | §12 Phase 1, FR-I5, FR-I4 |
| PHS-07 | Write per-slice gate charters and demo scripts for S1-S5 | docs/gates/S1.md through S5.md — each with scope, demo script, definition-of-done checklist, required telemetr… | M | low | §12 Phase 1 / S1-S5, §12 Phase 1 / Also in scope, §13 |
| PHS-08 | Specify Phase-1 exit and Phase-2 exit go/no-go criteria | docs/gates/phase-gates.md — Phase 0 gate restated as the template, Phase 1 exit criteria (five slice gates pas… | S | medium | §12 Phase 0 / Kill-continue gate, §12 Phase 1, §12 Phase 2 |
| PHS-09 | Operationalize all ten §14 risks into a tracked register | docs/risks/REGISTER.md — ten rows with id, risk, mitigation, owner, severity, likelihood, status (open / mitig… | M | low | §14 rows 1-10, §12 Phase 0 / Residual, Appendix F |
| PHS-10 | Track all six Appendix F open questions as owned, triggered decisions | docs/decisions/OPEN-QUESTIONS.md — seven rows (Appendix F items 1-6 plus the §15 brand pre-lock task), each wi… | S | low | Appendix F, §15 (post-decisions note), §12 Phase 0 / Residual |
| PHS-14 | Specify the analytics event taxonomy for the §13 funnel and rates | docs/metrics/event-taxonomy.md — versioned event list (onboarding_started, onboarding_completed, profile_confi… | M | low | §13, §10, §11 |
| PHS-17 | Set numeric targets for the three unbounded success metrics | docs/metrics/targets.md — per metric: bar, minimum sample N, measurement window, owner, review date, and the b… | S | medium | §13, §7.8, §14 row 9 |

## Pre-build P2 (human dependencies + brand)  ·  Pre-build  ·  3 items

**Goal.** Start the three long-lead human recruitments the PRD treats as free and instantaneous, and settle the name before it is baked into a repo, a package, a database and a domain.

**Demo.** A roster naming, with written availability: the D5 second senior AI engineer scheduled inside the S2 window, an independent senior for a role the founder did not author, and a non-technical spot reviewer; plus a dated domain/trademark record with a LOCKED or FALLBACK decision and a rename runbook.

**Entry.** BAR-01 has fixed the beachhead role identity and level bands, so the second senior can be briefed on a concrete scope.

**Exit.** Two named candidates per gate with contact status, an independence rule that forbids the D5 co-author from also being the holdout grader, and a brand decision recorded. If no second senior is available in the window, that is recorded as an S2 schedule risk with a stated fallback (ship v0.9 uncalibrated with a debt entry) rather than discovered at S2.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| GRD-08 | Complete D4 brand verification record and bound the rename blast radius | docs/brand/name_verification.md + config/branding.py (single PRODUCT_NAME constant) + docs/brand/rename_runboo… | M | medium | §0 D4, §15 (Non-blocking pre-lock task), Appendix F (Brand) |
| !GRD-09 | Stand up the external expert bench for the three non-founder human gates | docs/people/expert_bench.md + NDA/engagement template + reviewer roster (candidate, gate, status, availability… | M | high | §0 D5, §12 Phase 0 (Residual), §8 FR-I3 |
| BAR-07 | Define the two-senior calibration protocol and the expert spot-review gate | docs/process/rolebar-authoring-and-review.md + review-checklist template + role_bar_review sign-off record sch… | M | high | D5, §15 item 5, §7.3 |

## Phase 0A (grader re-baseline - hard gate)  ·  Phase 0  ·  7 items

**Goal.** Re-earn the kill/continue verdict the PRD already claims, on a pinned current model with a recorded prompt hash, using a harness that will still be there for every later eval. This is where the product's central bet is either re-confirmed or exposed.

**Demo.** A single command runs the v2 gold set blind through the provider-abstracted judge and prints verdict agreement, false-pass count, faker catch rate, rank separation and mean signed per-dimension bias - with the model id, prompt hash and temperature stamped on the results file.

**Entry.** P0 complete (the bundle and the skeleton exist). Note the honest dependency the PRD hides: re-running Phase 0 needs the provider client, the agent runtime, the prompt registry and the eval harness - i.e. a slice of S0 must exist before 'Phase 0' can be repeated.

**Exit.** GATE: >=85% verdict agreement AND zero false-pass AND zero rank inversions on gold_set_v2, reproduced on a pinned model. Below that, FINDINGS-replication.md carries an explicit no-go for wiring the grader live and S3 does not start. The passing run is committed as the frozen CI baseline.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| !AGT-02 | Re-establish the provider-abstracted LLM client and conformance suite | caliber/agents/llm/client.py (LLMClient protocol) + adapters/anthropic.py, adapters/openai.py, adapters/azure.… | M | medium | §9 Models, §10.1 design rules, §11 Architecture |
| !AGT-04 | Build the agent runtime with schema-validated I/O and a repair policy | caliber/agents/runtime.py (run_agent) + caliber/agents/base.py (AgentSpec: input model, output model, prompt i… | M | medium | FR-I2, §10.1 design rules, §11 Architecture |
| !AGT-06 | Create the versioned prompt registry and per-call provenance record | caliber/agents/prompts/registry.py + the prompts/ directory convention + prompt_version and prompt_hash column… | S | low | §9 Eval harness, §11 Eval/CI, §14 provider/model change row |
| !AGT-09 | Build the eval harness runner CLI and the gold-set file format | caliber/eval/runner.py + caliber/eval/schema.py (GoldCase / GoldSet) + the evals/<agent>/ layout + a `caliber-… | L | medium | §9 Eval harness, FR-I4, §10.1 design rules |
| !GRD2-03 | Build the agreement and calibration-bias metrics module | evals/metrics/agreement.py + evals/metrics/report_template.md | M | medium | §12 Phase 0 result/findings, §13 grader credibility, §7.7 (>=85% agreement) |
| !GRD2-04 | Re-run the v2 gold set to re-baseline the grader on a pinned current model | phase0-grader/results_replication_<date>.json + phase0-grader/FINDINGS-replication.md | M | high | §12 Phase 0, §14 provider/model change risk, §11 Eval/CI |
| BAR-08 | Recover Phase 0 grader artifacts and map gold answers to bar sub-skills | rolebar/gold/phase0_answer_to_subskill_map.json + docs/status/phase0-artifact-recovery.md (per-artifact recove… | M | high | §12 Phase 0, §7.3, §11 |

## Phase 0B (residual closure - runs parallel to S1-S4, gates S5)  ·  Phase 0  ·  3 items

**Goal.** Close the two residuals §12 and Appendix F make preconditions for any user-facing numeric score: the ~11-pt harsh bias, and self-authoring bias. Started early because the holdout depends on recruiting a human, which has weeks of lead time and zero budget in the PRD.

**Demo.** A signed gate memo stating go/no-go on displaying the '% ready' number, backed by a post-correction bias inside a pre-registered tolerance with false-pass still at zero, and an independent senior's blind grades on a role the founder did not author.

**Entry.** Phase 0A passed; GRD-09 has an engaged independent senior; BAR-01 has named a non-founder-authored role to grade.

**Exit.** GATE: mean signed bias inside the stated tolerance with agreement still >=85% and zero false-pass, AND an independent holdout of >=20 answers spanning strong/weak/fake-confident clearing the pre-registered bar. Until both pass, GRD-32's flag stays false and S5 ships qualitative progress only. A calibration layer defaulting to identity must exist before S3 so the judge service has something to call.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| !GRD2-06 | Implement the harsh-bias calibration layer and re-validate it | agents/judge/calibration.py + config/grading/calibration.yaml + phase0-grader/FINDINGS-calibration.md | L | high | Appendix F harsh-bias fix, §12 Phase 0 findings, §14 grader row |
| !GRD2-07 | Run the independent-senior holdout validation on a non-founder-authored role | evals/holdout_independent/ (gold set, grader brief, blind protocol doc, results json, GATE-MEMO.md) | L | high | Appendix F independent validation, §12 Phase 0 residual, §14 grader row |
| PRG-08 | Stand up the user-facing-score release gate checklist | docs/gates/user-facing-score-gate.md — a signed checklist with named sign-offs, referenced artifact paths/hash… | S | high | §12 Phase 0, §14 Risks, Appendix F |

## S0 (platform spine)  ·  Phase 1  ·  9 items

**Goal.** Turn the recovered skeleton into rails every later slice rides on: migrations and one enum module, provisioned environments, secrets, CI/CD, observability, model routing and the agent orchestrator. §12 calls S0 done; in practice only the three proof-of-life calls were done.

**Demo.** alembic upgrade head then downgrade base runs clean on a provisioned Postgres 17 with pgvector; a PR fails on a broken migration; one traced request shows a span per agent step with provider, model, tokens and latency; the S0 gate evidence pack is filed in the same format every later slice will use.

**Entry.** P0 complete; ARC-02's ADRs decided (enum-vs-lookup policy, PK and soft-delete conventions) so the baseline migration does not have to be redone.

**Exit.** GATE (PHS-03): all three §12 S0 claims demonstrated from a cold start by someone who did not rebuild the skeleton, with pinned versions recorded. Secrets scanner clean. Every one of the nine PRD enums defined exactly once, with a TS mirror generated in CI and a drift check.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| !ARC-03 | Alembic baseline, schema conventions, and the single-source enum module + data dictionary | services/api/db/base.py + alembic/env.py + migration 0001_baseline + packages/shared/enums.py (+ generated TS … | M | low | §7.1, §7.2, §7.3 |
| ARC-04 | Provision Azure Postgres 17 Flexible Server + pgvector per environment with backup/PITR | infra/bicep/postgres.bicep (or terraform equivalent) + docs/RUNBOOK-db.md | M | medium | §11 Infra, §12 Phase 1 S0 |
| ARC-05 | Azure Blob artifact store: container layout, storage adapter, SAS and lifecycle rules | infra/bicep/storage.bicep + services/api/storage/blob.py adapter + docs/ARTIFACT-LAYOUT.md | M | low | §11 Infra, §10 SkillProfile (source artifacts), §7.1 Path A |
| ARC-06 | Secrets and configuration: Key Vault, managed identity, settings module, env matrix | infra/bicep/keyvault.bicep + services/api/config.py (pydantic-settings) + docs/ENVIRONMENTS.md + .env.example | M | medium | §11 Infra, §9 Models, §11 Eval/CI |
| ARC-07 | CI/CD pipeline: build, test, migrate, eval gate, deploy to Azure | .github/workflows/ci.yml + .github/workflows/cd.yml + docs/RELEASE.md | L | medium | §11 Infra, §11 Eval/CI |
| ARC-08 | Observability: structured logging, agent-chain tracing, error tracking, PII redaction rule | services/api/obs/logging.py + services/api/obs/tracing.py + docs/OBSERVABILITY.md + dashboard and alert defini… | M | medium | §10.1, §11, §7.3 (competency: evals & observability) |
| AGT-03 | Define per-agent model routing, sampling and fallback config | caliber/agents/config/model_routes.yaml + caliber/agents/routing.py resolver + docs/model-routing.md rationale… | M | medium | §9 Models, FR-I1, §14 cost row |
| AGT-05 | Implement the agent orchestrator stage graph and failure semantics | caliber/agents/orchestrator.py + caliber/agents/orchestration/graph.py + agent_run / agent_stage tables with A… | L | medium | §10.1 design rules, §10.1 intro, §11 Architecture |
| PHS-03 | Record the S0 skeleton re-proof as the first slice-gate evidence pack | docs/gates/S0-gate.md — demo script plus captured output for the health endpoint, a Postgres 17/pgvector round… | S | medium | §12 Phase 1 / S0, §11 Architecture & stack, FR-I1 |

## S1 (onboarding + confirm)  ·  Phase 1  ·  32 items

**Goal.** §12's S1: manual entry first, then the LLM resume-parse, with the completeness gate that refuses to advance until 100% is captured and the candidate confirms it. The confirmed profile becomes the single source of truth §7.1 declares it to be.

**Demo.** A reviewer signs up cold, walks Path B to a confirmed profile, sees the gate refuse a thin profile and then say 'We now have a complete picture of what you've done' verbatim; then repeats via Path A with a real PDF, corrects the parse on the review screen, and confirms. Priya's non-technical profile completes the same flow unchanged.

**Entry.** S0 gate passed. ONB-01/02/03 decided (field dictionary, completeness rules file, onboarding state machine with the post-confirmation-edit invalidation contract).

**Exit.** GATE (PHS-27 holistic review): confirm refused at 99% and accepted at 100%, server-side as well as in the UI; both paths green end-to-end in CI with the parse stubbed; the §7.1 confirmation string byte-exact; no server-side fetch of a user-supplied artifact URL (D1); onboarding funnel events queryable in the store. S2 does not start on a fail.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| ONB-05 | Add User + EmailVerificationToken models and migration | caliber/backend/app/models/user.py (User, EmailVerificationToken) + Alembic migration | S | low | §7.1 Signup (zero friction), §11 Auth, §10 User (auth, profile) |
| ONB-06 | Build /auth signup, verify-email, resend, login endpoints + email sender | caliber/backend/app/api/auth.py + app/services/email_sender.py (azure/smtp/file backends) + auth dependency | L | medium | §7.1 Signup, §11 Auth: email + password (email verification), §11 Infra: founder's Azure |
| ONB-07 | Build signup / verify-email / login screens with all their states | web/app/(auth)/signup/page.tsx, /verify-email/page.tsx, /login/page.tsx + shared AuthShell component | M | low | §7.1 Signup (zero friction), §11 Frontend: React |
| !ONB-08 | Create capture core schema: work_experience, project, project_stack_item, education | caliber/backend/app/models/capture.py (WorkExperience, Project, ProjectStackItem, Education) + Alembic migrati… | L | medium | §7.1 work-experience block, §7.1 project block (the heart), §7.1 Path A/Path B education |
| ONB-09 | Build progressive per-entity capture CRUD API with draft/partial saves | caliber/backend/app/api/profile_capture.py + Pydantic request/response schemas in app/schemas/capture.py | L | medium | §7.1 Capture UX rules (progressive, not a wall of fields), FR-A2, FR-A3 |
| ONB-10 | Implement the completeness engine, completeness_state table and endpoint | caliber/backend/app/domain/capture/completeness.py + CompletenessState model + migration + GET /profile/comple… | L | high | §7.1 Completeness gate, Appendix B, FR-A3 |
| ONB-11 | Build Ravi and Priya capture fixtures + a profile factory for tests and demos | caliber/backend/tests/fixtures/profiles/ravi.json, priya.json + tests/factories/capture_factory.py + a dev see… | M | low | §6 Personas, D9, §1.2 |
| ONB-12 | Create skill_profile + skill_evidence schema (the FR-A5 output contract) | caliber/backend/app/models/skill_profile.py (SkillProfile, SkillEvidence) + Alembic migration | M | medium | FR-A5, §7.1 Signals derived, §7.1 Cross-check mechanism |
| ONB-13 | Build the deterministic derived-signals module (recency, ownership rollup, years of experience) | caliber/backend/app/domain/capture/signals.py + unit tests | M | medium | §7.1 Signals derived, §7.3 Inputs (years of experience), §7.3 Gap computation (priority = gap size x weight x recency) |
| ONB-14 | Build the Profiler agent: prompt, output schema, and normalization service | caliber/backend/app/agents/profiler/prompt.md + schema.py + service.py | L | high | §10.1 Profiler, FR-A5, FR-I2 |
| ONB-15 | Build the Profiler / evidence-strength gold set and CI eval gate | caliber/evals/profiler/gold_set.json + run_eval.py + CI job entry in the agent eval suite | L | high | FR-I4, §9 Eval harness (non-negotiable), §11 Eval/CI |
| !ONB-16 | Implement profile versioning, POST /profile/confirm gate, and the confirmed-profile read API | caliber/backend/app/models/profile_version.py + app/api/profile_confirm.py + app/domain/capture/confirmed_prof… | L | high | §7.1 Completeness gate ('single source of truth for every downstream stage'), FR-A3, §7.4 |
| ONB-17 | Build resume artifact storage: table, Azure container, upload endpoint with format and size limits | caliber/backend/app/models/resume_artifact.py + migration + app/api/resume_upload.py + app/services/object_sto… | M | medium | §7.1 Path A, FR-A1, §11 Infra: object storage for artifacts |
| ONB-18 | Build the PDF/DOCX text-extraction module with layout-aware output | caliber/backend/app/domain/capture/resume_extract.py + tests/fixtures/resumes/ (PDF and DOCX samples incl. two… | M | medium | §7.1 Path A (parser extracts...), FR-A1 |
| ONB-19 | Build the LLM resume-parse agent, async parse job, and status endpoint | caliber/backend/app/agents/resume_parse/prompt.md + schema.py + app/jobs/parse_resume.py + GET /profile/resume… | L | high | §7.1 Path A, FR-A1, FR-I2 |
| ONB-20 | Build the resume-parse gold set and CI eval gate | caliber/evals/resume_parse/gold_set.json + run_eval.py + CI job entry | L | medium | FR-I4, FR-A1, §9 Eval harness |
| ONB-21 | Build the parse-failure / partial-parse fallback path and confidence flags | caliber/backend/app/domain/capture/parse_fallback.py + per-field confidence column on draft capture rows + fal… | M | medium | §7.1 Path A, FR-A1, §7.1 review-and-confirm screen |
| ONB-22 | Create target_role_selection + job_description schema, endpoints, and the JD/no-JD branch flag | caliber/backend/app/models/target_role.py (TargetRoleSelection, JobDescription) + migration + app/api/target_r… | M | medium | §7.2 JD branch, D7, FR-A4 |
| ONB-26 | Build the path chooser and resume upload / parse-progress / failure screens | web/app/onboarding/path/page.tsx + web/app/onboarding/resume/page.tsx + components/ResumeDropzone.tsx, ParsePr… | M | medium | §7.1 Path A (preferred) / Path B, FR-A1, §7.1 Capture UX rules |
| ONB-27 | Build the review-and-confirm screen for parsed capture | web/app/onboarding/review/page.tsx + components/ReviewEntityCard.tsx, ConfidenceBadge.tsx | L | medium | §7.1 Path A (review-and-confirm screen), FR-A3, §7.1 Capture UX rules (pre-fills and asks only for gaps) |
| ONB-28 | Build the per-company work-experience editor screen | web/app/onboarding/experience/[id]/page.tsx + components/WorkExperienceForm.tsx, ExperienceList.tsx | M | low | §7.1 work-experience block, FR-A2, §7.5 (earliest experience -> current role) |
| ONB-29 | Build the per-project depth editor with progressive disclosure of all nine field groups | web/app/onboarding/project/[id]/page.tsx + components/ProjectDepthForm.tsx, StackPicker.tsx, ProcessPicker.tsx | L | medium | §7.1 project block (the heart), §7.1 Capture UX rules (progressive, not a wall of fields), FR-A2 |
| ONB-30 | Build the guided conversational manual flow (one project at a time) + collapsed education | web/app/onboarding/guided/page.tsx + components/GuidedStepper.tsx, ConversationalPrompt.tsx, EducationSection.… | L | medium | §7.1 Path B, §7.1 Capture UX rules (conversational, one project at a time; hardest problem and impact always asked), FR-A2 |
| ONB-31 | Build the completeness meter, nudge surface and the 'complete picture' gate moment | web/components/CompletenessMeter.tsx + components/NudgeList.tsx + web/app/onboarding/complete/page.tsx | M | medium | §7.1 Completeness gate, §7.1 verbatim copy, FR-A3 |
| ONB-34 | Instrument the onboarding funnel for the Activation metric | caliber/backend/app/telemetry/events.py (typed onboarding event definitions) + emit calls at each step + docs/… | M | low | §13 Activation, §13 Gap relevance, §7.0 |
| ONB-35 | Write end-to-end tests covering both onboarding paths through the gate | caliber/e2e/onboarding_path_a.spec.ts, onboarding_path_b.spec.ts, onboarding_gate.spec.ts + CI job | L | medium | §12 Phase 1 S1, FR-A1, FR-A2 |
| GRD-26 | Create the approved-copy module holding the PRD's verbatim strings under change control | app/copy/approved_strings.py (or shared i18n JSON) + docs/copy/approved_copy.md + tests/copy/test_approved_str… | S | low | §7.2 (Approved candidate-facing copy), §7.6, §7.2 (fit labels) |
| GRD-33 | Enforce the D1 ingestion boundary: no repo reading, artifact links never fetched | tests/boundaries/test_no_repo_ingestion.py + dependency denylist entry (VCS/repo SDK packages) + code-review r… | S | low | §0 D1, §5 Non-goals (Source-repo / code ingestion), §7.1 (Project block, manual, no repo connect) |
| ARC-18 | PII policy, retention, account-deletion cascade and third-party processing disclosure | DELETE /v1/account + services/api/privacy/erasure.py + retention job + docs/DATA-RETENTION.md + docs/PRIVACY-N… | L | high | §7.1 Path A, FR-A1, §11 Infra |
| ARC-33 | API contract: /v1 versioning, error envelope, OpenAPI spec, generated TS client and frontend data wiring | services/api/errors.py + openapi.json build artifact + packages/shared/api-client (generated) + apps/web route… | M | low | §11 Frontend, §11 Backend, FR-I2 |
| PHS-15 | Build the analytics_event table, emitter and retention policy | analytics/events.py emitter + analytics_event table (id, user_id, session_id, name, properties JSONB, occurred… | M | medium | §13, §10, §11 |
| PHS-27 | Run and record the S1 holistic review (onboarding + completeness gate) | docs/gates/S1-result.md — completed checklist, demo evidence, follow-up list with owners, verdict, and any ame… | S | low | §12 Phase 1 / S1, §7.1, FR-A1-A3 |

## S2 (role bar + assessment plan - the free aha ends here)  ·  Phase 1  ·  42 items

**Goal.** §12's S2: the founder-authored Senior AI Engineer bar, the experience-calibrated gap map, and the transparent assessment plan shown before any question. This is the largest and riskiest slice - it contains the XL depth-x-level matrix, the rubric anchors, and the two-senior calibration that D5 makes the credibility of the product.

**Demo.** A confirmed Ravi profile produces a five-bucket, priority-ordered gap map with a plain-English reason and a resolvable role-bar citation on every gap, then an assessment plan where every topic shows what it probes and why it is there, ending at the upgrade wall. Swapping the role-bar record changes the plan with no code change.

**Entry.** S1 gate passed (a confirmed profile exists to diff against). BAR-01 through BAR-06 decided. The D5 second senior is scheduled and available.

**Exit.** GATE (PHS-28 holistic review) plus the D5 sign-off gate: beachhead bar v1.0 is live with two recorded sign-offs and a reported inter-author agreement rate; no topic can exist with an empty why-it's-here or unresolvable source_refs; the paywall sits exactly at the end of the plan preview; the gap-analyst gold set clears its bar and a deliberately degraded engine fails it; the accuracy-rating instrument is capturing.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| !BAR-09 | role_bar.py models + Alembic migration for RoleBar/Version/Competency/SubSkill/ExpectedDepth | backend/app/models/role_bar.py + alembic/versions/xxxx_role_bar.py | M | low | §7.3, §10, FR-B1 |
| BAR-10 | gap_map.py models + Alembic migration for GapMap and Gap rows | backend/app/models/gap_map.py + alembic/versions/xxxx_gap_map.py | M | low | §10, §7.3, FR-B2 |
| BAR-11 | Pydantic + JSON Schema contracts for RoleBar, JDOverlay, GapMap and Gap | backend/app/schemas/rolebar.py, jd_overlay.py, gap_map.py + schemas/json/*.schema.json + tests/fixtures/schema… | M | low | FR-I2, §10.1, §7.3 |
| BAR-12 | Role-bar YAML authoring format, import/publish CLI and structural linter | tools/rolebar_cli (validate/import/diff/publish) + docs/authoring/role-bar-format.md + linter rule set | M | low | §7.3, FR-B1, FR-I5 |
| BAR-14 | Role-bar and gap-map REST endpoints | backend/app/api/routes/role_bars.py + backend/app/api/routes/gap_maps.py + OpenAPI entries | M | low | FR-B1, FR-B2, D3 |
| !BAR-15 | Author the beachhead competency-to-sub-skill taxonomy v0.1 | rolebars/<beachhead_role_key>/v0.1/bar.yaml (competencies + sub-skills, keys and names only) + authoring notes… | L | medium | §7.3, Appendix D, D5 |
| !BAR-16 | Author per-level expected depth, weight and how-it's-tested for every beachhead sub-skill | rolebars/<beachhead_role_key>/v0.9/bar.yaml (complete depth x level matrix, weights, how_tested) + per-compete… | XL | medium | §7.3, FR-B1, D6 |
| !BAR-17 | Author per-sub-skill rubric anchors and reference answers for the beachhead bar | rolebars/<role_key>/v0.9/rubrics/*.yaml + rolebars/<role_key>/v0.9/reference_answers/*.md + docs/spec/rubric-e… | L | high | §10, §7.7, Appendix C |
| !BAR-18 | Run the two-senior calibration pass and publish beachhead bar v1.0 | role_bar_review sign-off record for v1.0 + docs/status/beachhead-bar-calibration-report.md (agreement rate, di… | L | high | D5, §15 item 5, §7.3 |
| !BAR-19 | Sub-skill resolver: match SkillProfile skills to role-bar sub-skills | backend/app/services/subskill_resolver.py + rolebars/<role_key>/aliases.yaml + persisted match-report artifact | M | high | §7.3, §7.1, FR-A5 |
| BAR-39 | Bar coverage report: what candidates keep naming that no sub-skill covers | api/src/caliber/barcoverage.py + api/scripts/bar_coverage_report.py + tests | S | low | §7.3, D5, D10 |
| BAR-20 | Recency resolver and the per-skill recency ingestion contract | backend/app/services/recency.py + docs/contracts/profile-recency-contract.md (signed off by the ingestion lens… | S | medium | §7.1, §7.3, FR-A5 |
| !BAR-21 | Gap computation service: gap size, priority and probe-first ordering | backend/app/services/gap_engine.py (pure functions) + tests/unit/test_gap_engine.py | M | medium | §7.3, FR-B2, §7.1 |
| BAR-22 | Bucket classifier and probe-first tagging module | backend/app/services/gap_buckets.py + tests/fixtures/bucket_rule_table.json | M | medium | §7.3, FR-B4, Appendix D |
| BAR-23 | Role analyst agent + JD overlay builder | agents/role_analyst/prompt.md + backend/app/agents/role_analyst.py + JDOverlay persistence + tests | M | medium | §10.1, §7.3, D7 |
| BAR-24 | Gap analyst agent: plain-English reasons grounded with role-bar citations | agents/gap_analyst/prompt.md + backend/app/agents/gap_analyst.py + reason fallback templates | M | medium | FR-B3, §7.3, §9 |
| BAR-26 | Role fit-label scoring (Strong fit / Stretch / Not yet) | backend/app/services/role_fit.py + docs/spec/fit-labels-v1.md (thresholds + no-bar rule) | M | medium | §7.2, FR-A4, FR-B1 |
| BAR-27 | Free-tier gap map screen: bucketed, prioritized, explainable | frontend/app/(free)/gap-map/page.tsx + components/GapRow.tsx, BucketSection.tsx, GapMapStates.tsx + state fixt… | M | low | §7.3, FR-B3, FR-B4 |
| BAR-29 | Gap analyst gold set, scorer and agreement threshold | evals/gap_analyst/gold_set.json + evals/gap_analyst/score.py + evals/gap_analyst/README.md (protocol + thresho… | L | high | FR-I4, §9, §11 |
| BAR-32 | Bar-version bump migration worker and 'your bar was updated' state | backend/app/jobs/rolebar_migration.py + frontend/components/BarUpdatedNotice.tsx + job runbook | M | medium | §7.3, §10, §7.10 |
| BAR-33 | AI-landscape bucket source policy and curated landscape items file | rolebars/<role_key>/<version>/landscape.yaml + docs/process/market-signal-sourcing.md | M | medium | §7.3, §9, §14 |
| AGT-13 | Build the RAG grounding service over role-bar and confirmed profile | caliber/agents/grounding/{index.py,retriever.py} + grounding_chunk table with Alembic migration (source type, … | L | medium | §10.1 design rules, §9 Generation, §9 Anti-hallucination |
| ARC-24 | Re-embedding pipeline: embedding_jobs table and worker triggered by bar bumps and profile confirmation | embedding_jobs table + services/api/retrieval/embedder.py worker + scripts/backfill_embeddings.py | M | medium | §7.3 Versioned, §7.1 Completeness gate, §9 Generation |
| GRD2-08 | Author the 5-dimension rubric artifact with 0-20 band anchors on the RoleBar | role_bar/rubrics/senior_ai_engineer.rubric.yaml + role_bar/rubrics/rubric.schema.json | M | medium | Appendix C, §7.7 AI judge, §10 RoleBar |
| !PLN-08 | AssessmentPlan + Topic models and Alembic migration | caliber/backend/app/domains/plan/models.py (AssessmentPlan, Topic) plus the Alembic migration creating both ta… | M | low | §10 (AssessmentPlan -> Topic), FR-C4, Appendix B (Assessment plan) |
| PLN-09 | Topic state machine service with Progress projection sync | caliber/backend/app/domains/plan/state_machine.py plus the Progress projection writer and unit tests covering … | M | medium | FR-C4, §10 (Progress), §7.8 |
| PLN-10 | Enforce the gap -> topic -> guidance referential chain | Foreign-key constraints in the PLN-08 and PLN-21 migrations plus caliber/backend/app/domains/plan/integrity.py… | M | medium | §7.3 (Output -- the gap map), FR-B4, §10 |
| !PLN-11 | Plan-builder agent prompt and schema-validated I/O contract | caliber/backend/app/agents/plan_builder/prompt.md and schema.py (PlanBuilderInput / PlanBuilderOutput pydantic… | L | high | §7.4, FR-C1, FR-C2 |
| PLN-12 | Role-bar RAG grounding path and citation validator for plan generation | caliber/backend/app/agents/plan_builder/grounding.py (retrieval + citation validator) and its test suite | M | high | §7.3 (Grounded RAG), §9 (Generation, Anti-hallucination), §10.1 (Design rules) |
| !PLN-13 | Plan generation orchestration service with retry, cache and model tiering | caliber/backend/app/domains/plan/service.py with generate_plan() and its cache key derivation, plus service-le… | M | medium | §10.1 (Design rules), FR-I1, FR-I2 |
| PLN-14 | Plan API endpoints with completeness-gate precondition and tier shaping | caliber/backend/app/domains/plan/router.py with POST /api/plans, GET /api/plans/current, GET /api/plans/{id}, … | M | medium | §7.4, FR-C1, FR-C5 |
| PLN-16 | Assessment-plan view screen with per-item provenance | caliber/web/app/plan/page.tsx plus the PlanTopicCard component and its component tests | L | medium | §7.4 (Transparency principle), §11 (assessment-plan view), §7.0.4 |
| PLN-17 | Plan view loading, failure, blocked and minimal-plan states | Loading, error+retry, blocked-on-incomplete-profile and minimal-plan states in caliber/web/app/plan/, with sna… | M | low | §7.4, FR-A3, §13 (Activation) |
| PLN-19 | Plan-builder gold set and CI regression gate | evals/plan_builder/gold_set.json (>=20 cases across >=2 roles and >=2 experience levels), evals/plan_builder/s… | L | high | §9 (Eval harness), FR-I4, §10.1 (eval-gated) |
| PLN-20 | Worked-example plan fixtures for the two §7.4 role-parity cases | tests/fixtures/plans/devops_5yr.json and pmm_5yr.json plus tests/test_plan_role_parity.py | M | medium | §7.4 (worked examples), §0 D9, §6 (Priya) |
| ONB-24 | Build role-recommendation and honest-leveling gold sets with flattery-drift controls | caliber/evals/role_analyst/gold_set.json + caliber/evals/honest_leveling/gold_set.json + shared run_eval.py + … | L | high | FR-I4, §7.2 honesty over flattery, §9 Eval harness |
| ONB-32 | Build the target-role picker with fit labels, JD paste, and the approved copy block | web/app/onboarding/target-role/page.tsx + components/RoleRecommendationCard.tsx, FitLabel.tsx, JdPasteField.ts… | L | medium | §7.2 (two sides, fit labels, user keeps control, motivation guardrail), §7.2 Approved candidate-facing copy, FR-A4 |
| PRG-09 | Ship progress.py models + Alembic migration for track and topic state | caliber/backend/app/models/progress.py (ProgressTrack, TopicState, TopicStateTransition) + Alembic migration +… | M | medium | §10 Data model, §12 Phase 1 scope, FR-C4 |
| GRD-28 | Enforce the no-black-box transparency rule on every assessment-plan topic | Topic rationale + source_refs required fields (schema + API validation) + tests/transparency/test_plan_rationa… | M | low | §7.4, §8 FR-C1/FR-C2, §7.3 (gap links forward to the topic) |
| ARC-14 | Entitlements table and require_entitlement dependency enforcing the LOCKED D3 paywall | user_entitlements table + services/api/auth/entitlements.py + scripts/grant_entitlement.py + docs/PAYWALL-MATR… | S | low | D3 (LOCKED 2026-08-30), §5.1, §12 Phase 3 |
| GRD-23 | Build the upgrade-wall screen at the aha boundary with approved framing | frontend upgrade-wall screen + waitlist/notify-me capture (no payment provider) + copy strings in the approved… | M | low | §5.1, §0 D3, §7.4 |
| PHS-18 | Build the in-product gap-relevance rating instrument and rollup | gap_relevance_rating table + Alembic migration + two rating surfaces (post-gap-map, post-plan-preview) with ap… | M | low | §13 metric 2, §7.3, §7.4 |
| PHS-28 | Run and record the S2 holistic review (role bar + assessment plan) | docs/gates/S2-result.md — completed checklist including the role-bar swap test, demo evidence, follow-ups with… | S | medium | §12 Phase 1 / S2, §7.3, §7.4 |

## S3 (probe + grade)  ·  Phase 1  ·  23 items

**Goal.** §12's S3: the question generator plus the Phase-0-validated grader wired live, with the per-topic gate that turns per-answer scores into one pass/gap verdict - the aggregation rule the PRD never states anywhere.

**Demo.** A reviewer opens a topic, sees what it probes and why before any question, answers the seven journey-grounded probes (each citing a project from their own confirmed profile), and receives five dimension scores summing to the overall, named gaps, and evidence quotes highlighted inside their own answer.

**Entry.** S2 gate passed (a plan with topics exists). Phase 0A gate passed - the grader must not go live on an unreproduced baseline. GRD2-05's threshold and aggregation rule decided and in config.

**Exit.** GATE (PHS-29): the grader gold-set regression suite green in CI for the reviewed commit; the verdict threshold in code equals the number in the decision record (asserted by a no-literals test); two consecutive attempts on one topic never return the same variant; an answer with a blank reasoning field is rejected before any tokens are spent; cost per graded topic recorded.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| !GRD2-09 | Write the versioned open-ended judge prompt template v1 | agents/judge/prompts/open_ended_judge.v1.md + prompt registry entry with content hash | M | high | §7.7 AI judge, §9 Grader, §9 anti-hallucination |
| GRD2-10 | Define the judge output contract: schema, repair loop, and evidence-quote verifier | agents/judge/schemas.py + agents/judge/validators.py + schemas/judge_output.schema.json | L | medium | FR-D3, FR-I2, §9 anti-hallucination (require citations to the answer) |
| !GRD2-11 | Build the judge agent service with low-temperature, tiered model binding and telemetry | agents/judge/evaluator.py + agents/judge/config.yaml | L | medium | §9 Models / low temperature for grading, §7.7 AI judge, FR-I1 |
| !GRD2-12 | Build the assessment data model and Alembic migration | models/assessment.py (SQLAlchemy) + alembic/versions/xxxx_assessment_engine.py | L | medium | §10 data model (Exam, Question, Rubric, Attempt, Guidance), FR-C4, §11 Postgres |
| !GRD2-13 | Build the question-generator agent producing the 7-question journey-grounded probe set | agents/question_generator/prompts/probe_set.v1.md + agents/question_generator/schemas.py + agents/question_gen… | L | high | §7.5 probe set, Appendix C probe set, §10.1 Question generator |
| GRD2-14 | Build the fresh-variant generator and freshness store with difficulty-equivalence check | agents/question_generator/variants.py + variant table usage + config/grading/variant_policy.yaml | M | high | §7.7 anti-gaming, FR-D5, Appendix C fresh variants |
| GRD2-15 | Build the reference-answer generation, versioning and review pipeline | agents/question_generator/reference_answers.py + role_bar/reference_answers/senior_ai_engineer/*.md | M | high | §7.7 grounded in role-bar + reference answer, §9 anti-hallucination, §10.1 grounded design rule |
| GRD2-16 | Build the MCQ item schema, deterministic auto-grader, and mandatory reasoning capture | assessment/mcq.py + assessment/reasoning.py + schemas/mcq_item.schema.json + Answer.reasoning column | M | medium | §7.7 MCQ auto-graded instant, FR-D1, FR-D5 reasoning required |
| !GRD2-17 | Build the per-topic gate/aggregator service | assessment/gate.py + GateDecision persistence | M | high | §7.7 gating, FR-D4, Appendix B (Gate) |
| GRD2-19 | Build the assessment API surface (start, fetch, answer, submit, skip, grade, re-attempt) | api/assessment.py router + generated OpenAPI schema | L | medium | FR-D1..D5, FR-C4, §11 FastAPI |
| GRD2-20 | Build the topic-by-topic assessment/exam UI | app/assess/[topicId]/page.tsx + probe components (MCQ, open-ended, reasoning field, skip dialog) | L | medium | §7.5, §7.4 transparency, §7.7 |
| GRD2-21 | Build the grade feedback UI with a score-display flag gated on the harsh-bias memo | app/assess/[topicId]/result/page.tsx + score-display feature flag | L | medium | §7.7 per-dimension output pinpoints the weakness, Appendix E, Appendix F (before any user-facing numeric score) |
| GRD2-22 | Implement grader failure, timeout and degraded-mode handling | assessment/errors.py + grading retry queue + degraded-mode UI states | M | medium | §7.7 AI judge (core execution risk), §14 provider/model risk, FR-I2 |
| GRD2-23 | Build AI-answer/plagiarism flagging with a defined consequence policy | assessment/integrity.py + docs/policies/integrity.md + IntegrityFlag table | M | high | §7.7 anti-gaming, FR-D5, Appendix F anti-gaming depth |
| GRD2-24 | Implement optional time limits with a server-authoritative timer | assessment/timing.py + role_bar time_limit fields + exam-UI countdown component | S | low | §7.7 optional time limits, FR-D5, §7.3 role-bar fields |
| GRD2-33 | Instrument the assessment funnel and grader-quality telemetry | telemetry/assessment_events.py + event taxonomy doc + a grader-health dashboard panel | M | low | §13 engagement metrics, §13 grader credibility, §14 quality drift |
| AGT-17 | Build the evidence-quote citation verifier for grading and generation | caliber/agents/citations.py (span validator + chunk-id validator) + citation fields added to the evaluator and… | M | medium | §9 Anti-hallucination, §7.7 The AI judge, FR-D3 |
| AGT-20 | Formalize the grader gold set and freeze a CI regression baseline | evals/evaluator/gold_set_beachhead.json + evals/evaluator/gold_set_devops.json in the AGT-09 format, evals/eva… | M | medium | §9 Eval harness, §13, §11 Eval/CI |
| AGT-29 | Build the practical/design challenge generator and submission rubric grading | caliber/agents/question_generator/practical.py + prompts/question_generator/practical_challenge.v1.md + a prac… | M | medium | FR-D2, §7.7 question types, §12 Phase 2 (code auto-run) |
| AGT-31 | Author the Question generator gold set and its scoring functions | evals/question_generator/gold_set.json + evals/question_generator/scorer.py (coverage, grounding, targeting, f… | M | medium | §9 Eval harness, FR-I4, §11 Eval/CI |
| ARC-29 | grading_configs: versioned pass threshold, bias offset and rubric configuration | grading_configs table + seeds/grading_config.v1.yaml + services/api/grading/config.py implementing docs/adr/00… | S | medium | §7.7 Gating, FR-D4, Appendix C |
| GRD-22 | Write the entitlement boundary test suite covering every free and paid surface | tests/entitlements/test_free_paid_boundary.py (table-driven from docs/monetization/free_paid_matrix.md) + fron… | M | low | §0 D3, §5.1, §12 Phase 1 |
| PHS-29 | Run and record the S3 holistic review (probe + grade) | docs/gates/S3-result.md — completed checklist, a graded end-to-end transcript showing all five rubric dimensio… | S | medium | §12 Phase 1 / S3, §7.5, §7.7 |

## S4 (guidance + reassessment - the crown jewel loop)  ·  Phase 1  ·  17 items

**Goal.** §12's S4: gap -> exactly what to learn and why -> fresh-variant re-attempt -> pass and advance, with D8 enforced mechanically rather than by good intentions. This is the loop the whole product is.

**Demo.** Appendix E runs end to end: a buzzword-heavy RAG answer scores 21 and produces guidance naming the retrieval-vs-generation failure separation with no lesson body, the candidate re-attempts on a fresh variant, scores 86, and the topic flips to passed with readiness recomputed and the next topic unlocked.

**Entry.** S3 gate passed (a grader verdict with per-dimension gaps exists to feed guidance). GRD-05's ADR-004 allowed/forbidden lists and numeric caps decided, so the no-teach guard has a rule to enforce.

**Exit.** GATE (PHS-30) plus the D8 gate: guidance containing step-by-step instruction, a code block, or an over-cap mechanism explanation is rejected by the guard and by the eval; the Appendix E exemplar passes unchanged; every gap-open topic has retrievable guidance including skip-origin gaps; a skipped topic still renders as an open gap after skip, session end and re-login; the variant-freshness query returns zero repeats.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| PLN-21 | Guidance model and migration with a no-lesson-content schema | caliber/backend/app/domains/guidance/models.py (Guidance) plus the Alembic migration and the gap_source enum t… | M | low | §10 (Guidance), FR-C3, FR-E1 |
| !PLN-22 | Guidance agent prompt and schema modelled on the Appendix E exemplar | caliber/backend/app/agents/guidance/prompt.md and schema.py (GuidanceInput / GuidanceOutput) plus the Appendix… | L | high | §7.7 (Gap guidance), FR-C3, FR-E1 |
| PLN-23 | GapEvidence normalization adapters for non-judge gap sources | caliber/backend/app/domains/guidance/evidence.py (GapEvidence contract + judge, mcq, practical and skip adapte… | M | high | §7.7 (bullet 1), FR-D1, FR-D2 |
| !PLN-24 | Guidance generation service with idempotency and an explicit failure state | caliber/backend/app/domains/guidance/service.py with generate_guidance(), its persistence path, idempotency ke… | M | medium | §7.7, FR-C3, FR-D4 |
| PLN-25 | No-teaching output guard enforcing the D8 boundary on generated guidance | caliber/backend/app/domains/guidance/no_teach_guard.py plus the teaching-flavoured and compliant fixture pairs… | M | high | §0 D8, §7.6, FR-C3 |
| PLN-26 | Socratic hint generator with hint usage recorded on the Attempt | caliber/backend/app/agents/guidance/hint_prompt.md and schema, the POST /api/topics/{id}/hint endpoint, and th… | M | medium | FR-E2, §7.7, §7.6 |
| PLN-27 | Guidance view screen with the return-and-prove call to action | caliber/web/app/guidance/[topicId]/page.tsx plus the GuidanceCard component and its component tests | L | medium | §11 (guidance view), §7.7, §7.0.6 |
| PLN-28 | Adaptation agent and the plan regeneration job (FR-C5) | caliber/backend/app/agents/adaptation/prompt.md and schema, plus caliber/backend/app/domains/plan/regeneration… | L | high | FR-C5, §10.1 (Adaptation agent), §7.5 (Adaptive) |
| PLN-29 | Guidance-agent gold set and CI regression gate | evals/guidance/gold_set.json (>=25 cases across judge/mcq/practical/skip and >=2 roles), evals/guidance/scorer… | L | high | §9 (Eval harness), FR-I4, §14 (Question/guidance quality) |
| PLN-31 | Appendix E end-to-end loop integration test | caliber/backend/tests/e2e/test_appendix_e_loop.py plus the stubbed agent-response fixtures it drives | L | medium | Appendix E.1-E.7, §7.0 (core loop), §7.7 |
| PLN-32 | Activation-funnel and guidance telemetry events | caliber/backend/app/telemetry/plan_guidance_events.py event definitions, the frontend emitters, and analytics/… | M | low | §13 (Activation, Engagement), §5.1, §7.0 |
| !GRD2-29 | Build the reassessment loop orchestration with an explicit attempt policy | assessment/reassessment.py + config/grading/attempt_policy.yaml + attempt-history query | L | medium | §7.7 reassessment loop, Appendix B reassessment loop, §12 Phase 1 S4 |
| PRG-14 | Build the gap↔topic link table and the gap-closure service | caliber/backend/app/models/gap_link.py (GapTopicLink) + app/services/gap_closure.py + Alembic migration | M | medium | §7.3, §7.8, §7.7 |
| GRD-29 | Add the skip-persistence invariant tests so a skipped topic never disappears | tests/invariants/test_skip_persistence.py covering the FR-C4 state machine, gap list, readiness computation an… | S | low | §7.5 (Skip), §7.7 (Skip is respected but honest), §8 FR-C4 |
| PHS-21 | Instrument anti-gaming coverage and flag rates for risk burn-down | metrics/anti_gaming.sql + answer_flag table and review-queue view + docs/risks/anti-gaming-baseline.md recordi… | M | medium | §14 row 8, FR-D5, §7.7 Anti-gaming |
| PHS-30 | Run and record the S4 holistic review (guidance + reassessment) | docs/gates/S4-result.md — completed checklist, a recorded gap→guidance→reassess→pass transcript, variant-fresh… | S | medium | §12 Phase 1 / S4, §7.6, §7.7 |
| PHS-33 | Audit assess-and-guide positioning across every gap and guidance surface | docs/risks/positioning-audit.md — surface-by-surface audit table (surface, current copy, verdict, fix) plus th… | S | low | §14 row 3, §0 D8, §7.6 |

## S5 (progress dashboard + honest leveling + first real user run)  ·  Phase 1  ·  26 items

**Goal.** §12's S5: the surface a returning user lands on, the read that makes the honesty positioning concrete, and the only point where the §13 metrics get real data. Its centrepiece - the '% ready' number - is gated on Phase 0B.

**Demo.** One real beachhead-role user runs the whole §7.0 journey and lands on a dashboard showing every topic and its state, the gap open/closed tracker, exactly one next-best-action, the honest-leveling read with its rationale, and either the readiness percentage or - if Phase 0B has not closed - a qualitative progress read with no numeric score anywhere.

**Entry.** S4 gate passed (topics can reach passed and gaps can close, so the dashboard has something true to show). PRG-01's formula and PRG-06's recompute-trigger matrix decided. PRG-08's ship/no-ship decision on the number recorded.

**Exit.** GATE (PHS-31, and the Phase-1 exit gate): the readiness score never decreases across a pass-only sequence with a fixed plan and bar version; no 0-100 number renders while GRD-32's flag is false; the activation funnel and both engagement rates compute from events alone with their N; every §13 metric is reported or explicitly marked not-yet-measurable; both Phase 0 residuals have a recorded status.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| !PRG-11 | Implement readiness.py as a pure, breakdown-returning calculator | caliber/backend/app/services/readiness.py — compute_readiness(track_snapshot, role_bar_version, config_version… | L | high | §7.8, FR-G2, §7.3 |
| PRG-12 | Add the readiness snapshot history table and scoring-config registry | caliber/backend/app/models/readiness_snapshot.py + readiness_config registry table + Alembic migration + confi… | M | high | D2, §10 Data model, §13 |
| PRG-13 | Wire the recompute orchestrator to the trigger matrix | caliber/backend/app/services/progress_recompute.py + event handler registrations covering every trigger in the… | L | medium | §7.8, Appendix E step 7, FR-C5 |
| PRG-15 | Build the honest-leveling read service and its agent prompt | caliber/backend/app/services/leveling_read.py + prompts/leveling_read.md + LevelingRead model/migration | L | high | §7.2, §7.5, §7.8 |
| PRG-16 | Implement the next_best_action resolver returning exactly one action | caliber/backend/app/services/next_best_action.py returning NextAction(verb, target_id, reason, is_terminal) | M | low | §7.8, §7.3, D8 |
| PRG-17 | Implement the streak and badge service with a backfill path | caliber/backend/app/services/engagement.py + models StreakState and BadgeAward + migration + scripts/backfill_… | M | low | §7.8, FR-G1, §10 Progress |
| !PRG-18 | Ship GET /api/v1/progress/{track_id} as one dashboard aggregate | caliber/backend/app/api/routes/progress.py + schemas/progress_dashboard.py (ProgressDashboardResponse) + OpenA… | M | medium | §7.8, FR-G1, FR-G2 |
| PRG-19 | Enforce the D3 free/paid boundary on the progress surface | caliber/backend/app/services/entitlements.py + a route dependency + the free-tier variant of ProgressDashboard… | M | medium | §5.1 / D3, §7.8, §7.2 |
| PRG-20 | Add the mock-interview unlock predicate as a flagged Phase 1 seam | caliber/backend/app/services/unlock.py — is_mock_interview_unlocked(track) + config key readiness.mock_unlock_… | S | low | §7.9, §5 Non-goals, FR-G2 |
| PRG-21 | Build the TopicMap component showing every topic and its state | caliber/frontend/app/(dashboard)/progress/components/TopicMap.tsx + StateLegend.tsx | L | medium | §7.8, FR-G1, §7.4 |
| PRG-22 | Build the % ready headline with its how-this-is-computed disclosure | caliber/frontend/app/(dashboard)/progress/components/ReadinessHeadline.tsx + ScoreDisclosure.tsx | M | medium | §7.8, FR-G2, D9 |
| PRG-23 | Build the gap → closed tracker panel with the five buckets | caliber/frontend/app/(dashboard)/progress/components/GapTracker.tsx | M | low | §7.8, §7.3, FR-B3 |
| PRG-24 | Build the NextBestAction card with a single primary CTA | caliber/frontend/app/(dashboard)/progress/components/NextBestAction.tsx | S | low | §7.8, D8, D3 |
| PRG-25 | Build the honest-leveling read panel with free and paid variants | caliber/frontend/app/(dashboard)/progress/components/LevelingRead.tsx (paid updating and free profile-derived … | M | medium | §7.2, §7.8, §5.1 / D3 |
| PRG-26 | Build the streaks and badges strip as secondary, light gamification | caliber/frontend/app/(dashboard)/progress/components/EngagementStrip.tsx | S | low | §7.8, FR-G1 |
| !PRG-27 | Build the progress dashboard shell with all five non-happy states | caliber/frontend/app/(dashboard)/progress/page.tsx + LoadingSkeleton, EmptyState, LockedState, ErrorState, Sta… | L | medium | §7.8, §13 (engagement), §5.1 / D3 |
| PRG-30 | Author progress fixtures and seed tracks for both personas | caliber/backend/tests/fixtures/progress/*.json + scripts/seed_progress_tracks.py + a frontend fixture loader f… | M | low | §6 Personas, D9, §7.8 |
| PRG-31 | Write the readiness invariants and golden-snapshot test suite | caliber/backend/tests/test_readiness_invariants.py (property-based) + tests/golden/readiness/*.json snapshots | M | medium | §7.8, FR-G2, PRD §7.5 adaptive |
| PRG-32 | Build the leveling-read eval gold set and CI gate | evals/leveling_read/gold_set.json (≥25 cases) + evals/leveling_read/run.py + a CI job with a stated pass bar | L | medium | FR-I4, §9 (eval harness), §7.2 |
| BAR-28 | Role-bar weight rollup service for the readiness-score denominator | backend/app/services/rolebar_weights.py + docs/contracts/readiness-denominator.md | S | medium | §7.8, FR-G2, D2 |
| GRD-27 | Build the tone guardrail eval for leveling, verdict and guidance copy | evals/tone_guardrail/{banned_patterns.yml, rubric.md, cases.jsonl, score_tone.py} + CI job over a fixed sample… | M | medium | §7.2 (Motivation guardrail), §7.5 (Honesty moment), §7.2 (honesty over flattery) |
| !GRD-32 | Gate every user-facing numeric score on the two Phase 0 residuals | app/core/calibration_status.py + calibration_status table (grader_bias_closed, independent_holdout_passed with… | M | high | §12 Phase 0 (Residual), §7.8, §8 FR-G2 |
| PHS-16 | Implement the activation-funnel and engagement-rate metric queries | metrics/activation_funnel.sql and metrics/engagement.sql (or equivalent views) + docs/metrics/definitions.md +… | M | low | §13 metrics 3-4, §7.8, FR-C4 |
| PHS-19 | Build the internal success-metrics dashboard for all five §13 metrics | /admin/metrics internal page rendering six tiles from the metric queries, each showing value, target, N and la… | M | low | §13, §14 row 10, §11 Eval/CI |
| PHS-31 | Run the S5 review and the Phase-1 exit go/no-go decision | docs/gates/S5-result.md + docs/gates/phase1-exit.md — completed checklist, the metrics readout with N per metr… | M | medium | §12 Phase 1 / S5, §7.8, §13 |
| !PHS-32 | Design and run the S5 first-real-user protocol | docs/research/s5-user-run.md — protocol (N, recruitment criteria, consent text, session script, observation fo… | L | medium | §12 Phase 1 / S5, §13, §3 beachhead |

## Cross-cutting (arm before the slice each one polices)  ·  Cross-cutting  ·  9 items

**Goal.** Guardrails and instrumentation that belong to no single slice because they police all of them. Each has a 'must be armed by' slice, and arming one after the slice it guards is the same as not building it.

**Demo.** A PR that hard-codes a role name fails; a PR that changes a model id without a swap report fails; a PR that drops grader agreement below the floor fails and names the failing cases; the cost dashboard shows spend per user and per completed topic; a nightly job drives the whole pipeline for a Senior PMM fixture with no code branch, proving D9.

**Entry.** Each has its own: GRD-14 needs GRD-03's ADR and seeded role-bar data (arm by S2); AGT-11 and BAR-30 need AGT-10's eval contract and the frozen baseline (arm by S3); ARC-09 and AGT-08 need the agent runtime (arm by S1, before the free tier's LLM-heavy chain runs); GRD-25 needs the entitlement model (arm by S2); GRD-15 needs the full pipeline (S4).

**Exit.** Each gate demonstrably bites once - a deliberate violation fixture fails it - rather than being merely configured. PHS-34's drift log stays open for the life of the build; it is the only place the PRD and the code are reconciled.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| GRD-14 | Ship the FR-I5 no-hard-coded-per-role-content CI check with an allowlist | tools/lint_no_role_content.py + config/role_content_allowlist.yml + CI job 'no-hardcoded-role-content' + tests… | L | medium | §8 FR-I5, §0 D10, §1.2 |
| GRD-15 | Build the role-agnostic conformance harness on a non-technical role fixture | tests/conformance/test_role_agnostic_pipeline.py + fixtures/roles/senior_pmm_profile.json + nightly CI job (co… | L | medium | §0 D9, §1.2, §6 (Priya) |
| GRD-25 | Add free-tier usage caps and per-user LLM spend accounting before the paywall | app/limits/rate_limits.py (per-user caps on resume re-parse, gap-map regeneration, plan regeneration, target-r… | M | medium | §14 (Cost per user), §5.1, §9 (Models) |
| BAR-30 | Role-bar structural and content regression gold set with CI gate | .github/workflows/eval.yml role-bar job + evals/role_bar/regression_set.json + evals/role_bar/run.py | M | medium | §11, §9, FR-I4 |
| AGT-08 | Implement prompt/response caching and per-assessment cost budgeting | caliber/agents/cache.py (key builder + store) + cache and budget blocks in model_routes.yaml + a budget-exceed… | M | medium | §14 cost row, §9 Models |
| AGT-11 | Wire the agent eval suite into CI with a defined regression gate | .github/workflows/agent-evals.yml (or the Azure Pipelines equivalent) + caliber/eval/gate.py + evals/baselines… | M | medium | §11 Eval/CI, §14 provider/model change row, §14 quality drift row |
| AGT-12 | Add the model-swap regression eval workflow and swap sign-off record | a `caliber-eval swap --route <key> --from <model> --to <model>` command + the evals/swaps/<date>-<route>.md si… | M | medium | §14 provider/model change row, FR-I1, §9 Models |
| ARC-09 | agent_runs / llm_calls telemetry tables with cost accounting and a per-user ceiling | agent_runs and llm_calls tables + migration + services/api/obs/cost.py + docs/COST-MODEL.md with the rollup SQ… | M | low | §14 Risks (Cost per user), §9 Models, §10.1 |
| PHS-34 | Maintain the PRD changelog and a PRD-vs-build drift log | docs/prd/CHANGELOG.md (continuing Appendix A) + docs/prd/drift-log.md (PRD statement, build reality, authorizi… | S | low | Appendix A, §7.7 vs Appendix C, §0 D2 rationale |

## Phase 2  ·  Phase 2  ·  13 items

**Goal.** §12 Phase 2: role expansion off the beachhead (including the non-technical role that proves D9 for real), the mock interview, and the outcome loop that D2 depends on for recalibration and §4 calls the only durable moat.

**Demo.** A Product Marketing Manager role-bar is generated, expert-reviewed by someone with actual PMM background, passes its own eval set, and drives Priya's gap map and plan through the identical code path; a mock interview runs with adaptive follow-ups and writes its post-mortem back onto the topic map.

**Entry.** Phase-1 exit gate passed. GRD2-36's template and reviewer-qualification rule exist before any generated bar goes live.

**Exit.** GATE: no role reaches live without a passing per-role eval artifact and a named expert sign-off record, enforced at the service layer through every path (CLI, API, console). Outcome capture is rejected without an explicit opt-in row, and the anonymized export contains nothing that identifies a candidate.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| BAR-34 | Role-bar generator agent for a new role on demand | agents/role_bar_generator/prompt.md + backend/app/agents/role_bar_generator.py + draft-version writer + genera… | L | high | FR-I3, D9, D10 |
| BAR-35 | Expert spot-review console and enforced go-live gate | frontend/app/(internal)/role-bar-review/ + backend/app/api/routes/role_bar_review.py + go-live guard in the pu… | M | medium | FR-I3, §7.3, §9 |
| BAR-36 | Author the Product Marketing Manager role-bar and its per-role eval set | rolebars/product_marketing_manager/v1.0/ (bar.yaml, rubrics/, reference_answers/, landscape.yaml) + evals/role… | L | high | §7.3, D9, §6 |
| BAR-37 | Outcome-loop to role-bar drift proposal pipeline | backend/app/jobs/bar_drift_proposals.py + drift proposal review view + docs/spec/bar-drift-inputs.md | M | medium | §7.10, §7.3, §12 Phase 2 |
| GRD2-34 | Build the practical/code/design challenge runner with a sandboxed executor (Phase 2) | assessment/practical/ (submission schema, test-harness spec, sandboxed runner service) + docs/specs/practical-… | XL | high | FR-D2, §7.7 question type 2, §12 Phase 2 (code auto-run) |
| GRD2-35 | Build adaptation agent v2 and the richer guidance explainer (Phase 2) | agents/adaptation/rules_v2.yaml + agents/guidance/prompts/explainer.v2.md + evals for both | L | medium | §12 Phase 2 (deeper adaptive probing, richer guidance explainer), §7.5, §7.7 |
| GRD2-36 | Create the per-role eval gold-set template and expert spot-review go-live gate (Phase 2) | evals/roles/_template/ + docs/process/role-golive-checklist.md + a config startup check | L | high | §9 new roles get a per-role eval set, FR-I3, FR-I4 |
| AGT-38 | Build the Phase 2 Interviewer agent, its rubric and its gold set | caliber/agents/interviewer/{spec.py,schema.py} + prompts/interviewer/{conduct_turn.v1.md,post_mortem.v1.md} + … | XL | high | §7.9, FR-F1, FR-F2 |
| ARC-35 | Phase 2 persistence: outcomes, mock-interview sessions and the anonymized aggregate export | Alembic migration 0015_outcomes + outcomes, interview_sessions, interview_turns tables + views/anonymized_outc… | L | medium | §7.9, §7.10, §10 (Phase 2) Outcome |
| PRG-34 | Build the readiness↔outcome calibration harness (D2) | caliber/backend/analytics/readiness_calibration.py + docs/reports/readiness-calibration-template.md + a candid… | L | high | D2, §7.10, §13 |
| PRG-35 | Implement the mock-interview unlock rule and post-mortem mapping | caliber/backend/app/services/unlock.py (rule + hysteresis) + app/services/postmortem_mapping.py writing mock-i… | M | medium | §7.9, FR-F2, §7.8 |
| PHS-35 | Plan the Phase-2 outcome-loop instrumentation for the readiness correlation | docs/metrics/outcome-loop-spec.md + draft Outcome table and event schema (interview result, questions captured… | M | medium | §13 metric 5, §7.10, FR-H1-H2 |
| PHS-37 | Decide the mock-interview unlock bar and the D2 readiness recalibration plan | docs/decisions/D13-readiness-bar-and-recalibration.md — unlock threshold with rationale, recalibration method,… | S | medium | §7.9, §0 D2, §13 metric 5 |

## Phase 3  ·  Phase 3  ·  2 items

**Goal.** §12 Phase 3: broad role-library rollout with a cadence and a rollback, and anti-gaming hardening beyond the MVP controls. Payments, teams and mobile polish also live here per §12 but generated no work items in this pass.

**Demo.** Someone who did not write the runbook takes one new role from generation to live - eval set, spot review, sign-off, gradual rollout - and then demotes it again via the rollback procedure without affecting live users.

**Entry.** Phase 2 complete with at least two live roles, one non-technical, and enough usage that the anti-gaming baseline from PHS-21 has real numbers to harden against.

**Exit.** A live role's quality regression can be detected and rolled back without a code deploy, and legitimate pass rate shows no measurable regression against the pre-hardening baseline.

| ID | Title | Deliverable | Eff | Risk | PRD |
|---|---|---|---|---|---|
| BAR-38 | Per-role eval-set template and role-library rollout runbook | evals/templates/per_role_eval_set_template/ + docs/process/role-library-rollout-runbook.md | M | medium | §12 Phase 3, §9, §14 |
| GRD2-37 | Ship anti-gaming hardening: cross-user similarity, pool depletion, integrity dashboard (Phase 3) | assessment/integrity_v2.py + variant pool replenishment job + integrity dashboard | L | medium | §12 Phase 3 (anti-gaming hardening), Appendix F anti-gaming depth, §14 gaming the gates |

---

## Merged items (101)

If you are looking for an ID that is not above, it was merged. **Note:** the sequencing critic found ~100 of these IDs are still referenced in surviving items' `depends_on` fields — see WORKLOG Part 3, SEQ-1.

| Merged ID | Kept as |
|---|---|
| AGT-01 | GRD2-01 |
| AGT-07 | ARC-09 |
| AGT-14 | GRD2-08 |
| AGT-15 | GRD2-09 |
| AGT-16 | GRD2-05 |
| AGT-18 | GRD2-15 |
| AGT-19 | GRD2-17 |
| AGT-21 | GRD2-06 |
| AGT-22 | GRD2-07 |
| AGT-23 | ONB-14 |
| AGT-24 | BAR-23 |
| AGT-25 | BAR-24 |
| AGT-26 | PLN-11 |
| AGT-27 | GRD2-13 |
| AGT-28 | GRD2-16 |
| AGT-30 | GRD2-14 |
| AGT-32 | PLN-22 |
| AGT-33 | PLN-28 |
| AGT-34 | GRD2-23 |
| AGT-35 | BAR-34 |
| AGT-36 | BAR-35 |
| AGT-37 | GRD2-36 |
| ARC-10 | AGT-05 |
| ARC-11 | AGT-08 |
| ARC-12 | ONB-05 |
| ARC-13 | ONB-06 |
| ARC-15 | ONB-08 |
| ARC-16 | ONB-12 |
| ARC-17 | ONB-17 |
| ARC-19 | ONB-16 |
| ARC-20 | BAR-09 |
| ARC-21 | BAR-12 |
| ARC-22 | ONB-22 |
| ARC-23 | AGT-13 |
| ARC-25 | BAR-10 |
| ARC-26 | PLN-08 |
| ARC-27 | GRD2-12 |
| ARC-28 | GRD2-12 |
| ARC-30 | PLN-21 |
| ARC-31 | PRG-09 |
| ARC-32 | PHS-15 |
| ARC-34 | AGT-11 |
| BAR-13 | AGT-13 |
| BAR-25 | PRG-15 |
| BAR-31 | PHS-18 |
| GRD-02 | GRD2-05 |
| GRD-07 | GRD2-01 |
| GRD-10 | BAR-07 |
| GRD-11 | BAR-09 |
| GRD-12 | BAR-35 |
| GRD-13 | GRD2-07 |
| GRD-16 | PLN-22 |
| GRD-17 | PLN-22 |
| GRD-18 | PLN-29 |
| GRD-19 | PLN-26 |
| GRD-20 | ARC-14 |
| GRD-21 | ARC-14 |
| GRD-24 | PLN-32 |
| GRD-30 | GRD2-14 |
| GRD-31 | AGT-17 |
| GRD-34 | AGT-12 |
| GRD-35 | PHS-35 |
| GRD2-02 | AGT-09 |
| GRD2-18 | PLN-09 |
| GRD2-25 | ARC-14 |
| GRD2-26 | PLN-31 |
| GRD2-27 | PLN-22 |
| GRD2-28 | PLN-26 |
| GRD2-30 | PLN-28 |
| GRD2-31 | AGT-11 |
| GRD2-32 | AGT-08 |
| ONB-04 | ARC-01 |
| ONB-23 | BAR-23 |
| ONB-25 | PRG-15 |
| ONB-33 | PRG-25 |
| ONB-36 | ARC-18 |
| PHS-02 | GRD2-01 |
| PHS-05 | GRD2-05 |
| PHS-11 | GRD-08 |
| PHS-12 | GRD-09 |
| PHS-13 | AGT-10 |
| PHS-20 | ARC-09 |
| PHS-22 | AGT-20 |
| PHS-23 | AGT-11 |
| PHS-24 | AGT-12 |
| PHS-25 | GRD2-06 |
| PHS-26 | GRD2-07 |
| PHS-36 | GRD2-36 |
| PLN-01 | ARC-01 |
| PLN-03 | GRD2-05 |
| PLN-15 | ARC-14 |
| PLN-18 | GRD-23 |
| PLN-30 | GRD-26 |
| PLN-33 | PHS-18 |
| PLN-34 | GRD2-35 |
| PRG-02 | PLN-04 |
| PRG-03 | GRD2-05 |
| PRG-10 | PLN-09 |
| PRG-28 | PHS-14 |
| PRG-29 | PHS-18 |
| PRG-33 | PHS-32 |
