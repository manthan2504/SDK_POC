# Caliber POC — Database & Persistence Specification

> **Status:** research output, written 2026-09-21 for the engineer who implements the
> PostgreSQL 18 schema next. Nothing here is code, and nothing here changes RULEBOOK.md.
>
> **Sources, in the order they were trusted:**
> 1. `D:\SDKPOC\Caliber-PRD-v1.7.html` — what must be persisted and why (§ and FR numbers below).
> 2. `D:\SDKPOC\caliber-poc\reference\` — the imported Caliber design snapshot (ADRs, `plan/`, `llm/`).
> 3. `D:\Caliber\api\src\caliber\` — the real product repo, read-only. Ground truth for **naming and shape**.
> 4. The POC as built: `app/pipeline/store.py`, `app/pipeline/runner.py`, `app/pipeline/steps.py`,
>    `app/agents/base.py`, `RULEBOOK.md` §4, §11, §16.2, §17.
>
> Where the PRD and the Caliber repo disagree, both are shown and neither is silently picked.
> Where nothing says, it says **not specified**.

---

## 0. One-paragraph summary

The pipeline needs **three tables today** (`pipeline_run`, `step_run`, `checkpoint_decision` — all
three already exist in SQLite under the names `runs`, `step_runs`, `checkpoints`), **one table it is
currently missing** (`run_input`, because a resumed run cannot today reconstruct the resume text it
started from), and **eight more that arrive with pipeline steps [4]–[8]**. The move to Postgres is
mostly a type upgrade — `timestamptz`, `JSONB`, `numeric` for money, identity keys — plus one
structural change the POC's own rulebook already demands but the code does not do: the `step_run`
row must be written *before* the agent call, not after (RULEBOOK §4 rule 9, `SEQUENCING.md` §6
trap 2). `pgvector` is not needed. Redis/ARQ and `job_run` are not needed. The Caliber trace row's
two biggest columns — `prompt` and `response` — must **not** be copied, and that is a direct
conflict with the real repo that this document flags rather than resolves.

---

## 1. Every PRD requirement that constrains persistence

### 1.1 Hard requirements (the PRD states these outright)

| Ref | Requirement (quoted / closely paraphrased) | What it forces on the schema |
|---|---|---|
| **FR-I8** (§8.I) | *"The output of every step is saved before the next step runs. A run can resume from the last completed step, and any single step can be re-run on its own."* | A durable per-step output, written and committed **before** the next step starts. Resume must not need anything held in process memory. "Re-run a step on its own" needs that step's **logical inputs** to be reconstructible, not only its output. |
| **FR-I10** (§8.I) | *"Every step writes an audit record (agent name, agent/prompt version, model, input reference, output, validation result, latency, tokens/cost)."* | Eight named fields, minimum. Note the PRD says **input *reference***, not input; and **output**, not output reference. |
| **FR-I9** (§8.I) | *"On schema-validation failure or provider error, the app retries that step (default: up to 2 retries with the validation error fed back). It then fails safe: the step is marked failed and the candidate sees a recoverable error. Downstream steps never run on invalid data."* | A per-attempt row (not per-step), a retry counter, a terminal `failed` status on the step, and a human-readable failure reason on the run. |
| **FR-I11** (§8.I) | *"Human checkpoints (profile confirm, role pick, plan view, answer submit, retry) are app-level pauses in the pipeline, not agent behaviour."* | A run status meaning "waiting for a person", the identity of the checkpoint being waited on, and the decision once it is given. Five named checkpoints. |
| **FR-I7** (§8.I) | *"Each agent is stateless and single-purpose: it receives only the inputs listed in its contract (§10.1 table), and returns exactly one output object that must pass schema validation."* | §9 restates it: *"Context is passed only through saved, schema-validated records."* The database **is** the inter-step channel. There is no session, no conversation, no cache to fall back on. |
| **FR-I2** (§8.I) | *"Structured, schema-validated I/O between app and agents."* | Every persisted step output is a validated object, so it can be stored as JSON without a per-step table. |
| **§10 data model, v1.7 rows** | *"PipelineRun (user, role, current step, status: running / waiting-for-user / failed / complete)"* and *"StepRun (pipeline run, step #, agent name + version, model, input refs, output ref, validation result, retries, latency, cost). This is the audit trail from FR-I10."* | The two table names and their columns are **named by the PRD**. Note `output ref` here vs `output` in FR-I10 — see §7 Open questions. |
| **§10 data model, entity list** | *"User (auth, profile) · SkillProfile (demonstrated skills, evidence strength, source artifacts) · RoleBar · GapMap (user × role → prioritized, bucketed gaps) · AssessmentPlan → Topic (scope, why-it's-here, state: not-started / in-progress / passed / gap-open / skipped) · Exam → Question (MCQ/practical/open) + Rubric · Attempt (answers, scores, dimension breakdown, pass/fall-short) · Guidance (topic → what-to-learn + why; no lesson content) · Progress (topic states, streaks, readiness score)"* | The full entity list for [1]–[8]. Mapped in §2. |
| **§7.1** | *"onboarding is not done until 100% of the relevant, evidence-based career information is captured and the candidate has confirmed it … This confirmed profile is the single source of truth for every downstream stage."* and *"The pipeline does not move to step [2] until that confirmation is saved."* | The confirmation is a **persisted fact**, not a UI state. Downstream steps must be able to check it. |
| **§7.1** work-experience block | *"company, role/title, employment type, duration, team context (size, did you lead), domain"* | Field-for-field; Caliber's `work_experience` table matches exactly. |
| **§7.1** project block ("the heart") | *"name + summary; your role (built solo / led / contributed / owned); responsibilities; processes handled (design/review/deploy/on-call/agile); achievements/impact (quantified where possible); stack/tools used (languages, frameworks, tools, platforms, methods); scale & constraints; hardest problem solved (decision + why); optional demo/artifact link (manual, no repo connect)."* | Ten fields. Caliber's `project` table matches exactly, including `artifact_url` with a D1 comment forbidding server-side dereference. |
| **§7.1** signals + cross-check | *"depth score per skill (claimed vs evidenced), ownership level (contributor/owner/leader), recency, seniority signals"*; *"each claimed skill gets an evidence strength (none / mentioned / demonstrated / led). Claimed-but-weak → flagged probe area"* | Per-skill evidence strength and a `probe_first` flag are **stored**, not derived at read time (see the Caliber note in §2.2 — Caliber derives and rewrites them on every snapshot). |
| **FR-A5** (§8.A) | *"Output a normalized demonstrated-skills profile with per-skill evidence strength."* | Same. |
| **FR-C4** (§8.C) | *"Topic state machine: not-started / in-progress / passed / gap-open / skipped."* | Five states, exact names. §7.7: *"Skip is respected but honest — stays an open gap until demonstrated; never hidden."* So `skipped` is terminal-but-open, not a deletion. |
| **§7.7 / Appendix C** | Grade carries *"per-dimension score + specific gaps + evidence quotes"*; five dimensions 0–20 each; *"Verdict = pass if overall ≥ operational threshold, else gap. Operational threshold: ~70"* | The Grade record needs five numeric columns (or a JSONB with five keys), a total, a verdict, gaps and quotes. |
| **§7.7** | *"Guidance works only from the saved grade record."* (and *"The Evaluator and the Guidance Agent never see each other's prompts and never exchange messages."*) | The grade must be **readable back** as a first-class record, not reconstructed from a trace row. |
| **§7.7 / FR-D5** | *"the app runs the Question Generator ([5]) again, passing the IDs of earlier questions so it produces a fresh variant"*; *"fresh question variants every attempt"* | Question **IDs** are persisted per topic and queryable. |
| **§7.8 / D2** | *"Visual topic map — every topic and its state"*; *"'% ready for [role] at [level]' … (Computed in app code, not by an agent — D2)"*; *"Next best action … taken from the latest Adaptation output."* | Topic state is stored; readiness is computed; the latest Adaptation output is stored and addressable as "latest". |
| **§7.2 / D7** | Target role + level, optional pasted JD. | `target_role`, `target_level`, `jd_text` on the run/profile. |
| **§7.3** | *"The Role-Bar … a structured, **versioned** definition"*; *"Versioned — the bar drifts"* | Every gap-map/plan/fit output must carry the bar version it was computed under. |
| **§11 Architecture** | *"Backend: FastAPI (Python), **Postgres**."* … *"Infra: founder's Azure … **object storage for artifacts**."* | Postgres is the PRD's database. Artifacts (resume files) live in object storage, **not** in the database. |
| **§12 S0 row** | *"Pipeline runner + PipelineRun/StepRun tables (v1.7 addition)"* | The two tables are S0 infrastructure — they precede every domain entity. |

### 1.2 Things the PRD only implies (do not treat these as requirements)

- **"Input refs" implies content-addressing.** §10 says StepRun holds *"input refs, output ref"* while
  FR-I10 says *"input reference, output"*. The PRD never says whether the output is stored inline or
  behind a pointer. Both readings are available; the POC stores it inline today.
- **Attempt history implies an append-only table.** FR-D5's "fresh variants per attempt" and §7.7's
  "repeats until passed" imply attempts accumulate rather than overwrite, but the PRD never says it.
- **§14 risk row** — *"any step can be re-run on its own from saved inputs"* — implies **saved inputs**,
  a phrase FR-I8 does not use. This is the strongest PRD hint that a step's logical inputs are
  persisted separately from the previous step's output.
- **Cost roll-ups.** §14's *"Cost per user (LLM heavy)"* mitigation and §13's metrics imply per-run and
  per-workload cost queries, but no PRD line requires the aggregation.
- **§7.10 Phase 2** is the **only** PRD sentence that touches data protection at all:
  *"Opt-in, anonymized for the aggregate model."* It is about the Phase-2 outcome loop and is out of
  POC scope (RULEBOOK §17).

### 1.3 What the PRD does **not** specify (say "not specified", do not invent)

- **Retention.** No retention period, no deletion policy, no account-deletion cascade, no
  data-processing disclosure. Nothing. (Caliber tracks this as `ARC-18`, unbuilt — see §4.)
- **PII handling in the audit trail.** The PRD names `output` as an audit-record field (FR-I10) and
  never says whether that output may contain the candidate's own words. It does.
- **Encryption at rest, column-level or otherwise.** Not specified.
- **Retry/timeout budgets.** Appendix F, open: *"Retry policy defaults: confirm max retries per step,
  and the timeout / latency budget per step and per full run."*
- **Pipeline persistence mechanism.** Appendix F, open: *"Pipeline framework: custom runner in FastAPI
  vs a workflow engine (e.g. a durable task queue). Decide before S1."*
- **Postgres version.** The PRD's §12 S0 row says **"Postgres 17/pgvector"**. The POC is targeting
  **Postgres 18**. That is a deliberate POC choice, not a PRD requirement.

---

## 2. The entity list

Staging is by **pipeline step**, which is what makes implementation orderable.
"Now" = pipeline steps **[1] Profiler, [2] Role Analyst, [3] Gap Analyst** — the next three build
steps (RULEBOOK §15 steps 4 and 5). "Later" = steps [4]–[8].

### 2.1 Needed now — the pipeline spine

#### `pipeline_run` — one row per run (exists today as `runs`)

PRD §10: *"PipelineRun (user, role, current step, status: running / waiting-for-user / failed / complete)"*.

| Column | Type | Source | Note |
|---|---|---|---|
| `run_id` | `uuid` PK | POC `runs.run_id` | POC generates `uuid4().hex` client-side today. |
| `created_at`, `updated_at` | `timestamptz NOT NULL` | POC | `created_at DEFAULT now()`; Caliber pattern `server_default=func.now()` / `onupdate=func.now()`. |
| `status` | `text NOT NULL` | POC (`running` / `waiting` / `done` / `failed`) | **Naming mismatch:** PRD says `running / waiting-for-user / failed / complete`. POC says `running / waiting / done / failed`. Pick one and record the choice; the PRD's `waiting-for-user` is the more legible of the two. |
| `current_step` | `smallint NULL` | POC | The step number in flight or paused at. |
| `waiting_for` | `text NULL` | POC | Checkpoint key (FR-I11). Non-null exactly when `status='waiting'`. |
| `failed_reason` | `text NULL` | POC | FR-I9's "recoverable error" text. |
| `target_role` | `text NULL` | PRD §10 ("role"), §7.2; Caliber `candidate_profile.target_role` | Needed from step [2]. Nullable until the role-pick checkpoint. |
| `target_level` | `text NULL` | PRD §7.2; Caliber `candidate_profile.target_level` | |
| `confirmed_profile_sha256` | `char(64) NULL` | `SEQUENCING.md` §8: *"`PipelineRun` stores a sha256 of the confirmed profile; downstream steps refuse to run unless confirmed; an edit un-confirms"*; Caliber `confirmation.content_fingerprint()` | **Recommended now.** Caliber stores this inside `candidate_profile.confirmed_snapshot` JSONB as `content_sha256`. The POC has no profile table, so the run is the right home. |
| `confirmed_at` | `timestamptz NULL` | Caliber `candidate_profile.confirmed_at`; PRD §7.1 | |
| `candidate_ref` | `text NULL` | PRD §10 ("user") | **Open** — the POC has no auth (RULEBOOK §17). Recommend a nullable opaque label, not a FK. |

Written by: the runner, at run creation and on every status change.

#### `step_run` — one row per **attempt** (exists today as `step_runs`)

PRD §10: *"StepRun (pipeline run, step #, agent name + version, model, input refs, output ref, validation result, retries, latency, cost)."*
RULEBOOK §4 rule 6 and the POC docstring: *"one row per ATTEMPT at a step, including the ones that failed."*

Columns today (`store.py`): `id`, `run_id`, `step`, `step_key`, `attempt`, `status`, `started_at`,
`finished_at`, `agent`, `prompt_version`, `prompt_sha256`, `model_requested`, `cw`, `subtype`,
`salvaged_from`, `session_id`, `latency_ms`, `input_tokens`, `output_tokens`, `total_cost_usd`,
`error_kind`, `problems`, `meta`, `output`. Unique on `(run_id, step, attempt)`.

**Changes the move should make:**

1. `finished_at` becomes **nullable**, and `status` gains **`running`**. RULEBOOK §4 rule 9 says
   *"Record before you call. A `StepRun` row (status `running`) is written *before* the agent call
   and updated after, in its own transaction — a failed or dying step is recorded, never lost
   (Caliber lesson: a rolled-back request took the trace with it)."* `SEQUENCING.md` §6 trap 2 is the
   same lesson from the real incident. **The code does not do this today** — `runner.run_step()`
   calls `store.record_attempt()` only after `step.execute()` returns or raises. Flagged, not fixed.
2. Add `model_served` alongside `model_requested`. `observability.md` §8.2 Model truth:
   *"requested model · served `response.model` (echoed, normalized) … a provider that echoes a
   different model must be caught, not trusted"*. `CallMeta.models_served` already collects it.
3. Add `output_sha256 char(64)` — see §5.1 for why a hash over JSONB is not the same thing as a hash
   over the bytes that were inserted, and why the hash must be computed before the insert.
4. Add `input_sha256 char(64)` — `CallMeta.input_sha256` exists but is buried in `meta` JSON.
   FR-I10 names "input reference" as a first-class audit field.
5. `total_cost_usd` becomes `numeric(12,6)` — see §5.5.
6. `problems`, `meta`, `output` become `jsonb`.

#### `checkpoint_decision` — the candidate's answers at pauses (exists today as `checkpoints`)

FR-I11's five checkpoints: profile confirm, role pick, plan view, answer submit, retry.
Today: `(run_id, key)` PK, `decided_at`, `payload`. `store.decide()` uses `INSERT OR REPLACE` and
`clear_decision()` deletes — **so a re-armed checkpoint loses the previous answer**. That is correct
for the Profiler completeness *loop* (`repeat_after`), and questionable for an audit trail. See §7.

#### `run_input` — **new; the POC is missing it**

`runner.run_pipeline()` reads completed step outputs back from the store, but step [1]'s own inputs —
`resume_text`, `answers`, `today` — come from the caller-supplied `state` dict, which lives only in
memory. A resume in a fresh process therefore requires the caller to re-supply the resume text.
FR-I8's *"any single step can be re-run on its own"* and §14's *"re-run on its own from saved inputs"*
are not satisfied by the current schema.

Recommended shape: `run_id` FK, `kind` (`resume_text` / `answers` / `jd_text` / `target_role`),
`payload jsonb`, `payload_sha256`, `created_at`. Append-only, so a re-run after new answers is a new
row and the old input is still readable. **PII warning:** this table holds the candidate's own words
(see §4.3).

#### `resume_artifact` — the uploaded file's pointer (Caliber's name and shape)

Needed now only if the POC persists uploads. Caliber's columns (`domain.py`): `id`, `profile_id`,
`created_at`, `filename VARCHAR(400)`, `content_type VARCHAR(120)`, `byte_size`, `sha256 (indexed)`,
`storage_key VARCHAR(500)`, `parsed_ok bool`, `parse_error text`, `extracted_chars int`.
The **bytes live behind the storage interface, never in the database** (§11 PRD; `storage.py`).
See §4.2 for the two-phase design and delete-after-commit.

#### Not a table: the role bar

`ARITHMETIC_RULES.md` §7: *"Active bar is **named in config**, never discovered from the filesystem
(a draft can't start serving by accident)."* Caliber has **no** `role_bar` table — the bar is
versioned YAML under `rolebars/`. The POC does the same (`data/rolebars/`, RULEBOOK §5 D9/FR-I5).
The PRD lists `RoleBar` as a §10 entity; the repo does not implement it as one. **Both shown; the
repo's choice is the one the POC already follows.**

### 2.2 Needed now — the profile, if it is to be rows rather than JSON

The POC currently stores the whole `CandidateProfile` as JSON in `step_runs.output` and revives it
with `CandidateProfile.model_validate`. Caliber stores it as six normalised tables. The decision is
genuinely open (§7); here is what Caliber's shape is, so it can be adopted verbatim if chosen.

| Table | Purpose | Key fields (exact Caliber names) | Written by |
|---|---|---|---|
| `candidate_profile` | Onboarding state + target role. One per user. | `state` (signed_up/capturing/review/confirmed), `capture_path` (resume/guided), `target_role`, `target_level`, `years_experience`, `jd_text`, `jd_source_url`, `confirmed_at`, `confirmed_snapshot jsonb`, `resume_filename`, `resume_text`, `resume_reviewed_at`, `dismissed_duplicate_pairs jsonb` | [1] |
| `work_experience` | §7.1 per-company block | `profile_id`, `sort_order`, `company`, `title`, `employment_type`, `start_date`, `end_date` (null ⇒ current), `is_current`, `team_size`, `did_you_lead`, `domain` | [1] |
| `project` | §7.1 "the heart" | `experience_id`, `sort_order`, `name`, `summary`, `your_role`, `responsibilities`, `processes jsonb`, `impact`, `stack jsonb`, `scale_constraints`, `hardest_problem`, `artifact_url` | [1] |
| `education` | §7.1 academics; *"NOT part of the gate"* | `profile_id`, `institution`, `qualification`, `field_of_study`, `end_year` | [1] |
| `skill_claim` | §7.1 cross-check | `profile_id`, `skill`, `evidence_strength`, `evidence_project_count`, `probe_first`; `UNIQUE (profile_id, skill)` | [1] |
| `skill_evidence` | Which project supports which skill, and how strongly | `skill_claim_id`, `project_id`, `contributed_strength`, `reason VARCHAR(300)`; `UNIQUE (skill_claim_id, project_id)` | [1] |

Caliber's own note on `skill_evidence`: *"Derived, not authored: rebuilt from project evidence on
every snapshot, for the same reason `evidence_strength` is never typed by the candidate."*
And on `skill_claim.evidence_project_count`: a count alone *"cannot answer the question the
cross-check depends on: which work supports this, and how strongly?"*

### 2.3 Later — steps [4]–[8]

| Entity | PRD source | Step that writes it | Notes |
|---|---|---|---|
| `gap_map` / `gap_row` | §10 *"GapMap (user × role → prioritized, bucketed gaps)"*; §7.3 | [3] | **CONFLICT.** `ARITHMETIC_RULES.md` §4: *"Gap maps are recomputed per request, **never stored**."* The PRD lists GapMap as an entity; Caliber deliberately does not persist it. Both shown. If stored, each row needs `sub_skill`, `required`, `demonstrated`, `gap_size`, `priority`, `bucket`, `reason`, `source_ref` (`role@version#sub_skill`), plus `scoring_version`, `bar_version`, `bar_is_placeholder`. |
| `assessment_plan` | §10, §7.4, FR-C1 | [4] | `ARITHMETIC_RULES.md` §5: stamped `generated_by = "arithmetic"`, `question_mix` counts probe types. |
| `topic` | §10 *"AssessmentPlan → Topic (scope, why-it's-here, state…)"*; FR-C4 | [4] writes; [6]/[8] advance `state` | Fields per `ARITHMETIC_RULES.md` §5: `key = topic.{sub_skill}`, `order`, `title`, `competency`, `bucket`, `probes`, `why`, `source_ref`, `gap_ref`, required/demonstrated labels, `priority`, `state = not_started`. **`state` is the only mutable column and the one FR-C4 names.** |
| `question_set` / `question` | §10 *"Exam → Question (MCQ/practical/open) + Rubric"*; §7.5 7-probe set | [5] | IDs must survive: §7.7 re-runs [5] *"passing the IDs of earlier questions"*. Also holds the reference answer and grading notes (RULEBOOK §7 CW-9). |
| `attempt` | §10 *"Attempt (answers, scores, dimension breakdown, pass/fall-short)"* | app (answer checkpoint) + [6] | One per candidate answer. Append-only; a retry is a new attempt on the same topic. |
| `grade` | Appendix C; §7.7 *"Guidance works only from the saved grade record"* | [6] | Five dimension scores (0–20), `total`, `verdict` (pass/gap), gaps, evidence quotes, `rubric_version`. **Never cached** (ADR-0005). |
| `guidance` | §10 *"Guidance (topic → what-to-learn + why; no lesson content)"*; FR-C3/E1 | [7] | Must record that the D8 no-teaching code check passed. |
| `adaptation` | §7.5, §7.8 *"Next best action … taken from the latest Adaptation output"* | [8] | The chosen move plus the menu it was chosen from (RULEBOOK §7: menu-only). |
| `progress` / readiness | §10 *"Progress (topic states, streaks, readiness score)"*; D2 | app code | **Recommend: do not store.** Readiness is a pure function of topic states and bar weights (RULEBOOK §9), and D2 says it is computed in app code. Storing it creates a second truth that can disagree with the topic rows. Topic state is the stored fact; readiness is the view. |
| `outcome` | §10 *"(Phase 2) Outcome"*; §7.10 | — | **Out of scope** (RULEBOOK §17). |

---

## 3. Caliber's trace/audit row, field by field

### 3.1 As built: `agent_call` (`D:\Caliber\api\src\caliber\models.py`)

> *"One row per LLM call. The local replacement for Langfuse tracing."* — and the module docstring:
> *"Every LLM call writes exactly one row: prompt, context, model, tokens, cost, latency, outcome.
> This is what makes agent behaviour auditable without a hosted trace UI."*

| Column | Type | Nullable | Purpose (from the repo's own comments) |
|---|---|---|---|
| `id` | `UUID(as_uuid=True)` PK, `default=uuid.uuid4` | no | |
| `created_at` | `DateTime(timezone=True)`, `server_default=now()` | no | Indexed. |
| `agent` | `String(64)` | no | Indexed. Agent name. |
| `provider` | `String(32)` | no | Which provider served it. |
| `model` | `String(64)` | no | The model **as echoed by the provider** (`resp.model`), not the one requested. |
| `effort` | `String(16)` | yes | |
| `served_from` | `String(16)` | no | `provider` \| `cache_exact` \| `fake` — *"distinguishes a real billed call from a replay. The S0 gate asserts on this field."* |
| `outcome` | `String(16)` | no | `ok` \| `error`. |
| `cw` | `String(16)` | yes | Indexed. Workload tag (`cw-1`, `cw-3`). *"Nullable: rows from before `b7e2c4d1a9f3` have neither, and null says so honestly."* |
| `prompt_version` | `String(64)` | yes | Which prompt file. |
| `prompt_hash` | `String(64)` | yes | *"the sha256 of exactly what the model saw"* (AGT-06). |
| `request_hash` | `String(64)` | no | Indexed. sha256 over `{agent, provider, model, prompt, system, effort, json_schema, cw}` — the cache key and the trace/file reconciliation key. |
| **`prompt`** | `Text` | **no** | **The full rendered user prompt.** |
| `context` | `JSONB` | yes | `{cw, agent, …}` — the request context dict. |
| **`response`** | `Text` | yes | **The model's full reply text.** |
| `error` | `Text` | yes | Clipped to 2000 chars at the call site. |
| `input_tokens` | `Integer`, default 0 | no | |
| `output_tokens` | `Integer`, default 0 | no | |
| `cost_usd` | `Float`, default 0.0 | no | |
| `latency_ms` | `Integer`, default 0 | no | |

Indexes: `created_at`, `request_hash`, `agent`, `cw`.

Two operational notes from `tracing.py` that shaped the columns:

- **Every string is clipped to its column width before insert** (`_clip`), because
  *"a trace row is diagnostic; it may lose precision, never a user's work"* — a
  `StringDataRightTruncation` on the caller's session would deactivate their transaction and turn a
  trace failure into a lost resume upload. The narrow `VARCHAR`s are therefore a liability the code
  has to defend against.
- **Two sinks, one truth:** every record is written to `agent_call` **and** to
  `logs/agent-YYYY-MM-DD.jsonl`, both carrying the same `request_hash` so they can be reconciled.
  The file sink keeps the prompt too.

### 3.2 As specified but **not** built: `observability.md` §8.2

The design doc asks for more than the table has. Fields specified and missing from `agent_call`:

- Identity: **trace/request id**, **session/user ref (pseudonymous)**.
- Model truth: served model **normalized** (the column stores the raw echo).
- Prompt provenance: **rubric version** (judge).
- Generation: **effort known-honored flag** (*"Traces must not imply an effort that wasn't served"*),
  **thinking mode**, **schema id**.
- Usage: **cached tokens**; *"Unknown model ⇒ `unknown_model_for_pricing` warning, never silent $0"*.
- Outcome: **`stop_reason`**, **`stop_details`** (refusals), **validator results** (quote-check,
  numbers-verbatim, canon∈candidates), **error class (A/B/C/D + transport)**.
- Integrity: **response fingerprint (hash of normalized output)** — *"Silent-update defense"*.

### 3.3 `CallMeta` (`app/agents/base.py`) vs `agent_call`

**What the POC has that Caliber does not** (all of it comes from reading the SDK's message stream and
`ResultMessage`, which Caliber's provider layer has no equivalent of):

| `CallMeta` field | Why it matters |
|---|---|
| `session_id` | SDK session id per attempt; RULEBOOK §3.3 "audit replay". |
| `subtype`, `is_error`, `stop_reason`, `terminal_reason` | `stop_reason` is explicitly asked for by `observability.md` §8.2 and by `SEQUENCING.md` §6 trap 5 — Caliber's table does not have it. |
| `num_turns`, `duration_api_ms` | |
| `cache_read_tokens`, `cache_creation_tokens` | §8.2 asks for cached tokens; `agent_call` has only input/output. |
| `models_served` | The normalized served-model list §8.2 asks for. |
| `permission_denials`, `errors`, `api_error_status` | |
| `tools_called`, `structured_output_called` | Proves the structured-output tool was actually used. |
| `assistant_text_chars`, `thinking_blocks`, `thinking_chars` | Counts only — D8 forbids keeping thinking text. |
| **`salvaged_from`** | RULEBOOK §16.2. The error subtype a paid result was rescued from. Nothing in Caliber corresponds; Caliber has no salvage concept. |
| `input_sha256` | Hash of the rendered user prompt. Caliber's `request_hash` is broader (covers model/schema/cw too) and is used as a **cache key**, which the POC has no use for. |
| `effort` | Both have it. |
| `started_at`, `latency_ms`, `prompt_version`, `prompt_sha256`, `agent`, `cw`, `model_requested`, token counts, `total_cost_usd` | Both have equivalents. |

**What Caliber has that the POC does not:**

| `agent_call` column | POC status | Recommendation |
|---|---|---|
| `provider` | absent | Add as a constant (`claude_agent_sdk`). Cheap, and it future-proofs a second transport. |
| `served_from` | absent | **Add.** The POC's analogue is `provider` \| `salvaged` \| `fake` (the offline tests' `FakeQuery`). Caliber's S0 gate asserts on this field precisely so a fixture reply cannot be mistaken for a billed call — the POC has the same hazard with 590 offline tests. |
| `outcome` (`ok`/`error`) | partly — `step_runs.status` carries `ok`/`salvaged`/`failed` | Keep the POC's three-valued version; it is strictly more informative. |
| `request_hash` | absent (`input_sha256` is narrower) | Optional. Only earns its place if the POC ever caches, which ADR-0005 makes undesirable for grading anyway. |
| **`prompt`** (full text) | **deliberately absent** | **Do not add.** RULEBOOK §11. See §4.1. |
| **`response`** (full text) | **deliberately absent** | **Do not add.** |
| `context` JSONB | partly — the POC's `meta` JSONB is the nearest thing | Fine as is. |
| `error` Text | partly — `error_kind` + `problems[]` | Keep the POC's structured version; it is what `observability.md` §8.2 asks for under "validator results" and "error class". |
| `model` (served) | absent (only `model_requested`) | **Add `model_served`**, populated from `models_served`. |
| response fingerprint | absent | **Add `output_sha256`.** §8.2 Integrity. Contains no PII. |
| `rubric_version`, `schema_id` | absent | Add when [6] Evaluator lands. |

---

## 4. Retention and PII rules

### 4.1 The POC's rule, and the conflict with the real repo

**POC (RULEBOOK §11):** *"**Counts only.** The model's prose is quoted in the exception a developer
reads, never in the record; thinking text is never kept at all (D8). **Never** log candidate PII or
full prompts at info level — store hashes and versions."*
The code enforces it: `MAX_MODEL_TEXT_CHARS = 300` prose excerpts go into *exceptions*, never into
`CallMeta`; `_read_blocks()` counts thinking blocks and characters and discards the text; the
`StructuredOutput` payloads are held in a local list and never written to `meta`.

**Caliber's design doc agrees** (`observability.md` §8.5): *"Structured events only; **never** full
prompt contents at info level, never credentials, never candidate PII in logs. Traces store prompt
*hashes* + versions; the rendered prompt is reconstructible from the versioned prompt registry +
recorded inputs (which live in the DB under the app's own PII rules, not in logs)."*

**Caliber's code does not.** `agent_call.prompt` is `Text NOT NULL` and `_record()` passes
`prompt=req.prompt` — the fully rendered prompt including the fenced resume text — plus
`response=r.text`, the model's whole reply. Both are also appended to `logs/agent-YYYY-MM-DD.jsonl`.
The file sink's own comment concedes it: *"Prompts can be large; the file sink keeps them, the DB
sink keeps them too, and a retention job trims both before any hosted deploy."* **That retention job
is `ARC-18`, and it is unbuilt.**

> **Verdict for the POC:** keep §11. Do not copy `prompt` or `response`. Where §8.5 says the prompt is
> *"reconstructible from the versioned prompt registry + recorded inputs"*, the POC already has both
> halves: `prompts/<agent>.vN.md` is immutable and hashed, and `run_input` (§2.1) would hold the
> inputs. Reconstructability is the right property; retention of the rendered text is not.

### 4.2 What Caliber does about resume files specifically

**Two-phase upload/extract (ADR-0014).** One endpoint became two:

| | |
|---|---|
| `POST /profile/resume` | *"Reads, validates, stores the bytes, extracts the text, supersedes any previous artifact. **No model call.** Returns the snapshot."* |
| `POST /profile/resume/parse` | *"Runs CW-1 over the `resume_text` the first call committed. Writes the structured rows."* |

Persistence consequences the ADR names:
- *"A failed parse no longer costs the upload. The text and artifact are already committed by the time
  the model is called."* — i.e. **the extracted text is committed before any token is spent.**
- *"Re-parsing with a better model or a fixed prompt becomes a single call against stored text."*
- *"Re-parse can now duplicate … The parse route therefore **clears the rows it owns before writing**."*
  Pinned by `test_parsing_twice_replaces_rather_than_duplicates`.
- A new legitimate intermediate state exists: *"text stored, nothing parsed."*

**Artifact storage, keyed by sha256** (`storage.py`):
- Bytes never enter the database. `LocalArtifactStore.put()` writes
  `storage/resumes/{profile_id}/{sha256[:12]}-{safe_filename}`; the digest prefix
  *"keeps two uploads of different files with the same name from colliding, without inventing a
  second id."* The row (`resume_artifact`) carries `sha256`, `storage_key`, `byte_size`,
  `content_type`, `parsed_ok`, `parse_error`, `extracted_chars`.
- Keys are **relative and opaque**: *"The root moves; the key must not."* `path_for()` resolves and
  asserts containment so the class cannot become a file-read primitive.
- `_safe_name()` strips anything that could escape the root — a candidate controls the filename, and
  *"a filename of `../../.env` writes outside the root"*.
- `get_store()` refuses loudly if `STORAGE_BACKEND != local`: *"Silently falling back to local storage
  in a hosted environment would scatter PII across container filesystems."*

**Delete-after-commit (ARC-18).** This is the pattern worth copying verbatim:

> *"Bytes must not outlive their database pointer — and must not predecease it either. Deleting a file
> inside the request looks right and is not: the endpoint can still fail AFTER the unlink … the
> transaction rolls back, and the row that pointed at the file comes back — now pointing at nothing.
> Observed exactly that way."*

`delete_after_commit(session, keys)` queues keys on `session.info`; a SQLAlchemy `after_commit`
listener drains the queue; `after_rollback` **and** `after_soft_rollback` discard it. The soft variant
exists because a session that queued deletions without ever beginning a real transaction would
otherwise have its queue drained by the *next* commit — *"a different unit of work, maybe a different
request"* — deleting files whose rows still exist. Caught by `test_rollback_keeps_the_bytes`.

**What Caliber admits is still broken** (`resume_artifact` docstring and `OPEN-WORK.md`):
- *"The FK cascade means deleting a profile deletes the pointer — it does NOT delete the file, which is
  why ARC-18 is still open."*
- `OPEN-WORK.md` D12: *"'Exactly one artifact per profile' is a comment, not a constraint. Only a
  non-unique index exists … Two concurrent uploads against a profile with no existing artifact both
  insert — two retained resumes, **the PII outcome ARC-18 exists to prevent**. A `UNIQUE (profile_id)`
  would make it true."*
- `OPEN-WORK.md` D11: `resume_filename` and `content_type` are written unclipped into
  `VARCHAR(400)`/`VARCHAR(120)` on the upload path — *"A long filename or a crafted `Content-Type`
  header 500s the request after the bytes are on disk — an orphaned file."*
- `BACKLOG.md` ARC-18: *"PII policy, retention, account-deletion cascade and third-party processing
  disclosure"* — size **L**, priority **high**, **not built**.

### 4.3 Rules for the POC — the honest version

1. **The audit columns stay hash-only.** No `prompt`, no `response`, no thinking text, no model prose.
   This is RULEBOOK §11 and it is already true of `CallMeta`.
2. **`step_run.output` is not covered by that rule, and pretending otherwise would be dishonest.**
   FR-I8 *requires* the step's output to be saved, and step [1]'s output is a `CandidateProfile` —
   which contains verbatim quotes from the candidate's resume, because "grounded or dropped"
   (RULEBOOK §5) requires them. The schema therefore has **two zones**, and they should be documented
   as such:
   - *Audit zone* — every promoted column on `step_run` plus `meta`: hashes, versions, counts, ids.
     Safe to keep, safe to export, safe to log at debug.
   - *Payload zone* — `step_run.output`, `run_input.payload`, `checkpoint_decision.payload`, and any
     profile tables: **candidate data**. Never logged, never exported, subject to whatever retention
     rule the POC states.
3. **Do not store resume bytes or `resume_text` in Postgres.** Caliber stores `resume_text` on
   `candidate_profile`; the POC does not have to. Recommend: extracted text stays in
   `runs/private/` (already git-ignored per RULEBOOK §16.2) and the database keeps only
   `sha256`, `byte_size`, `extracted_chars`, `pages`, `layout`, `parsed_ok`, `parse_error`. That
   satisfies FR-I8 resume (the text is addressable) without putting a career in the audit database.
   **Open** — see §7.
4. **HUM-3 stands:** synthetic data only in the repo. The one real resume used on 2026-09-21 lives in
   `runs/private/`, git-ignored (RULEBOOK §16.2).
5. **A retention rule must be written down, because neither the PRD nor Caliber has one.** The
   simplest defensible POC rule: a run's payload zone is deletable by `run_id`, and deleting a run
   cascades to `step_run`, `checkpoint_decision` and `run_input`. Caliber's whole ARC-18 problem is
   that the file deletion does *not* cascade; the POC can avoid inheriting it by not storing files.

---

## 5. Postgres-specific decisions, with recommendations

### 5.1 JSONB vs TEXT for the step output and the audit blob

**Recommendation: `jsonb` for `step_run.output`, `step_run.meta`, `step_run.problems`,
`checkpoint_decision.payload`, `run_input.payload`.**

Why:
- It is what Caliber does everywhere it stores a document: `agent_call.context`,
  `job_run.payload`/`result`, `candidate_profile.confirmed_snapshot`,
  `candidate_profile.dismissed_duplicate_pairs`, `project.processes`, `project.stack`.
- Malformed JSON is rejected **at insert**, not at read. With `TEXT`, a serialisation bug surfaces
  three days later when a resume tries to revive the row.
- It is queryable without application code: `output->>'fit_label'`,
  `meta->>'salvaged_from' IS NOT NULL`, `jsonb_array_length(problems)`. The POC's demo (`step3_demo.py
  --runs`) and any future FastAPI listing want exactly these.
- GIN indexing is available later if a query needs it (do not add one now — see §5.6).

**The one real trap, and it is load-bearing:** `jsonb` does **not** preserve key order, does not keep
duplicate keys, and normalises numeric formatting. So `sha256(row.output::text)` read back from the
database is **not** the same string as `sha256(json.dumps(output))` computed in Python.
Therefore: **compute `output_sha256` and `confirmed_profile_sha256` in Python over the canonical
serialisation before the insert, store them in their own `char(64)` columns, and never recompute them
from the JSONB.** (Caliber does the same thing for the same reason — `confirmation.content_fingerprint()`
hashes a Python-built blob and stores the digest in `confirmed_snapshot`, rather than hashing the
JSONB column.)

Use `json` (not `jsonb`) only if byte-exact round-tripping is ever required. It is not, if the hash
columns above exist.

### 5.2 Native enum types vs CHECK constraints vs plain text

**Recommendation: `text` + a named `CHECK` constraint for closed, slow-moving vocabularies; bare
`text` for vocabularies the POC does not own.**

Caliber's position, stated on `UserEntitlement.feature`:
> *"Stored as text, not a DB enum: the set is expected to grow with the product, and an `ALTER TYPE`
> per addition buys nothing when the application validates the value on the way in anyway."*

Caliber uses `String(n)` with **no** CHECK at all, relying entirely on `enums.py` + application
validation. That is one step looser than recommended here.

Why not native `CREATE TYPE ... AS ENUM`:
- A value can be added (`ALTER TYPE ... ADD VALUE`) but **cannot be removed or reordered** without
  recreating the type and rewriting every dependent column. Every vocabulary below has changed at
  least once during this POC (`salvaged` was added to the attempt statuses on 2026-09-21).
- The SDK owns some of these vocabularies. `step_run.subtype` and `error_kind` carry values invented
  by `claude-agent-sdk` (`error_max_budget_usd`, `error_max_structured_output_retries`, …). A native
  enum or a CHECK there would turn an SDK upgrade into a failed insert — exactly the failure mode
  `tracing.py`'s `_clip` exists to avoid.

Per column:

| Column | Recommendation | Reason |
|---|---|---|
| `pipeline_run.status` | `text` + `CHECK (status IN ('running','waiting','done','failed'))` | Four values, ours, named by the PRD, and an invalid one silently breaks resume. |
| `step_run.status` | `text` + `CHECK (... IN ('running','ok','salvaged','failed'))` | Add `running` per §2.1. |
| `topic.state` (later) | `text` + `CHECK` on FR-C4's five values | FR-C4 names them exactly; a typo here loses a gap. |
| `grade.verdict` (later) | `text` + `CHECK (verdict IN ('pass','gap'))` | |
| `step_run.subtype`, `error_kind` | bare `text` | The SDK owns the vocabulary. |
| `step_run.salvaged_from` | bare `text` | Same — it is an SDK subtype. |
| `served_from` | `text` + `CHECK (... IN ('provider','salvaged','fake'))` | This is the field the S0 gate asserts on; a wrong value means a fixture reply is counted as billed. |

Name every constraint explicitly (`ck_step_run_status`), so a migration can drop and re-add it.

### 5.3 Timestamp type

**Recommendation: `timestamptz` on every timestamp column, no exceptions.**

- `timestamp without time zone` stores no offset, and Postgres will interpret and render it in
  whatever the session's `TimeZone` happens to be. The POC writes `datetime.now(timezone.utc)`; a
  `timestamp` column would silently discard the fact that it was UTC and the demo on this Windows box
  would read back local time.
- Caliber uses `DateTime(timezone=True)` on **every** timestamp column in `models.py` and `domain.py`,
  with `server_default=func.now()` and `onupdate=func.now()`. Copy that.
- The POC currently stores **ISO-8601 strings** (`_now()` returns
  `datetime.now(timezone.utc).isoformat(timespec="seconds")`). Moving to `timestamptz` is what makes
  `ORDER BY created_at`, `finished_at - started_at`, and any "runs in the last hour" query correct
  rather than lexicographically lucky.
- Use `DEFAULT now()` for `created_at`. Note `now()` is *transaction start* time — if per-statement
  precision inside one transaction ever matters, `clock_timestamp()` is the one to use. It does not
  matter here (one row per attempt, one transaction per attempt).
- Keep `started_at` / `finished_at` written by the application, not by `now()`: they bracket the agent
  call, not the transaction, and after the §2.1 change the insert and the update are two transactions.

### 5.4 Primary keys

**Recommendation:**

| Table | Key | Reason |
|---|---|---|
| `pipeline_run` | `uuid` PK, generated in the application | A run id is handed to a CLI user, appears in a URL, and must exist **before** the insert (the POC already does `uuid4().hex`). Caliber uses `UUID(as_uuid=True), default=uuid.uuid4` on every table. Store it as a real `uuid` column, not `text` — 16 bytes vs 32, and it validates. |
| `step_run` | `bigint GENERATED ALWAYS AS IDENTITY` | High-volume, insert-ordered, never exposed outside the process. Use `GENERATED ALWAYS AS IDENTITY` rather than `bigserial`: `serial` is legacy syntax that creates a separately-owned sequence with permission and ownership quirks. Keep the real key as the existing `UNIQUE (run_id, step, attempt)`. |
| `checkpoint_decision` | composite `(run_id, key)` — as today | It is genuinely one decision per checkpoint per run. If history is wanted (§7), this becomes an identity PK plus an index. |
| `run_input` | `bigint IDENTITY` | Append-only. |
| Later domain tables | `uuid`, matching Caliber | So the shapes can be lifted from `domain.py` unchanged. |

**Postgres 18 note:** PG18 ships built-in `uuidv7()` alongside `uuidv4()`. A time-ordered v7 key gives
better B-tree locality than v4 for high-insert tables. At POC volumes (tens of runs, hundreds of
attempts) this is worth nothing, and it would move id generation from the application into the
database, which the CLI needs not to happen for `run_id`. **Recommendation: stay with
application-generated uuid4 for `run_id`; verify `uuidv7()` exists on the installed build before
relying on it anywhere.**

### 5.5 Money and counters

**`total_cost_usd` should be `numeric(12,6)`, not `real`/`double precision`.**
`Store.cost()` does `SUM(total_cost_usd)` across every attempt of a run, failures included, and
RULEBOOK §16.2's whole finding was a $0.1107 run measured against a $0.10 ceiling — a comparison that
floating-point summation can get wrong at exactly the boundary that matters. Caliber uses `Float`; the
POC uses `REAL`. This is a small, concrete improvement worth taking on the move.

Token counts: `integer` is fine (the largest observed is 18,191 output tokens). `latency_ms`:
`integer`. Make them `NOT NULL DEFAULT 0` only if a missing value and a zero mean the same thing —
they do not here (a transport failure has no token count), so **leave them nullable**, unlike Caliber
which defaults them to 0 and thereby cannot distinguish "free" from "unknown".

### 5.6 Indexes the queries we actually run will need

Derived from the four read paths in `store.py` and the two in `runner.py`:

| Query | Where | Index |
|---|---|---|
| `attempts(run_id)` / `completed(run_id)` — every attempt of a run, ordered | `run_pipeline()` resume, `run_step()` | `(run_id, step, attempt)` — **exists today**, keep it. |
| `next_attempt(run_id, step)` — `MAX(attempt)` | every attempt | Same index, backward scan. No second index needed. |
| `cost(run_id)` — `SUM(total_cost_usd)` | demo / reporting | Same index; add `INCLUDE (total_cost_usd)` only if an index-only scan is ever wanted. Not now. |
| `list_runs()` — `ORDER BY created_at DESC` | `step3_demo.py --runs` | `ix_pipeline_run_created_at (created_at DESC)`. Caliber has the equivalent on both its tables. |
| "which runs are waiting?" | any CLI/API that resumes | Partial: `CREATE INDEX ... ON pipeline_run (updated_at) WHERE status = 'waiting'`. Caliber uses the same partial-index technique on `gap_relevance_rating` (`postgresql_where=text("bar_is_placeholder = false")`). |
| per-workload cost roll-up | RULEBOOK §10 / `observability.md` §8.3 | `ix_step_run_cw (cw)`. This is Caliber's stated reason for `ix_agent_call_cw`: *"the per-workload cost roll-up is the query that reads it."* |
| `decided(run_id, key)` | every checkpoint check | Covered by the composite PK. |
| FK columns | | Index every FK (`step_run.run_id` is already the index prefix; `run_input.run_id` needs its own). Caliber indexes every FK explicitly. |

**Do not add a GIN index on `output` or `meta` yet.** A GIN index on a JSONB column that is only ever
fetched by primary key is pure write amplification. Add it the day a query filters on a JSON key.

### 5.7 pgvector

**Recommendation: no. Do not install it.**

1. **Nothing in POC scope embeds anything.** The role bar is a small YAML file loaded whole
   (`ARITHMETIC_RULES.md` §7: *"Active bar is named in config"*), matching is normalised
   string/alias comparison (`app/textmatch.py`, `ARITHMETIC_RULES.md` §4: *"skill names and bar
   aliases normalised to `[a-z0-9]`"*), and grounding is a **verbatim substring check**
   (RULEBOOK §13). Similarity search would actively break "grounded or dropped".
2. **Caliber installs it and does not use it.** `0001_baseline.py` runs
   `CREATE EXTENSION IF NOT EXISTS vector` and `main.py` health-checks it, but **no column anywhere is
   a vector**. ADR-0005 moved the semantic cache to pgvector; `llm/runtime.py` then says plainly:
   *"There is no semantic cache."* `barcoverage.py` line 130 marks the embeddings work (`EMB-1`) as
   unbuilt.
3. **The one place the POC might be tempted is forbidden anyway.** ADR-0005: *"The judge/grading route
   is excluded from semantic caching in code — two paraphrased answers are not the same answer; a
   cache hit would return someone else's score. This is a correctness rule, not a performance tuning
   choice."*

An extension no column uses is a deployment dependency bought for nothing.

### 5.8 Two more decisions worth making explicitly

- **Migrations.** Caliber uses Alembic (`api/alembic/`, 10 revisions) with a `db.ps1 drift` check that
  compares models to migrations. The POC has **no ORM** by design (`store.py`: *"One connection, no
  ORM"*). Recommendation: plain numbered `.sql` files plus a `schema_migrations` table, applied by a
  small script — Alembic's value is autogenerate-from-models, which a no-ORM project cannot use.
  Not specified anywhere; flagged in §7.
- **Transaction boundary per attempt.** After the §2.1 change there are two writes per attempt
  (insert `running`, update to terminal). They must be **two transactions**, not one — that is the
  entire point of `SEQUENCING.md` §6 trap 2: *"the trace row for a completed model call must not
  depend on the request's transaction surviving (write it in its own transaction / savepoint)."*

---

## 6. What we should deliberately NOT copy from Caliber

| Not copied | Reason |
|---|---|
| **Redis / ARQ job transport and the `job_run` table** | ADR-0005 exists because Memurai Developer *"self-terminates at 10 days"* and *"anything durable that lived only in Redis would eventually vanish"*. The POC runs the pipeline in-process, synchronously, with no queue — so `job_run` would record nothing `pipeline_run` does not. **Copy the lesson, not the table:** `SEQUENCING.md` §8 already translates it — *"`StepRun.status ∈ queued / running / succeeded / failed` + `attempts`"* — and `ARITHMETIC_RULES.md` §8 notes Caliber has *"No step tables"* at all. |
| **`agent_call.prompt` and `agent_call.response`** | RULEBOOK §11. Full prompt text = the candidate's resume; full response = the model's prose. Caliber's own `observability.md` §8.5 forbids this and its code does it anyway. See §4.1. |
| **The JSONL file sink (`logs/agent-YYYY-MM-DD.jsonl`)** | Same reason — it keeps the prompts too. The POC's step_run row is the single sink. |
| **Exact-response caching keyed on `request_hash`** | Out of POC scope, and ADR-0005's never-cache-grades rule would have to be reimplemented to make it safe. The POC's cost control is `max_budget_usd`, not a cache. |
| **`app_user`** (`email`, `hashed_password`, `session_version`, `pending_email`, `password_changed_at`, `is_verified`) | RULEBOOK §17: *"Out: … auth"*. Also the highest-PII table in the schema. |
| **`user_entitlement` and `upgrade_interest`** | RULEBOOK §17: *"payments (paywall = flag)"*. The POC's paywall is a boolean on the plan-view checkpoint, per RULEBOOK §6. |
| **`gap_relevance_rating`** | A §13 product-metric instrument (*"user rates gap map + assessment plan 'accurate' ≥ 80%"*), not part of the [1]–[8] pipeline. |
| **`jd_source_url` and the JD-fetch path (ADR-0016)** | Server-side URL fetching; the JD overlay is marked "later" in RULEBOOK §9 and the fetch is not in §17's "In" list. |
| **`dismissed_duplicate_pairs` and duplicate-suspect detection** | Caliber's O12/dedup territory; RULEBOOK §16 O12 already decided the POC relies on near-duplicate demotion instead. |
| **pgvector / semantic cache / `EMB-1`** | §5.7. |
| **Azure Blob storage backend** | RULEBOOK §17: *"Out: … Azure"*. Local filesystem only. |
| **Phase 2 entities** — `Outcome`, Interviewer transcripts, content-to-hire analytics | RULEBOOK §17: *"Out: … Phase 2 (Interviewer, outcome loop)"*; PRD §7.9/§7.10. |
| **Narrow `VARCHAR(n)` on provider-supplied strings** | `tracing.py`'s `_clip` exists only because `model` is `String(64)` and a provider can echo a file path longer than that, and a truncation error *"would deactivate their transaction"*. Use unbounded `text` for anything the provider or the candidate supplies; Postgres stores short `text` and short `varchar` identically. |

### Conflicts found — flagged, not resolved (RULEBOOK is the main session's)

1. **RULEBOOK §17 lists Postgres as out of scope.** Verbatim: *"**Out:** … frontend, **Postgres**,
   Azure"*. RULEBOOK §16 O5 records *"Storage: SQLite in `runs/`"*, and §15 marks Step 3 done as
   *"Pipeline runner + SQLite"*. The task this spec was written for says the POC is moving to
   PostgreSQL 18. **These cannot both be current.** §17 and O5 need updating by whoever owns the
   RULEBOOK; this document assumes the move is real and says so here rather than editing it.
2. **`ARITHMETIC_RULES.md` §4 vs PRD §10 on the gap map.** *"Gap maps are recomputed per request,
   never stored"* vs the PRD listing `GapMap` as a §10 entity. Unresolved — see §2.3 and §7.
3. **RULEBOOK §4 rule 9 vs the POC's own code.** Rule 9 requires the `step_run` row to be written with
   status `running` **before** the agent call; `runner.run_step()` writes only after. The schema
   change (§2.1) is a precondition for fixing it, but the fix is a code change this spec does not make.
4. **`observability.md` §8.5 vs `models.py`/`tracing.py`** on storing prompts. Documented in §4.1.
5. **PRD §12 says Postgres 17, POC targets 18.** Noted; no requirement depends on the difference.

---

## 7. Open questions

Listed plainly. None of these could be settled from the documents.

1. **Does the POC keep SQLite as the test backend?** The 590 offline tests run against
   `Store.in_memory()` (`sqlite3.connect(":memory:")`). Moving to Postgres either (a) requires a live
   Postgres for the test suite, (b) requires `Store` to support two dialects — and `INSERT OR REPLACE`
   in `decide()` is already SQLite-only syntax (`ON CONFLICT ... DO UPDATE` in Postgres) — or (c)
   means the tests stop covering the store. **This is the largest practical consequence of the move
   and nothing in the sources addresses it.**
2. **Inline output or content-addressed reference?** FR-I10 says *"output"*; §10 says *"output ref"*.
   The POC stores it inline. Not specified which the PRD means.
3. **Is the profile rows or JSON?** Caliber normalises it into six tables (`candidate_profile`,
   `work_experience`, `project`, `education`, `skill_claim`, `skill_evidence`); the POC stores the
   whole `CandidateProfile` as JSON on `step_runs.output`. Rows are needed the moment the candidate
   can *edit* the profile at the confirm checkpoint (PRD §7.1 *"review-and-confirm screen
   (edit/correct)"*); JSON is enough if the POC's confirm is accept-or-re-answer. **Not decided.**
4. **Is the gap map stored or recomputed?** PRD entity vs `ARITHMETIC_RULES.md` §4. If recomputed,
   the bar version and scoring version must be pinned somewhere so an old run reproduces.
5. **Does `resume_text` go in the database?** Caliber stores it on `candidate_profile`; RULEBOOK §11
   argues against. §4.3 recommends keeping it out and storing only hashes and counts, but the
   recommendation is this document's, not a source's.
6. **Retention period.** Nothing in the PRD. Caliber's ARC-18 is unbuilt. How long does a POC run's
   payload zone live, and is there a `DELETE FROM pipeline_run WHERE ...` path at all?
7. **Does `checkpoint_decision` need history?** Today `store.decide()` replaces and
   `clear_decision()` deletes, so the Profiler's completeness loop erases the previous round's
   answers. FR-I11 does not say whether the decisions themselves are auditable.
8. **Is there a user/candidate dimension at all?** PRD §10 gives PipelineRun a `user`. The POC has no
   auth. A nullable `candidate_ref` is proposed in §2.1; nothing requires it.
9. **Migration tooling.** Alembic (Caliber's choice, ORM-driven) vs plain numbered SQL (fits the POC's
   no-ORM store). Not specified anywhere.
10. **Timeout and latency budgets per step and per run.** PRD Appendix F, explicitly open.
11. **Does a salvaged attempt count against the retry budget?** Settled in code (`run_step()` returns
    immediately on a salvaged result; RULEBOOK §4.3 *"A salvaged result is never re-run"*), but the
    schema has no column expressing it — `attempt` just increments. Fine today; worth naming if
    per-step retry analytics are ever wanted.
12. **What is the "input reference" for a step whose input is another step's output?**
    `CallMeta.input_sha256` hashes the *rendered prompt*, not the step's logical input. So
    "re-run any step alone" (FR-I8) currently means "re-run it from the prior steps' saved outputs
    plus caller-supplied state", not "re-run it from a recorded input". `run_input` (§2.1) closes half
    of this; the other half — a per-step `input_ref` — is undecided.
