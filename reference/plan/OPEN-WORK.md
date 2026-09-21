# Open work — the ledger

**What this is.** Everything known to be outstanding, with an owner against each line. Kept
here rather than in a head or a chat log, so "what is left?" has one answer that does not
drift. Updated as part of the change that closes a line, never afterwards.

**Read with:** `docs/BACKLOG.md` (the sequenced 224-item plan — this file does not replace it),
`docs/AGENT_WORK_DESIGN.md` (per-agent build checklists), `api/STATUS.md` (what exists).

Last reviewed: 2026-09-05.

---

## 1. Decisions waiting on the user — each one blocks a build step

These are not research questions. Each has a written recommendation and an owner of `user`.
O2 sat here until 2026-09-05, was answered, and was built the same day.

| # | Decision | Recommendation | Blocks |
|---|---|---|---|
| **BAR-05** | What a job posting is *allowed* to change about a gap map (`docs/spec/jd-overlay-v1.md`, DRAFT) | — (open questions O1–O3, O6 in that spec) | The whole JD applier. The Role analyst can read a posting and cannot act on one, so half that agent is inert. **Highest value of the three.** |
| **O1** | Move the `profiler` agent to the S3 (Haiku) shelf the registry specifies, or leave it on Sonnet | Rebind — registry-conformant, cheaper, and Haiku is the family member that refused to fabricate under schema pressure | Profiler B8 (routing map) |
| **O3** | Build the ingestion hidden-text lint now, or defer to S2 | Now — the injection slice is mandatory for the CV-parse eval, and hidden data is the attack class nothing else catches | Profiler B9 |

---

## 2. Evals — FR-I4 has zero coverage in this repo

`evals/` is empty. Five workloads are built; none has a measured pass rate. Until these run,
every one of them is provisional **on both providers**, not just on the local model.

| Eval | What it measures | Note |
|---|---|---|
| `profiler.cw1.fidelity` | CV parse: fabricated fields, dropped roles | Needs ≥40 human-authored synthetic CVs (HUM-3). The long pole. |
| `profiler.cw3.grounding` | Skill clarify: quote survival, canon hallucination | Needs ≥60 project texts, including "nothing supports this" cases |
| `profiler.cw4` | Claim check: asymmetric cost matrix (a false "demonstrated" ≫ a false "claimed") | Built 2026-09-05; 4 live cases is a smoke test |
| `roleanalyst.cw6` | JD decomposition: planted-requirement drop rate + injection slice | — |
| `roleanalyst.cw5` | Standing read: sycophancy, paired-persona level invariance, undersell | **Claude only — a local run is not evidence for this one** |

---

## 3. Blocked on inputs that do not exist yet

| Item | Waiting on |
|---|---|
| CW-3's actual mandate — constrained selection over a retrieved canon, so a wrong canon key is *unrepresentable* rather than caught afterwards | **EMB-1** (embeddings). Today `skill` is free text policed by code. |
| CW-4's education-weight half | **CW-17** per-level policy (Phase 2). `policy.education_weight()` is a documented placeholder. |
| The JD applier (`JDOverlay` entity, closed-type applier, gap-map surfacing) | **BAR-05** above |

---

## 4. Known defects, recorded and not fixed

| # | Defect | Why it is not yet fixed |
|---|---|---|
| D1 | **The LLM cache stores responses before validation.** A reply that fails a validator is replayed from cache on every retry of that input, turning an intermittent refusal into a permanent one. | Fixing it means moving caching above validation in the runtime seam — touches every workload. |
| D2 | **`runtime._record` has no `connect_timeout`.** A crashed Postgres makes every agent call hang forever instead of degrading. Cost an hour on 2026-09-05. | One-line-ish change to a shared engine; deserves its own change plus tests. |
| D3 | **CW-5's `analysis` is a reasoning scratchpad returned as product.** Third-person while the rest addresses the reader as "you"; one live example was simply false. | Should not reach a candidate surface. Needs a decision on whether to drop or gate it. |
| D4 | **CW-5's number check has a hole:** a count that coincides with a legitimate value in the payload passes ("fourteen" where `gaps_total` was 14). | — |
| D5 | **O10: `end_date` null is read as "ongoing"** across every duration/gap/overlap calculation, so a non-current role whose end date the parse gate nulled becomes ongoing. | Make `is_current` the only currency signal in the arithmetic layer — its own change, with tests. |
| D6 | **O9: the local model under-emits roles on multi-role CVs** — 2 of 4 samples dropped the second role while its own reasoning named all of them. Prompt v2 improved the synthetic case on the 2B; the 4B case is not re-confirmed. | Decided on the eval, not on samples — so it waits on §2. |
| D7 | ONB-16's **profile-versioning half**: no history of confirmed snapshots is kept. | Nothing depends on it, and re-open no longer destroys anything. Low urgency. |

| D8 | **`POST /_probe/claim` is unauthenticated and fans out to up to six serialised model calls** — the other three probes are one call each, and the cap bounds a single request rather than a loop of anonymous ones. | All four probe endpoints are unauthenticated by the same convention and the API binds `127.0.0.1` only. Gating the router behind a dev-only setting is the right fix and belongs in its own change. |

| D9 | **CW-1 drops roles on the local model, and the trigger is LAYOUT.** Same CV content: indented `Project:` sub-blocks → 1 of 2 roles; flattened → 2 of 2. The model's own `analysis` asserted "one role" and then obeyed itself. **No gate fires** — grounding checks that what came back is real, never that what was real came back. | Silent loss of a candidate's career history. Needs a recall check (roles named in `analysis` vs roles emitted) and the eval in §2. |
| D10 | **CW-4's grounding gate checks that a quote is REAL, not that it is ABOUT the skill.** Live run: Terraform appears only in a stack list, and the model returned `demonstrated` / confidence high, justified by the verbatim sentence "I ran the schema migrations" — a real quote about a different tool. `dropped_ungrounded` was false. | This is the exact unearned "demonstrated" the row exists to prevent, produced on 1 of 3 claims. `contains_verbatim` cannot fix it; the quote has to be tied to the skill. |
| D11 | **`resume_filename` and `content_type` are written unclipped** into VARCHAR(400) / VARCHAR(120) on the upload path (`onboarding.py`). Both are client-supplied; the artifact row clips the filename 36 lines later, so the bound was known. | A long filename or a crafted `Content-Type` header 500s the request after the bytes are on disk — an orphaned file, same class as the STATUS §14 incident. |
| D12 | **"Exactly one artifact per profile" is a comment, not a constraint.** Only a non-unique index exists; the invariant is held by read-delete-insert inside one handler. | Two concurrent uploads against a profile with no existing artifact both insert — two retained resumes, the PII outcome ARC-18 exists to prevent. A `UNIQUE (profile_id)` would make it true. |
| D13 | **Profile state lags one request behind completeness.** `_snapshot`'s `if/elif` means the first read after reaching 100% returns `state: "capturing"` next to `is_complete: true`; only the second read says `review`. Deterministic, 13/13. | Any client gating the Confirm CTA on `state === "review"` hides it from someone already at 100% until they refresh. |
| D14 | **`PATCH` on child entities requires the create schema's required fields.** A partial update must resend `name` (project) or `company`+`title` (experience) or get a 422. | No silent field wipe (`exclude_unset` is used), but it is not PATCH semantics and forces the client to hold a full copy. |
| D15 | **`artifact_url` accepts arbitrary schemes** — `javascript:` stored, 201. Inert today: it is only rendered into an `<input value>` and D1 forbids dereferencing it. | Latent, not live. A scheme allowlist would make the guarantee structural rather than incidental. |

### Duplication worth collapsing (from `/code-review`, 2026-09-05) — none is a bug

- All four `_probe/*` endpoints hand-roll a byte-identical `CredentialError` → 503 block. One
  router-level `add_exception_handler` deletes all four.
- `claim_check.check_claim` and `profiler.clarify` (and partly `onboarding.py`) hand-roll the
  same `CredentialError` / `AgentOutputError` / broad-`Exception` triage.
- The demote-only guarantee in CW-4 is enforced in `apply()` by convention, not structurally.
  Worth a guarded constructor once a *second* workload also lowers evidence strength.
- The `FakeProvider` workload fixtures are now a five-branch `if/elif` chain; a dispatch dict,
  or fixtures living beside their workload, would read better.

---

## 5. Agents with no code at all

Seven of the nine in PRD §10.1. Expected at this stage — recorded so "two agents work" is
never mistaken for "the system works".

| Agent | Its workloads |
|---|---|
| Gap analyst | CW-7 (prose only — the diff itself is arithmetic and already built) |
| Plan builder | CW-8 |
| Question generator | CW-9 · CW-10 · CW-11 · CW-12 |
| Evaluator / judge | CW-13 — gated by Phase 0A |
| Guidance agent | CW-14 · CW-15 |
| Adaptation agent | menu-only; the triggers are arithmetic |
| Interviewer | CW-16 — **P2, do not plan ahead** |

Also unbuilt: **CW-2** (guided elicitation dialogue). Today's onboarding questions are
deterministic UI copy, which is a legitimate answer for now.

---

## 6. Closed recently — kept briefly, so the ledger shows movement

| Date | Item |
|---|---|
| 2026-09-05 | **O2 / B10 — re-parse safety.** A second CV parse deleted every experience and education and rebuilt them, destroying all hand-written project depth, and did it to CONFIRMED profiles. Now merge-not-replace plus an explicit re-open. |
| 2026-09-05 | **Review-screen replace never re-parsed.** When the upload was split into two phases, only the career-step card was updated; replacing a resume from the review screen swapped the file and kept showing the PREVIOUS parse's roles under the new filename. Both phases now run. |
| 2026-09-05 | **A NUL byte anywhere in captured text 500'd the request** (four routes). PostgreSQL cannot store a NUL byte; the 500 answered `text/plain`, the one shape the frontend cannot parse. Stripped once at the schema boundary. |
| 2026-09-05 | **Three probe pages crashed on a 422** — FastAPI's `detail` array rendered into JSX. One shared `readProbeError` now serves all four. |
| 2026-09-05 | **The 409 re-open dead end existed on the review screen too** — the upload card was wired for it and this one was not. |
| 2026-09-05 | **CW-4** claim check built — the Profiler's third workload. |
| 2026-09-04 | **CW-5**, **CW-6** built — the Role analyst's two runtime workloads. |
