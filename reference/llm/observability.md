> **POC copy — edited 2026-09-18.** Snapshot of the Caliber file with provider-gateway material removed; everything else is verbatim.

# §8 — Observability & Cost

The first-party trace sink (DEV-1: Langfuse deferred, interface kept) and what it must
capture for the AI layer's promises — drift attribution, cost truth, gray-failure
detection — to be keepable. Store: `agent_call` (Postgres) + structured JSON logs.

## 8.1 The principle

A model call that can't say *which prompt, which model, which effort, at what cost,
serving which workload* produced it is unusable for eval provenance, drift attribution,
or costing. Observability here is not debugging convenience — it is what makes FR-I4
auditable after the fact.

## 8.2 The `agent_call` record (per LLM call)

| Field group | Fields | Why |
|---|---|---|
| Identity | trace/request id · **`cw` workload tag** · agent name · session/user ref (pseudonymous) | Per-workload cost + eval attribution. Standing flag (§2.8): resume-parse and clarify both trace as `profiler` today — distinct `cw` tags required before more workloads ship |
| Model truth | requested model · **served `response.model` (echoed, normalized)** · provider · `served_from` (provider / cache_exact / cache_semantic) | Pin-and-log; a provider that echoes a different model must be caught, not trusted |
| Prompt provenance | `prompt_version` · `prompt_hash` · rubric version (judge) | Offset fitting is per (model × prompt hash); drift attribution needs both |
| Generation | effort **requested AND known-honored** flag · thinking mode · schema id | Traces must not imply an effort that wasn't served |
| Usage & cost | input/output/cached tokens · latency · `cost_usd` | Unknown model ⇒ `unknown_model_for_pricing` warning, never silent $0 |
| Outcome | stop_reason · `stop_details` (refusals) · validator results (quote-check, numbers-verbatim, canon∈candidates) · error class (A/B/C/D + transport) | Refusal routing (class B) and failure taxonomy feed from here |
| Integrity | response fingerprint (hash of normalized output) | Silent-update defense (§5.5.4) |

## 8.3 Aggregations that must exist (the §14 cost promise)

Cost per workload (`cw`) · per shelf/model · per candidate journey · per phase
(request-time vs library-time vs audit lane) · daily. The locked cost model these check
against: candidate journey CW-1..7 ≈ $0.10–0.25 · grading ≈ $55–83/1k answers all-Opus
($30–40 if Sonnet-workhorse wins) · authoring $0.5–2.5 · library-time ≈ 0. **The dominant
cost lever is effort, not model swaps** — the dashboards must make an
effort regression visible within a day, which is exactly what the known-honored flag is for.

## 8.4 Gray failures: sampled transcript review (a commitment, not an aspiration)

The majority failure class in production LLM systems is the plausible-looking, unusable
output no exception ever fires for. Dashboards do not find these; humans reading
transcripts do. Cadence:

- **Weekly** while any workload is in `eval owed` or within 30 days of graduating: review a
  random sample (min 20 calls or 5%, whichever is larger) of each live workload's
  transcripts; open-code failures; fold new failure modes into the workload row and, when
  they recur, into its regression eval.
- The judge additionally gets S4's 5–10% sampled re-scores + weekly fixed gold-set regrade
  (models.md §3.5) — automated companions to, not substitutes for, human reading.

## 8.5 Logging rules

Structured events only; **never** full prompt contents at info level, never credentials,
never candidate PII in logs. Traces store prompt *hashes* + versions; the rendered prompt
is reconstructible from the versioned prompt registry + recorded inputs (which live in the
DB under the app's own PII rules, not in logs).

## 8.6 Drift & health surfaces

- Anchor-interleave e-process state (verdict none/system/judge) — the always-on judge gate.
- Verdict flip-rate on the fixed regrade set, weekly trend.
- Per-shelf cost/latency P50/P95 + output-token monitors.
- OPS-1 liveness through the production path.
- Calendar tripwires from models.md §3.7 surfaced as standing alerts (Oct 15 bake-off,
  price events), because a deadline nobody is looking at is not a deadline.
