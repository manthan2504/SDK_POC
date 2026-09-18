# §10 — Development-Cycle Plan: Claude-Only (LOCKED 2026-09-02 · mapping researched v2, 2026-09-02)

**User decision (2026-09-02): for this development cycle, Caliber uses Anthropic/Claude
models exclusively — authenticated through the Claude OAuth profile, no API keys, no
non-Anthropic calls — with the OpenClaw gateway as the Claude-model switching layer
(ADR-0012).** This file is the operative model plan. Model Mapping v2 (`models.md` §3,
ADR-0009) remains the locked *destination*; its cross-vendor pieces are deferred, not
deleted. v2 of this file incorporates two in-depth research passes with same-day
primary-source verification (`research/p4_claude_premium.md`, `p4_claude_volume.md`).

## 10.1 Decision effects (amended by ADR-0012)

| Item | Status |
|---|---|
| OpenClaw gateway | **IN the runtime path as Claude-model mux** — set up 2026-09-02 (`docs/RUNBOOK-openclaw.md`): `caliber-mux` agent live, `/v1/responses` enabled + auth-verified, token wired into `.env`. Backend model = safe `pending/awaiting-D1` placeholder — no call can fall through to the subscription runtime |
| D1 (credential inside gateway) | **LIVE, ON HOLD** — the one gateway activation step left |
| D2 (judge transport) | LIVE — direct SDK proposed (gateway drops `effort` today) |
| D4 (PII through gateway) | LIVE — decide before resume text transits it |
| D5, R1 (Terra), R3 (Sol/Terra) | Deferred with the cross-vendor destination |
| R2 (MiniCheck) | Deferred (non-Claude); CW-4 compensates (§10.4) |
| Live provider today | `LLM_PROVIDER=anthropic` (direct SDK); `openclaw` is one `.env` flip once D1 + conformance land |
| **Interim local provider (ADR-0015, 2026-09-03)** | **BUILT and proven live** (`api/STATUS.md` §22): `LLM_PROVIDER=local` → llama-server + Qwen3.5-4B/2B/Granite-H-Micro, schema-constrained via the OpenAI-compatible surface (never `/v1/messages` — it has no structured output and needs the banned `ANTHROPIC_BASE_URL`). Dev iteration on CW-1/2/3/6/7/10/15/22/OPS-1 only; never judge/tone/authoring; gates nothing (FR-I4). Not the default — `.env` still says `anthropic` |

## 10.2 Auth — unchanged

`ant auth login` Console OAuth profile (ADR-0003), active and verified live 2026-09-02.
Claude Code's own credential is a different store the SDK cannot use; subscription OAuth
is banned for app traffic. Usage meters per token — the single remaining unblock for real
calls is **Console credits**.

## 10.3 The fleet — verified 2026-09-02 (deprecations/pricing pages fetched same day)

| Model | Price /MTok | Floor | Verdict |
|---|---|---|---|
| `claude-opus-5` | $5 / $25 | Jul 24, 2027 | **S1.** Dominates Opus 4.8's cost frontier at every effort (Opus-5-low ≈ Opus-4.8-max measured) |
| `claude-sonnet-5` | $2 / $10 (**permanent** — Sep-1 rise cancelled) | Jun 30, 2027 | **S2.** Best MASK honesty (3.1%); tone-bound work stays barred pending its own eval (mixed sycophancy evidence). New tokenizer: ~1.3× tokens |
| `claude-haiku-4-5` | $1 / $5 | **Oct 15, 2026 floor — verified; no notice, no successor announced** | **S3.** Cheapest, fastest (TTFT ~0.77s), old tokenizer, `temperature` still accepted, NO effort param. Nearest lifecycle cliff in the fleet |
| `claude-opus-4-8` | $5 / $25 | May 28, 2027 | Not assigned — class-A within-family fallback reference only (dominated by Opus 5) |
| `claude-sonnet-4-6` | $3 / $15 | Feb 17, 2027 | **Excluded** — dominated even after tokenizer adjustment |
| `claude-fable-5` / **`fable-5-1` (NEW Sep 1)** | $10 / $50 | Jun 9 / Sep 1, 2027 | **Disqualified, re-verified**: 5.1 is still a Covered Model — 30-day retention, no ZDR. Cheaper cache reads change nothing for PII posture |
| local `bge-small-en-v1.5` | free | — | EMB-1 (pending R7) — Anthropic has no embeddings endpoint |

API facts that moved since the September-1 lock: **structured outputs are GA on every
current model via constrained decoding** (schema validity is grammar-enforced; the model
choice moves content quality only) · citations remain incompatible with
`output_config.format` (400) — CW-4's two-pass design stays forced · **`max` effort is
officially warned against for structured-output tasks** ("overthinking") · a **per-message
effort beta** (Opus 5) changes effort mid-conversation *without* cache invalidation —
eval-design input that may obsolete the judge's dedicated xhigh cache lane · Priority Tier
is no longer purchasable (moot for us).

## 10.4 Workload → model mapping (Claude-only, researched; ALL rows provisional until their FR-I4 eval)

Effort values marked † are pre-sweep hypotheses (the sweep discipline stands — and the
research adds: sweep the judge DOWN, `medium` may hold the SLO at a fraction of cost).

| CW | Assignment | Effort† | Checker (external-examiner, within family) | Conf | Research notes |
|---|---|---|---|---|---|
| CW-1 extraction | **Haiku 4.5** + strict/structured outputs | n/a | — (planted-absence eval is the check) | MED | Grammar-enforced JSON; eval measures nulls-over-guesses. Vision fallback: Sonnet 5 native-PDF |
| CW-2 elicitation | **Haiku 4.5** | n/a | — | MED | Escalation C: depth ≥6/stall → Sonnet-5-low fresh ctx |
| CW-3 skill normalize | **Haiku 4.5** constrained-select | n/a | canon∈candidates validator (code) | HIGH | Classification parity evidence |
| CW-4 claim verify | **Opus 5 verdict + Sonnet 5 citations pass** | high (verdict) | **Deterministic verbatim substring check** (in code — neutralizes Opus 5's flagged hallucination uptick). MiniCheck veto deferred ⇒ every "demonstrated" verdict gets an Opus 5 re-adjudication on fresh context | MED | Citations × structured-output 400 keeps two-pass forced |
| CW-5 fit/leveling narrative | **Opus 5** | med-high, never max | Human review until eval passes | **LOW-MED** | Opus 5 STILL has no public sycophancy number + documented **overconfidence** — the 990-case tone eval gains an overconfidence/calibration slice, both directions |
| CW-6 JD decompose | **Haiku 4.5** + coverage validator | n/a | Validator (code); shortfall → Sonnet-5-low | LOW-MED | Recall is where Haiku likeliest loses — seeded-JD eval decides |
| CW-7 gap prose | **Haiku 4.5** + numbers-verbatim validator | n/a | Validator (code) | MED | — |
| CW-8 plan construct | **Sonnet 5** (regen: Haiku) | med | Escalation: Opus 5 + scope-freeze | MED | — |
| CW-9 open QG + reference answers | **Opus 5** | high | **Sonnet 5 blind-solve, commit-first** + human SME gate | MED-HIGH | 8/8 benchmarks + human-graded Elo favor Opus for answer-quality |
| CW-10 MCQ | **Haiku 4.5** overgenerate-and-rank | n/a | **Opus-5-low blind key solve** | MED | Diversity via temperature works ONLY on Haiku — Sonnet fallback needs prompt-side diversity |
| CW-11 practical challenge | statement+solution **Opus 5 `xhigh`** (official coding guidance); harness **Haiku 4.5** execution-verified | split | Harness self-verifies (pass-ref/fail-mutant) | MED-HIGH | — |
| CW-12 variant equivalence | **Sonnet 5** contrast+filter | med | **Opus-5-low difficulty check** | MED | — |
| **CW-13 judge** | **Opus 5** — structured outputs + same-model multi-sample vote in borderline band (RuVerBench supports voting; cross-model ensembles stay banned) | **high, PINNED — never `max` (official overthinking warning); sweep incl. `medium` arm** | S4 audit deferred ⇒ weekly fixed-set regrade on **Sonnet 5** (weak canary, honestly labeled) + e-process anchors + human transcript review as primary audit | MED (judge), Hypothesis (per rule) | Sonnet-5-judge bake-off justified but burden on Sonnet; compare **$/graded-submission** (its tokenizer +30%). No public benchmark includes either model as judge — our gold set decides (which is FR-I4 anyway) |
| CW-14 guidance/hint | **Haiku 4.5** behind D8 checker | n/a | D8 answer-leakage eval is the gate — the one S3 row where a stronger model plausibly matters | **LOW** | D6-high escalation → Opus 5 (never Sonnet on tone) |
| CW-15 probes | **Haiku 4.5, thinking off** | n/a | Pre-authored bank fallback | **HIGH** | TTFT ~0.77s vs Sonnet's ~1.21s + thinking tail — latency verdict is clean |
| CW-16 interviewer (P2) | **Sonnet-5-low bake-off** vs Haiku+budget_tokens | — | Turn-summary ledger (class-D) | MED | No published 30–60-turn data for ANY model — our simulator is the only instrument |
| CW-17/18 bar+rubric authoring | **Opus 5** | high→xhigh, never max | Human-gated; citation capture stays prompt/tool-space | MED | — |
| CW-19 bar drift | **Sonnet 5** diff-shaped | med | Human gate | MED | — |
| CW-20 gold-set fakes | **Human-authored** (Phase 0A rule); Claude-generated only as flagged non-anchor augmentation | — | Human filter | — | Family-disjoint generation impossible in-fleet — unchanged |
| CW-21 review assist | **Sonnet 5** | med | Human primacy | LOW-MED | R4 still open |
| CW-22 outcome ingest (P2) | **Haiku 4.5 via Batch** ($0.50/$2.50) | n/a | Low-confidence → Sonnet 5 | HIGH | **Sonnet 5 batch = $1/$5 = Haiku live price** — a near-free upgrade lane if the F1 eval wants it |
| OPS-1 probe | **Haiku 4.5** through production path | n/a | — | HIGH | — |

## 10.5 Honest costs & compensations (unchanged in substance, sharpened by research)

1. **Family-preference bias in auditing** — human gold set + human transcript review carry
   the burden; anchors must include human-written and non-Claude text (anti-self-laundering
   is now load-bearing).
2. **Silent-update detection** — vendor-independent instruments (e-process anchors,
   response fingerprints, pinned IDs vs served echo) stay mandatory; public judge rankings
   are benchmark-unstable (rankings shift up to 14 positions), reinforcing own-gold-set
   primacy.
3. **Judge injection** — regression suite runs pre-release on every judge change.
4. **CW-5 blind spot widened**: no sycophancy number AND documented overconfidence — its
   eval gains a calibration slice before any user sees a narrative.

## 10.6 Operational flags from research (each actionable at build time)

1. **S3 fallback is a parameter TRANSLATION layer, not a model swap**: Haiku
   (`budget_tokens`, temperature OK, no effort) vs Sonnet 5 (adaptive + `effort:low`,
   temperature 400). The rehearsed class-D config encodes both shapes.
2. **Prompt-cache minimum is non-monotonic**: Haiku 4096 · Sonnet 5 1024 · Opus 5 512
   tokens. Audit every S3 shared prompt — under 4K it silently never caches on Haiku.
3. **Cost math correction**: Sonnet-5-low ≈ 2.5–3.5× Haiku per task (price × tokenizer ×
   thinking), not 2×; but the $3/$15 rise is cancelled, so the fallback is permanently
   cheaper than mid-2026 planning assumed.
4. **Haiku cliff watch**: floor Oct 15 (verified), 60-day notice policy, no successor —
   earliest practical retirement ~Nov 1. The class-D rehearsal (Sonnet-5-low arm on the S3
   gauntlet) discharges the obligation.
5. Per-message-effort beta may retire the judge's dedicated xhigh cache lane — test at
   eval design, don't assume.

## 10.7 What remains open

| # | Decision | Owner |
|---|---|---|
| D1 | Credential inside the gateway (Console key recommended) — the last gateway step | user |
| D2 | Judge bypasses gateway (recommended) vs accept-and-measure | user |
| D4 | Resume text through gateway transcripts vs parse skips gateway | user |
| R4 | CW-21 accept-or-commission | user |
| R5 | Whole-bar-in-context → ADR | user + architect |
| R6 | Inspect-AI vs hand-rolled harness → ADR | build-time |
| R7 | Keep local embeddings under "Claude-only" (recommended: keep) | user |

## 10.8 Ready state (what "setup complete" means, achieved 2026-09-02)

Provider spine built + tested (STATUS §16) · gateway configured with safe placeholder
(RUNBOOK-openclaw) · OAuth active · mapping researched and written (this file) · report
amended. **When credits land**: probe → S3 gauntlet → gold set → Phase 0A. When D1 lands:
gateway credential + repoint `caliber-mux` models + conformance test → `LLM_PROVIDER=openclaw`.
