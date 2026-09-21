> **POC copy — edited 2026-09-18.** Snapshot of the Caliber file with provider-gateway material removed; everything else is verbatim.

# §4 — Routing, Providers & Prompt Governance

How a workload's request becomes a model call: the binding rules, the provider seam, and the versioning that makes every call reproducible. Code owners:
`api/src/caliber/llm/` (`provider.py`, `providers.py`, `routing.py`, `runtime.py`,
`structured.py`).

## 4.1 The call flow (app-governed, always)

```
app code (fixed §7 order, per-user state row)
  → run_agent(workload task tag, prompt bundle)         runtime.py
    → shelf lookup (workload → shelf)                   routing.py  [config, not code]
      → model lookup (shelf → model id)                 routing.py tiers + settings
        → provider (anthropic | fake)           providers.py [LLM_PROVIDER]
          → pin-and-log: served model, usage,
            stop_details, prompt_hash, effort           agent_call (§8.2)
```

Rules the flow enforces:
- **Intelligence never routes.** The workload names a shelf; config names the model;
  no model output influences where the next call goes (triggers are arithmetic, §2.6).
- **Provider selection is explicit** (`LLM_PROVIDER`), never automatic degradation. A
  missing credential is a 503 with the provider-appropriate fix hint, not a silent fake.
- **No silent fallback across models.** Class-A handling is within-family retry then
  output-pending. A result from an unmeasured model is worse than no result — it corrupts
  calibration, evals, and costing at once.

## 4.2 Shelf binding (the one-line-change contract)

`routing.py` holds: shelf → model id · the `_PRICES` table · `canonical_model_id()` normalization for echoed
models. Contracts:

- Swapping a shelf's model touches **one line** and triggers that shelf's eval suite
  (models.md §3.6 bake-offs land here).
- An unmapped model ref raises an informative error — **no silent aliasing**.
- `cost_usd` on an unknown model logs `unknown_model_for_pricing` — **never silently $0**.
  Known-free models get explicit `(0.0, 0.0)` entries, distinct from unknown.
- Effort values pass through only to models that accept them (never Haiku).

## 4.4 Prompt governance (registry semantics — AGT-06)

Prompts, rubrics, and judge instructions are **versioned production artifacts**, not
strings in code review's blind spot:

1. **Immutable versions.** A prompt change is a new version with a commit message; the old
   version remains addressable. Prompt text lives in the repo (prompts/ convention), diffed
   like code.
2. **Provenance on every call.** Each `agent_call` row records `prompt_version` +
   `prompt_hash` (sha256 of the exact rendered system prompt) + served model + (for the
   judge) rubric version. A trace that can't say which prompt produced it is unusable for
   drift attribution.
3. **Eval-gated promotion.** No prompt, model assignment, rubric, or tool-schema change
   ships without a recorded eval-gate result (evals.md §5.7 — the one change-management
   rule). Rollback is re-pointing to the prior version, instant.
4. **Judge coupling.** The harshness offset is fitted **per (model version × prompt
   hash)** — a prompt edit invalidates the offset exactly like a model change does
   (evals.md §5.5).
5. **Cache discipline.** Stable content first (frozen system prompt, deterministic
   schemas), volatile content after the last cache breakpoint; caches are model-scoped and
   effort-scoped — verify with `cache_read_input_tokens`, not hope.

## 4.5 Structured output policy

- Schema'd calls use `output_config.format` / `messages.parse()` with Pydantic, or strict
  tools (`strict: true`, `additionalProperties: false`) — never prose parsing, never prefill
  (removed, 400).
- **Reasoning fields precede verdict/score fields on every schema'd call** (standing
  constraint; the evidence-driven two-pass refinement — free-text critique, then constrained
  extraction — is an eval-design comparison arm for the judge: evals.md §5.5).
- Tool/parameter names are prompt-grade artifacts: unambiguous semantics, actionable error
  messages. The few tool-using workloads (CW-11's harness loop) budget response tokens
  explicitly.

## 4.6 Failure semantics at the seam

| Condition | Behavior |
|---|---|
| No credential | `CredentialError` → 503 with provider-appropriate hint (`ant auth login` / `LLM_PROVIDER=fake`) |
| Refusal (`stop_reason: refusal`) | Class B: retry-with-repair → human queue. Judge: human queue IS grade-of-record; `stop_details` logged. **Server-side `fallbacks` stay OFF for the judge, permanently** |
| 429/5xx | Propagate after the provider's own retries — the app reports, never loops |
| Unparseable structured output | Class B repair path; for assists (clarify), `[]` is a valid, non-blocking answer |

## 4.7 Batch lane

Authoring-time and audit work that tolerates hours (S4 sampled re-scores, CW-10 blind key
checks, CW-22 ingestion, CW-16 post-mortems) goes through the Batch API at −50%, keyed by
`custom_id`, results order-independent. Request-time workloads never wait on a batch.
