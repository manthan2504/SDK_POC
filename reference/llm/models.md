# §3 — Model Policy (application-level system card)

> **⚠ Development cycle override (2026-09-02, ADR-0011 + ADR-0012):** the operative
> fleet is **Claude-only — S1/S2/S3 + local embeddings — behind the OpenClaw
> provider-mux** (direct SDK as standing fallback; judge transport = D2, open). This
> file remains the locked *destination* (incl. the S4 cross-vendor slot, deferred). For
> what actually runs now, read `dev-cycle.md` §10 first; where the two disagree, §10
> wins until the S4/D5 re-open trigger fires.

The fleet, what each model may and may not be asked to do, the API facts that constrain
them, and the monitoring each assignment commits to. Format: system card for *this
application* — per-capability assignment + known failure modes + monitoring commitments —
kept in sync with eval runs, not hand-maintained lore. Binding: ADR-0009; operational map:
`routing.py`.

Facts below verified 2026-09-01 (claude-api skill + six-researcher pool with two-auditor
check). Anything newer than that date is unverified by definition — re-check before relying.

## 3.1 The fleet

**Hard budget: 4 API models + 2 local.** Every extra model is a standing
eval/prompt/migration tax. A new slot requires workload evidence + eval suite + migration
owner in the same change (§2.7).

| Shelf | Model | Price in/out per MTok | Context | Role | Runway note |
|---|---|---|---|---|---|
| S1 | `claude-opus-5` | $5 / $25 | 1M | Judge (CW-13) + high-stakes authoring (CW-9/11/17/18) + tone-bound narrative (CW-5) | ≥ Jul 2027 |
| S2 | `claude-sonnet-5` | $2 / $10 (permanent — Sep-1 rise cancelled) | 1M | Everyday generation (CW-8/12/16-post-mortem/19/21), citations pass (CW-4) | ≥ Jun 2027 |
| S3 | `claude-haiku-4-5` | $1 / $5 | 200K | High-volume structured jobs (CW-1/2/3/6/7/10/14/15/22, OPS-1) | **Retirement floor Oct 15 → class-D bake-off mandatory (§3.6)** |
| S4 | `gemini-3.7-flash` *(provisional)* | $1.50 / $7.50 modeled post-Jan-1 | — | Cross-vendor auditor (§3.5) | Stable lifecycle; validated only by its own bake-off |
| local | `bge-small-en-v1.5` | free (CPU) | 384-d | EMB-1 embeddings | Challenger: `granite-embedding-small-english-r2` |
| local | MiniCheck-class verifier *(pending ratification)* | free (CPU) | — | CW-4 grounding veto | Eval + migration owner named in ADR-0009 |

## 3.2 API constraints that shape everything (Claude models)

| Constraint | Opus 5 | Sonnet 5 | Haiku 4.5 |
|---|---|---|---|
| `temperature` / `top_p` / `top_k` | **removed — 400** | **removed — 400** | accepted |
| `thinking: {type: "adaptive"}` | on by default (omit = adaptive); `disabled` only ≤ effort high | only on-mode | pre-4.6 style: `enabled` + `budget_tokens` |
| `budget_tokens` | **removed — 400** | **removed — 400** | required for thinking |
| `output_config.effort` | low/med/high/xhigh/max | low/med/high/xhigh/max | **errors — NEVER send** |
| Assistant prefill | **removed — 400** | **removed — 400** | — |
| Structured output | `output_config.format` / `messages.parse()` / strict tools (`strict: true` + `additionalProperties: false`) | same | same |
| Batch API | −50%, results keyed by `custom_id` | same | same |

Consequences the registry already encodes: grading stability is engineered, not sampled
(ADR-0007); **unset effort on 5-generation models means high** — an effort silently dropped
in transport (the OpenClaw gateway today, ADR-0010/D2) is a silent cost leak on cheap rows
and a silent max→high downgrade on the judge; **an effort change invalidates the prompt
cache** (the judge's xhigh re-sample lane carries its own cache prefix for this reason);
citations and structured outputs are mutually exclusive (400) — the fact that forced CW-4's
two-pass design.

## 3.3 Effort discipline

- Every default above `medium` requires a recorded low/med/high sweep before it locks
  (defaults in workloads.md §2 are pre-sweep hypotheses).
- The judge's effort is **high, pinned per session, versioned** — changing it forces a
  gold-set re-run.
- Effort is sent only where supported (never Haiku — the CW-14 escalation lane was
  re-pointed in audit partly because the old lane would have 400'd).

## 3.4 Known failure modes, per model per assignment (why the carve-outs exist)

| Model | Measured/known failure | Consequence in the mapping |
|---|---|---|
| Sonnet 5 | **9.1% sycophancy — worst-measured major**; flagged off-Pareto for backend coding | **Never tone-bound work.** CW-5 is S1; CW-14's D6-high escalation goes to S1, never S2 |
| Opus 5 | **No public sycophancy measurement** (excluded run) | CW-5 assignment is *conditional*; the 990-case tone eval is its gate |
| Haiku 4.5 | No effort param; 200K context | Never send effort; long-context rows stay off S3 |
| Gemini 3.7 Flash | **Unmeasured on tone and judging** (the 0.5%-sycophancy figure was 3.6 Flash — and achieved by hedging: 37.9% decisive) | S4 slot is provisional; validated only by the S4 gold-set bake-off; never a safety filter (near coin-flip under distribution shift) |
| Gemini 3.1 Pro | Best-measured **cross-vendor** judge (κ=0.898) but `-preview` lifecycle (2-week notice) | Bake-off instrument only; barred from standing duty until a stable ID ships (runway rule) |
| Any single-family panel | 9 same-family judges ≈ 2.18 effective votes; 3-family panel passed 55% of hacked answers | **No voting ensembles for the gate** — one strong judge + de-anchored S4 |

## 3.5 S4 — the cross-vendor auditor, precisely

- **Non-blocking in the grading-audit role**: re-scores a 5–10% weekly sample (batch) and
  regrades a fixed gold set — the silent-degradation canary. It alerts; it never gates.
- **Blocking only at authoring/library time**, where an independent second opinion is the
  point: CW-9 blind-answer check, CW-10 blind key check, CW-12 difficulty check (batchable).
- **Commit-first / blind-solve protocol mandatory everywhere** (answers before seeing the
  candidate's answer/key: FPR 0.719 → 0.012).
- May hold grade-of-record **only** after its own harshness offset is fitted; never doubles
  as a safety filter.
- Activation on real candidate content is gated by **D5** (cross-vendor retention/ZDR check
  + credential decision — safety.md §7.6). Synthetic-fixture work (HUM-3) is unaffected.

## 3.6 Bench, dormant, and disqualified

**Dormant alternates** (named, NOT in fleet; each needs ratification + D5 before first
use): GPT-5.6 Sol (S1 availability alternate — 3.0% sycophancy / 73.7% decisive; promo
$4/$20 ends Nov 21) · GPT-5.6 Terra (CW-9 refusal alternate; S2/CW-16 bake-off challenger;
**CW-20 offline fake-generation exception pending ratification**). Until ratified, S1
availability failures = retry/defer — never an out-of-fleet call.

**S3 class-D bake-off (before Oct 15, 2026 — mandatory):** GPT-5.6 Luna ($0.20/$1.20) vs
Gemini 3.7 Flash (post-promo $1.50/$7.50) vs Sonnet-5-low. Discharges class-D for every S3
row. Blast radius: CW-1/2/3/6/7/8-regen/10/14/15/16-screen/22, OPS-1, S3 fallbacks in
CW-12/19. Recorded dissent: one researcher reads retirement as successor-triggered, not
imminent — the stricter deadline stands (cheap bake-off, asymmetric downside). Terra/Luna
context/cutoff specs are family-assumed, unverified — **verify before either activates.**

**Disqualified** (with reasons, so nobody relitigates casually): Kimi K3 (no safety report,
AISI cyber failures) · Grok 4.6 (self-reported sycophancy/dishonesty regressions — fatal
judge-adjacent) · **Fable 5** (above budget $10/$50; mandatory 30-day retention, no ZDR —
fails PII posture) · Sonnet 4.5 (retires ~Sep 29 — standing veto) · Gemini 3.1 Flash Lite,
GLM-5.2 (budget; may enter the S3 bake-off) · DeepSeek (evidence-backed for deceptive fakes
but flag-don't-recommend — data handling).

## 3.7 Calendar (all dated obligations in one place)

| Date | Event | Action owed |
|---|---|---|
| ~Sep 29, 2026 | Sonnet 4.5 retires | Standing veto — nothing may depend on it |
| **Oct 15, 2026** | Haiku 4.5 retirement floor expires (60-day notice → earliest ~Nov 1) | **S3 class-D bake-off must have run** (§3.6) |
| Nov 21, 2026 | Sol promo pricing ends | Cost-model update (not a migration) |
| Jan 1, 2027 | Gemini 3.7 Flash price doubles | Already modeled post-promo; re-check S4 economics |
| watch | Gemini 3.1 Pro leaves Preview | May challenge for S4 (needs its own bake-off) |
| watch | Any Anthropic deprecation notice | Runway rule: <~9 months ⇒ named owner + rehearsed fallback |

## 3.8 Monitoring commitments (what this card promises observability.md delivers)

Per LLM call: pin-and-log served `response.model` + usage + `stop_details` + prompt hash +
effort (§8.2). Weekly: S4 sampled re-scores + fixed gold-set regrade. Continuous: anchor
interleave with e-process drift verdict {none/system/judge}; response fingerprints retained;
pinning verified (a "pinned" endpoint that auto-upgrades is a documented industry failure).
Every number in §3.1's price columns is exercised by `cost_usd` — an unknown model warns,
never silently prices at $0.
