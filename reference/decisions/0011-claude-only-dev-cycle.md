> **POC copy — edited 2026-09-18.** Snapshot of the Caliber file with provider-gateway material removed; everything else is verbatim.

# ADR-0011: Claude-only for the development cycle — OAuth, no API keys

## Status
Accepted — 2026-09-02 (user decision) · scoped to the development cycle; amends the
*operative* mapping, not the locked destination
· **Amended by ADR-0015 (2026-09-03, interim):** "no non-Anthropic calls" reads as
*no non-Anthropic network calls* while Console credits are unresolved — a local CPU
model may carry the validator-bounded S3 rows for dev iteration only

## Context
Model Mapping v2 (ADR-0009) fields four API models across two vendors, which forced a
queue of cross-vendor decisions (D5, Terra/Sol/MiniCheck ratifications). The user's call: development runs on Anthropic
exclusively, authenticated by the Claude Console OAuth profile (`ant auth login`,
ADR-0003) — no API keys, no non-Anthropic calls.

## Decision
For the development cycle:
- **Fleet: 3 Claude API models** — S1 `claude-opus-5`, S2 `claude-sonnet-5`,
  S3 `claude-haiku-4-5` — **+ 1 local** (`bge-small-en-v1.5`, pending R7; Anthropic has
  no embeddings endpoint, and a local model sends nothing anywhere).
- **Transport: direct Anthropic SDK only** (+ the first-class fake provider).
- **S4's duties are reassigned within family or to humans** — every delta enumerated in
  `docs/llm/dev-cycle.md` §10.4, and every weakened protection named with its
  compensation in §10.5 (the human gold set and the vendor-independent drift
  instruments now carry the audit burden).
- Fable 5 stays disqualified (retention/no-ZDR + price) — "Claude-only" does not
  rehabilitate it.
- Dissolved by collapse: D5-for-now, R1, R3; R2
  deferred. The destination mapping's S4 slot + D5 re-open as one decision when the
  product approaches real-candidate scale.

## Alternatives considered
- **Keep the 4-model fleet.** Rejected by the user for this cycle: two
  vendors' worth of credentials and data-governance gates ahead of a
  product that hasn't passed Phase 0A yet — the complexity bought protection the human
  gold set must provide anyway.
- **Claude-only including embeddings (strike EMB-1).** Left open as R7 — striking it
  also strikes CW-3 retrieval and the semantic cache; recommendation is to keep local.

## Consequences
- Critical path shortens: `ant auth login` → harness → human gold set → Phase 0A gate.
  Open decisions drop from nine to two (R5, R7).
- Family-preference bias in auditing is accepted, eyes open, with named compensations
  (dev-cycle.md §10.5) — the anti-self-laundering anchor rule is now load-bearing.
- The Oct 15 S3 obligation simplifies to rehearsing the Sonnet-5-low fallback config.

## Enforced by
`docs/llm/dev-cycle.md` (operative plan, §10); provider registry keeps exactly
`anthropic` + `fake` live; `routing.py` alias map carries no non-Anthropic refs this
cycle; banners in `models.md`/`roadmap.md` point here.

## Sources
User decision 2026-09-02 (this session); ADR-0003/0009; `docs/llm/dev-cycle.md`.
