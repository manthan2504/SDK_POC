# ADR-0014 — The resume upload is split from the resume parse

- **Status:** Accepted
- **Date:** 2026-09-03
- **Context:** PRD §7.1 Path A; `docs/llm/workloads.md` CW-1; the presence brief
  §36 ("no arbitrary timers for production behaviour")
- **Supersedes:** nothing. **Superseded by:** nothing.
- **Related:** `web/AgentPresence/AgentImplementation.md` §4.2 (this is the "v2"
  it planned); ADR-0008 (app-governed orchestration — the app sequences agents,
  no orchestrator agent).

---

## Context

`POST /profile/resume` did two unrelated things in one request:

1. **Read the file.** `extraction.py` over pdfplumber / python-docx. Pure
   arithmetic on bytes, deterministic, and usually finished in well under a
   second. It also stores the bytes and the extracted text.
2. **Understand it.** `run_agent("profiler", …)` — CW-1. A model call that takes
   **10–30 seconds** and can fail in ways the first phase cannot.

To a client these were indistinguishable: one request, one long opaque wait, one
answer. That was tolerable while the wait was just a spinner. It stopped being
tolerable when the Profiler got a presence, because the character is supposed to
say *what is happening now* — and with one request there was only ever one thing
to say for the whole thirty seconds.

The tempting fix was to narrate the phases on a timer: show "reading" for the
first N seconds, then switch to "thinking". That is exactly the pattern the
presence brief forbids (§36), and the same one the progress-indicator research
names as deceptive — a status that advances on a clock rather than on work.
It would also have been *wrong* as often as not: extraction is sub-second, so a
timer would have shown "reading the file" long after the file was read.

## Decision

**Two endpoints, one per phase.**

| | |
|---|---|
| `POST /profile/resume` | Reads, validates, stores the bytes, extracts the text, supersedes any previous artifact. **No model call.** Returns the snapshot. |
| `POST /profile/resume/parse` | Runs CW-1 over the `resume_text` the first call committed. Writes the structured rows. Returns the snapshot. |

The first endpoint keeps its path and its request shape; it simply stops
earlier. The second carries no upload at all, which is the property that makes
it independently retryable.

The UI calls them in sequence and reads the agent's state off which request is
in flight: `working` during extraction, `thinking` during the parse. Both are
now true statements about a live request rather than positions on a clock. This
is what finally makes `thinking` emittable — it had been reserved-but-never-used
since the character was built, precisely because nothing honest could drive it.

## Consequences

**Good**

- `thinking` becomes real. The one state the presence had to keep dark now has a
  genuine signal behind it.
- **A failed parse no longer costs the upload.** The text and artifact are
  already committed by the time the model is called, so a 502 is retryable with
  one cheap request instead of asking the candidate for the file again.
- The two failure classes separate cleanly: a 413 or an unreadable scan belongs
  to phase 1 and never reaches the agent; a provider stand-down belongs to
  phase 2. The UI already distinguishes them, and now the server does too.
- Re-parsing with a better model or a fixed prompt becomes a single call against
  stored text.

**Costs, accepted**

- **Two round trips** where there was one. Irrelevant against a 10–30s model
  call.
- **A new intermediate state exists**: text stored, nothing parsed. It was
  always reachable (a 502 left exactly that), but it is now reachable by design.
  `resume-review.tsx` shows no agent when there are no rows, because it cannot
  tell "never ran" from "ran and found nothing" — see the open item below.
- **Re-parse can now duplicate.** One request could only parse once; a retryable
  parse can be called twice over the same text, and appending would hand the
  candidate two copies of their career. The parse route therefore clears the
  rows it owns before writing. Pinned by
  `test_parsing_twice_replaces_rather_than_duplicates`.
- A client that calls only the first endpoint gets a stored resume and no rows.
  That is a legitimate state, not an error, and the second call is idempotent
  enough to be safe to retry.

## Alternatives rejected

- **Narrate one request on a timer.** Forbidden by §36, and factually wrong most
  of the time. This is the option the split exists to avoid.
- **Stream the phases over SSE.** The honest end state, and considerably more
  machinery: a streaming transport, a provider that emits token events, and a
  client that consumes them. It buys progress *within* the model call; the split
  buys the phase boundary, which is the larger of the two gaps. SSE remains open
  and is what would make `thinking` reflect real token flow rather than "the
  request is in flight".
- **Keep one endpoint and return phase timings afterwards.** Tells the candidate
  what happened after they have finished waiting, which is the one moment the
  information is worthless.

## Open

- **`parse_error` is not exposed on `ProfileOut`.** It lives on `ResumeArtifact`,
  which `ProfileOut` does not read, so the client still cannot distinguish "the
  provider never took its turn" from "it ran and honestly found nothing". Until
  it is, `resume-review.tsx` claims neither and shows no character when there
  are no rows.
- **The eval CW-1 owes (FR-I4) is untouched by this.** Splitting the transport
  does not measure the parse.
