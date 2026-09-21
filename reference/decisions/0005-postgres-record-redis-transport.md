# ADR-0005: Postgres is the system of record; Redis is transport only

## Status
Accepted — 2026-08-31 (constraints C-1/C-2)

## Context
Local Redis is Memurai Developer: verified non-production licence, ~10-day uptime ceiling
(self-terminates), `appendonly no`, and **no RediSearch** (`MODULE LIST` empty). Anything
durable that lived only in Redis would eventually vanish on a box that stays up for weeks.

## Decision
- Redis/ARQ carries jobs **in flight**; the `job_run` table in Postgres is the record of what
  was requested, what happened, and what must be recovered. Sessions belong in Postgres.
- The semantic cache moves to a pgvector table (no RediSearch locally).
- **The judge/grading route is excluded from semantic caching in code** — two paraphrased
  answers are not the same answer; a cache hit would return someone else's score. This is a
  correctness rule, not a performance tuning choice, and it survives any future cache backend.
- Swap to Azure Cache for Redis is mandatory before production (licence forbids Memurai prod use).

## Alternatives considered
- **Trust Memurai + AOF.** Rejected: the licence tier caps uptime by design; durability
  by configuration on a product that terminates itself is not durability.
- **Drop Redis entirely, poll Postgres.** Viable at this scale but keeps ARQ's semantics —
  kept because the target stack names Redis and the abstraction cost is already paid.

## Consequences
- Every job-producing path writes `job_run` first; a Redis wipe loses transport, not truth.
- Grade requests always recompute (`docs/llm/06-grounding.md` § cache policy).

## Enforced by
CLAUDE.md §6 (known trap); `docs/llm/06-grounding.md` cache-exclusion rule (code-enforced
at the cache lookup seam); `job_run` schema.

## Sources
`docs/WORKLOG.md` Part 5; `docs/TECH_STACK.md` Constraints discovered after bring-up.
