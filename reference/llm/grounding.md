# §6 — Grounding, Retrieval & Caching

How model calls get their evidence, and what may never be cached. Physical store: pgvector
in the one Postgres (ADR-0004); embeddings: EMB-1 (workloads.md §2.4).

## 6.1 Grounding rules

- **Grounded or dropped** (behavior spec §1.2): claim-resolving proposals carry verbatim
  quotes, substring-verified in code. The prompt asks; the code checks.
- **Constrained selection beats open generation** wherever a canon exists: CW-3 picks from
  retrieval-supplied candidates and a validator enforces canon ∈ candidates. The model
  never mints taxonomy.
- **The near-miss hazard** is retrieval's characteristic failure here: an adjacent role's
  bar reads plausibly and grades wrongly. Retrieval for bar-dependent workloads is
  department-of-one — filtered to the target role/level, with source attribution, never
  best-effort semantic soup.
- **Open architectural fork (needs an ADR before S3):** for a single role's assessment,
  put the **whole bar in context** rather than retrieving fragments. 1M-context S1/S2
  models make this affordable; it eliminates the near-miss class entirely for the
  highest-stakes consumers (CW-8/9/13). Retrieval then serves only genuinely cross-corpus
  work (CW-3 taxonomy, CW-22 mapping). Decide at S2 when bars exist; record as ADR-0011.

## 6.2 EMB-1 operations

- Local `bge-small-en-v1.5`, 384-d, CPU, no network — same pgvector column that serves
  the semantic cache and retrieval.
- **A model swap is a migration** (dimensions are DDL-fixed; vectors from different models
  never co-mingle): blue/green dual-column — add column → backfill with new model → cutover
  reads → drop old. The bake-off (incumbent vs `granite-embedding-small-english-r2`) runs
  TalentCLEF-B-style: ~300 in-domain queries, NDCG@10 + recall@50 + CPU P50/P95.
- Deferred arms recorded, not lost: Qwen3-0.6B (quality ceiling, offline-index-only),
  EmbeddingGemma (pending license clearance).

## 6.3 Caching policy (the table that prevents the expensive mistake)

| Layer | Policy |
|---|---|
| **Grades / judge route** | **NEVER cached, semantic or exact.** Enforced in code at the cache seam. Two paraphrased answers are not the same answer; a hit returns someone else's score |
| Semantic cache (pgvector, C-2) | Non-graded, idempotent lookups only (e.g. clarify on identical text). Exact-key first, semantic as assist; entries carry model id + prompt version — a prompt bump invalidates |
| Anthropic prompt caching | Stable-prefix discipline (§4.4): frozen system prompt + schemas before the breakpoint, volatile content after. Model-scoped AND effort-scoped — the judge's xhigh re-sample lane has its own prefix. Verify via `cache_read_input_tokens` |
| Provider result reuse | `served_from` field on every trace: `provider` / `cache_exact` / `cache_semantic` — a response that can't say where it came from doesn't count as either |

**Cascade-of-judges is never used for the gate** (locked caveat): no cheap-model prefilter
deciding which answers the real judge sees — that reintroduces an unmeasured model into the
grade path through the back door.

## 6.4 Context discipline

Retrieve less, deliberately: the model gets the fields the workload names (workloads.md
In→Out), not the profile dump. Long-horizon state (CW-16's 30–60 turns) uses the external
turn-summary ledger pattern — re-injected summary, not unbounded history. Context budgets
are per-workload numbers in the eval's cost column, not vibes.
