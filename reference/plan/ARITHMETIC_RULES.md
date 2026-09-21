# Caliber's deterministic layer — rules and constants (as built)

> Extracted 2026-09-18 from `D:\Caliber\api\src\caliber\` (policy, completeness, textquality, signals, confirmation,
> onboarding, reparse, gapmap, plan, role_fit, rolebar, enums, domain, models) — **facts, not code**. Paths below
> are relative to that folder. This is what the real app computes *without* a model ("arithmetic owns dated facts").
> The POC may simplify; where it does, `RULEBOOK.md` records the POC choice.

---

## 0. Policy constants (`policy.py`, `POLICY_VERSION = "s1.2"`)

Every tunable number lives in one file; changing any value bumps the version, which is stamped on every completeness report and confirmed snapshot.

| Constant | Value | Used for |
|---|---|---|
| `W_CRITICAL` / `W_CORE` / `W_SUPPORTING` | 3 / 2 / 1 | completeness item weights |
| `RECENT_WINDOW_MONTHS` | 36 | recency: recent vs dated |
| `SIZABLE_TEAM` | 6 | cross-team seniority signal |
| `STRONG_MIN_COUNT`, `STRONG_MIN_RATIO` | 2, 0.5 | seniority "strong" tier |
| `DEFENDED_MIN_WORDS` | 20 | "ambiguity/defended" signal |
| `CREDIT_GRANULARITY` | 3 | completeness units per weight |
| `EDUCATION_FULL_WEIGHT_YEARS` | 5 | education counts (weight 1) only below 5 years |
| `DEPTH_BASE` | none 0 · mentioned 20 · demonstrated 55 · led 75 | depth score |
| `DEPTH_CORROBORATION_STEP` / `_CAP` | 8 / 16 | depth score |
| `DEPTH_MENTION_STEP` / `_CAP` | 2 / 4 | depth score |
| `DEPTH_QUANTIFIED_BONUS` | 5 | depth score |
| `DEPTH_RECENCY_ADJ` | current +4 · recent 0 · dated −12 · unknown −6 | depth score |
| `CLAIM_CHECK_MAX_CALLS` | 24 | LLM claim checks per run, strongest claims first |
| `YEARS_TOLERANCE`, `YEARS_TOLERANCE_RATIO` | 2.0, 0.25 | years mismatch flag: `|claimed − computed| > max(2.0, 0.25 × claimed)` |
| `GAP_MONTHS` | 6 | timeline-gap flag |
| `TITLE_RANKS` | 0 intern/trainee/apprentice · 1 junior/associate/graduate/assistant · **2 default** · 3 senior/sr · 4 staff/principal/lead/architect · 5 head/director/vp/chief/founder | trajectory |
| Text-quality | `MIN_WORDS_ANY=3`, `WORDLIKE_NOISE_RATIO=0.34`, `WORDLIKE_THIN_RATIO=0.5`, `BIGRAM_HIT_MIN=0.40`, `BIGRAM_MIN_ALPHA=12`, `REPEAT_RUN_LIMIT=4`, `NEAR_DUP_JACCARD=0.80` | text tiers |

**Field specs** (text fields a candidate writes):

| field | min_words | min_chars | specificity | echo tokens (restating the question) |
|---|---|---|---|---|
| summary | 6 | 20 | — | project, summary, about, the, this |
| responsibilities | 6 | 20 | — | responsible, responsibilities, duties, for, my, i, was |
| impact | 5 | 15 | **quantified** | impact, achievements, achievement, results, changed, the |
| hardest_problem | 8 | 25 | **decision** | hardest, hard, problem, solved, call, decision, the, i |
| scale_constraints | 4 | 10 | — | scale, constraints, constraint, big, the |

---

## 1. Profile state machine (onboarding)

**States:** `signed_up` → `capturing` → `review` → `confirmed`.

| Transition | Trigger |
|---|---|
| signed_up → capturing | at least one experience exists |
| capturing → review | completeness `is_complete` |
| any → **confirmed** | only `POST /profile/confirm`: re-derives skills, recomputes completeness **on the server**, 409 `incomplete_profile` unless complete. Stores `confirmed_at` + `confirmed_snapshot {percent, total_weight, counts, policy_version, content_sha256}`. Message: *"We now have a complete picture of what you've done"* |
| confirmed → review / capturing | **any content edit** changes the fingerprint → confirmation no longer stands (review if still complete, else capturing) |
| confirmed → review / capturing | explicit `POST /profile/reopen` (idempotent) |

- Transitions are evaluated lazily on every read, in this order: re-derive skills → completeness → state rules.
- **Fingerprint** = sha256 of canonical JSON over target role/level, years, JD text, experiences (company, title, type, dates, current, team, lead, domain) and projects (name, summary, role, responsibilities, processes, impact, stack, scale, hardest problem, link), educations. Excludes derived skills, ids and timestamps.
- **Freeze semantics:** a matching fingerprint stands even if the policy later tightens (a policy change never un-confirms an untouched profile); a changed fingerprint never stands, even if still complete.
- **Refused while confirmed:** resume upload and resume parse (409 + a "reopen" link). Ordinary edits are allowed but invalidate the confirmation.
- **Downstream gate:** gap map, assessment plan and relevance ratings return 409 unless `state == confirmed` ("Confirm your career picture first").

**Re-parse = merge, never replace:** match rows by normalised (company, title) / (project name) / (institution, qualification), one-for-one, no fuzzy matching. A parse may fill only blank fields (experience: type, domain, dates · project: summary, stack · education: end year); existing values always win; nothing is deleted. A fresh parse resets "reviewed" (a new suggestion must be reviewed again).

---

## 2. Completeness gate

| Level | Item | Weight | Satisfied when |
|---|---|---|---|
| profile | target_role | 3 | ≥2 chars and not gibberish |
| profile | target_level | 2 | set |
| profile | years | 2 | set |
| profile | has_experience | 3 | ≥1 experience |
| experience | dates | 2 | start set, and current or end set |
| experience | employment_type | 1 | set |
| experience | team_context | 1 | team size or "did you lead" set |
| experience | domain | 1 | set |
| experience | has_project | 3 | ≥1 project |
| experience | identity *(only when failing)* | 2 | company and title ≥2 chars |
| project | summary | 2 | text tier ≥ substantive |
| project | your_role | 2 | one of built_solo / led / contributed / owned |
| project | responsibilities | 2 | tier ≥ substantive |
| project | **impact** | **3** | tier ≥ substantive (specific = quantified) |
| project | **hardest_problem** | **3** | tier ≥ substantive (specific = decision) |
| project | stack | 2 | ≥1 non-vague entry |
| project | scale | 1 | tier ≥ substantive |
| project | processes | 1 | ≥1 entry |

- **Units:** each item is worth `weight × 3`. Booleans: all or nothing. Text: empty/noise 0 · thin `weight×1` · substantive `weight×2` (if a specific tier is still available) else `weight×3` · specific `weight×3`.
- **Gate = every item satisfied** (text needs ≥ substantive). **Percent** = floor(got × 100 / total), **capped at 99 while anything is open**. The gate reads `is_complete`, never the percent.
- **Nudges** = open items sorted by (−weight, location, label); text: empty → the item's prompt · noise → "That doesn't read as a real answer — …" · thin → the reason.
- Non-gating refinements: "quantify your impact", "name the decision", and education (only when years < 5).

**Text-quality ladder:** empty < noise < thin < substantive < specific.
1. empty: blank.
2. noise: no tokens, a character repeated ≥4 times, word-like ratio < 0.34, or (≥12 letters and common-bigram rate < 0.40).
3. noise: fewer than 3 words.
4. thin: under the field's min words / chars.
5. thin (`echo`): mostly restates the question.
6. thin (`gibberish`): word-like ratio < 0.5.
7. specific: impact has a number/currency/"doubled"/"million"… (`quantified`); hardest problem has a decision word — chose, decided, opted, went with, instead of, rather than, trade-off, vs, rejected, ruled out, weighed (`decision`), plus a `causal` flag for because / so that / to avoid / the risk was …
8. A later project field ≥80% token-similar (Jaccard) to an earlier one is demoted to thin (`duplicate`).

---

## 3. Evidence ladder and signals

**Per project → one strength for every skill in its stack:**
- `has_depth` = responsibilities ≥ substantive **and** impact ≥ substantive
- `has_hard_call` = hardest problem is *specific* (a decision is named)
- `leads` = role ∈ {led, owned, built_solo}
- **led** = leads + depth + hard call · **demonstrated** = depth · **mentioned** = otherwise ("named in the stack only")
- **probe_first** = leads **and not** a hard call (claims ownership without showing a decision); sticky across projects.

**Per skill:** strongest source wins; vague terms skipped; skill key = whitespace-collapsed lowercase.

**LLM claim check (CW-4) is demote-only:** `new = min(derived, max(verdict, mentioned))` — can never raise, never below mentioned; only demonstrated/led sources are checked (≤24, strongest first); a demotion sets `probe_first`.

**Recency:** current if any contributing role is current; else by the latest real end date: ≤36 months recent, else dated; no end date → unknown.

**Depth score (0–100, display only — never used in gap size):** `base[strength] + min(16, 8 × (deep sources − 1)) + min(4, 2 × extra mentions) + 5 if quantified + recency adjustment`.

**Ownership level:** leader (led a role/project) › owner (owned/built solo) › contributor.

**Seniority signals** (none / some / strong; strong = ≥2 and ≥50%): scope (scale described) · tradeoffs (hardest problem specific) · ambiguity/defended (specific + causal + ≥20 words) · cross-team (led a team or team ≥6). Near-duplicate answers count once.

**Trajectory:** needs ≥2 dated roles; "growing" if title rank rose, project ownership rose, or team grew; else "steady".

**Consistency flags (never gate):** years mismatch (tolerance above) · timeline gap > 6 months · "led without a team" (team < 2).

**Duplicates:** same company (legal suffixes stripped, one name a prefix of the other) + overlapping dates (undated overlaps everything).

**Vague terms:** "cloud", "various tools", "technologies", "frameworks", "devops", "analytics", "automation", anything with "etc"/"misc"/"and more"… → never a skill; they trigger CW-3 clarify.

---

## 4. Gap map

- **Level from years only** (bands: junior 0 · mid 2 · senior 5 · staff 9 · principal 14); clamped to the bar's supported levels (mid/senior/staff) with a visible flag.
- **Refusals:** no years → no level → empty map; target role not matched by the bar → empty map ("no bar for your role"), never another role's gaps.
- **Matching:** skill names and bar aliases normalised to `[a-z0-9]`; strongest-evidence alias hit wins.
- Per sub-skill: `required = depth[level]` (0 → out of scope) · `demonstrated` = evidence rank (none 0 … led 3; 4 only after passing an assessment) · `gap = max(0, required − demonstrated)`.
- **Bucket precedence:** landscape (only if gap > 0) → probe_first → **claimed_but_unproven** (even at gap 0) → gap 0 → **proven** (listed separately) → tier (author override or required depth: 3–4 must_know · 2 should_know · 1 optional).
- `priority = round(gap × weight/5 × recency_factor, 2)`, recency factor current/recent 1.00 · dated 1.25 · unknown 1.10 · no evidence 1.00.
- **Order:** claimed-but-unproven by evidence desc; then priority desc → weight desc → bar order. Display: must_know, should_know, claimed_but_unproven, optional, ai_landscape. **Headline = must_know + claimed_but_unproven.**
- `assessment_only` = required 4. `source_ref = role@version#sub_skill`.
- **Depth words:** 0 "nothing captured" · 1 "aware of it" · 2 "can build with it" · 3 "can design with it" · 4 "can defend it under load".
- **Reason templates (deterministic, always present):**
  - claimed_but_unproven: *"You list '{x}', but the projects behind it do not yet show it. The assessment probes this first."*
  - landscape: *"The market now expects awareness here. The bar wants {want}; your captured work shows {have}."*
  - nothing shown: *"Nothing in your captured work covers this. At your level the bar wants {want}."*
  - depth 4: *"Your work shows {have}. The bar wants {want} — which capture alone cannot prove, so this is settled in the assessment."*
  - otherwise: *"Your work shows {have}; at your level the bar wants {want}."*
- Also returns unmatched candidate skills, `scoring_version`, `bar_version`, `bar_is_placeholder`. **Gap maps are recomputed per request, never stored.**

---

## 5. Assessment plan (arithmetic version)

- **One topic per gap row, in gap-map order** (proven rows skipped and counted).
- Topic fields: `key = topic.{sub_skill}`, order, title, competency, bucket, probes (from `how_tested`: multiple choice / practical exercise / open-ended scenario), why, source_ref, gap_ref, required/demonstrated labels, priority, **`state = not_started`** (nothing advances it yet).
- **"Why" templates:** claimed → *"…This topic checks whether it holds up — which is why it comes early."* · nothing shown → *"Nothing in your captured work covers this, and at your level the bar expects {r}."* · depth 4 → *"…Going beyond that means defending it under load, which capture cannot settle — this topic is where that happens."* · otherwise → *"Your work shows {d}; this topic is where it is pushed to {r}."*
- Stamped `generated_by = "arithmetic"` so it is never mistaken for an agent-built plan. `question_mix` counts probe types.

---

## 6. Fit labels

- Over sub-skills with 0 < required < 4 that were measured: `coverage = Σ weight × min(shown, required) / Σ weight × required` (3 dp).
- Required-4 rows are excluded from the ratio; any unproven one **caps the label at Stretch**.
- **Strong fit:** coverage ≥ 0.85 **and** no must_know gap **and** not capped · **Stretch:** ≥ 0.55 · **Not yet:** below. No fourth label.
- **No label at all** when the bar is for another role (`no_bar_for_role`) or years are unknown (`no_calibration_level`).
- **Direction:** overshoot (target above calibrated) / undersell (below) / aligned; never when the level was clamped.
- **Reach:** a second fit at the target level if the bar supports it. `compare_levels` over sub-skills in scope at both levels: Δ > 0.01 "closer", < −0.01 "further", else "about the same" — computed in code and handed to the narrative, never inferred by the model.

---

## 7. Role bar loading

- Active bar is **named in config**, never discovered from the filesystem (a draft can't start serving by accident).
- Schema: schema_version, role_key, display_name, version, status (draft / in_review / published / retired / placeholder; not published ⇒ placeholder), supported_levels, role_aliases, competencies → sub_skills {key, name, weight (default 3), how_tested, aliases, depth {level: 0–4}, optional tier}, landscape items.
- Validation: tier ∈ {must_know, should_know, optional}; depth 0–4; unique keys; supported levels exist.
- **Role match:** lowercase, split, drop level words (junior, jr, mid, senior, sr, staff, principal, lead, head), join; match against aliases + display name.

---

## 8. Persistence patterns (for our PipelineRun / StepRun)

- **`agent_call`** (one row per LLM call): agent, provider, model, effort, served_from, outcome, **cw**, **prompt_version**, **prompt_hash**, request_hash, prompt, context, response, error, input/output tokens, cost_usd, latency_ms, created_at.
- **`job_run`** (Postgres is the record, the queue is only transport): job_type, **status queued / running / succeeded / failed / cancelled**, payload, result, error, **attempts**, created/updated. No step tables.
- **Versioning pattern worth copying:** every computed output carries the version of the rules it was computed under (`policy_version`, `scoring_version`, `bar_version`, `prompt_version` + hash) **plus a fingerprint of its input**.

---

## 9. Sequence rules encoded in the app

1. Every read: derive skills → completeness → state rules → derived outputs (ambiguities, duplicates, seniority, trajectory, ownership).
2. Resume path: **upload** (deterministic extraction, no model) → **parse** (separate, retryable request) → **review** → pick target → capture depth → **confirm**.
3. Confirm re-checks completeness on the server.
4. Gap map, plan and fit all require `confirmed`; plan is built from the gap map; fit from gap map + bar.
5. No years → no level → no rows → no topics → no label.
6. Depth 4 is earned only by passing an assessment topic; until then it stays a gap and caps fit at Stretch.
7. The LLM claim check runs **after** the arithmetic and may only lower ratings.
8. A confirmed profile can't be rewritten by a side effect (upload/parse need an explicit reopen); edits invalidate the confirmation.
