# ADR-0006: The fake LLM provider is first-class, not a test shim

## Status
Accepted — 2026-08-31 (S0/S1 build)

## Context
This box authenticates via interactive OAuth only (ADR-0003): no credential in CI, none for
an agent working unattended, none until a human runs `ant auth login`. If development,
tests, and evals required a live credential, every one of them would be blocked on a human
and every offline run would silently skip the LLM paths.

## Decision
`FakeProvider` is a deterministic, offline, first-class member of the provider registry —
same interface, same routing, same tracing as the real ones. Same prompt → same answer,
always. It mirrors the *contracts* the real agents are held to (the fake Profiler only
proposes terms it can find verbatim in the supplied text — the grounding rule, honored
offline), so the offline path exercises the same rules as the live one.

What the fake provider is **not**: an eval subject. FR-I4 evals-of-record run against the
pinned live model; the fake exists so the app, its tests, and the harness *mechanics* run
with no credential and no network.

## Alternatives considered
- **Mock at the test layer only.** Rejected: leaves the running app dead without a
  credential, and every integration surface (probe endpoint, resume parse, clarify) untestable
  in a real browser offline.
- **Record/replay cassettes.** Rejected for now: recorded responses go stale against a moving
  API surface and leak prompt content into fixtures on a PII-sensitive repo.

## Consequences
- 275+ tests run in seconds, DB-free and network-free.
- Every provider error path had to be honest: a missing credential is a 503 with a fix hint,
  never a silent fake fallback — provider selection is explicit (`LLM_PROVIDER`), never
  automatic degradation.

## Enforced by
`providers.py` (FakeProvider contract mirror); `LLM_PROVIDER` explicit selection; FR-I4
(evals name their live model — a fake-provider eval run gates nothing).

## Sources
`api/STATUS.md` §13; `providers.py` module docstring.
