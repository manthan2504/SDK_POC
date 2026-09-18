# evals/ — the FR-I4 gate

**This directory is empty, and that is the single largest piece of debt in the repo.**

FR-I4 (PRD §8, p14) is one sentence: *"Per-agent eval/gold-set gate; no agent ships on
vibes."* `docs/llm/evals.md` §5 turns it into contracts. Every workload in
`docs/llm/workloads.md` names the eval that gates it. None of them has been written or run.

The file is committed so the directory survives in git, and so nobody has to discover the
gap by grepping for it.

## What is owed, per workload already built

| Workload | Named gate | Gold set |
|---|---|---|
| **CW-1** resume parse | planted-absence (nulls over guesses) | `evals/profiler/cw1_*` |
| **CW-3** skill clarify | grounding: quote survival, empty-list correctness | `evals/profiler/cw3_*` |
| **CW-6** JD decomposition | seeded-JD drop rate + an injection slice | `evals/role_analyst/cw6_*` |

CW-6's contract is specified in `docs/AGENT_WORK_DESIGN.md` §2.12 and is the most concrete:
30–50 synthetic postings with requirements planted in low-salience positions, scored as a
**four-cell classification** (`coverage_recall` and `discard_precision` reported separately,
never blended — a single "everything was accounted for" percentage is satisfied by
discarding the whole posting). Target is **≥0.80 cluster-level recall**, deliberately *not*
strict-span F1: expert-vs-expert agreement on skill extraction is F1 0.44–0.53, so a high
span target would be measuring noise rather than quality.

## Two rules that apply to everything in here

- **Synthetic fixtures only (HUM-3).** No real resume or real candidate data enters this
  repository, in a fixture or anywhere else.
- **A local-model result never gates anything** (ADR-0015). The eval of record names a
  pinned Claude model. Local runs are development evidence, reported separately and never
  pooled with it — an average across two providers describes neither.

## Status

Nothing here has run. Until it has, every workload marked "built" in `workloads.md` is
built and **unmeasured**, and the status fields say so.
