# reference/ — read-only snapshot from D:\Caliber (2026-09-17)

Copied from the real Caliber repo so the POC can be built against its design.
**Do not edit these files**; they are a snapshot. The source of truth stays in `D:\Caliber`.
The current PRD is one level up: `D:\SDKPOC\Caliber-PRD-v1.7.html` (the Caliber repo still cites v1.6).

Runtime data the POC will actually load lives in `../data/`, not here.

| Folder / file | What it gives us | Used when building |
|---|---|---|
| `agents/AGENT_WORK_DESIGN.md` | Per-agent design: PRD demands, "never" rules, schema, prompt, validators, evals. Only §1 Profiler and §2 Role analyst are written | Every agent |
| `agents/AGENT_PLANNING_PROCEDURE.md` | The 16-heading template Caliber uses to plan an agent | Planning each agent |
| `llm/workloads.md` | The CW-1..22 registry: what each AI task may / may never do, and the arithmetic-only list (§2.6) | Deciding code vs model |
| `llm/dev-cycle.md` §10.4 | Claude model + effort per workload | Picking `model` / `effort` per agent |
| `llm/overview.md`, `safety.md`, `grounding.md` | Behaviour rules, injection posture, grounded-or-dropped | Prompts + validators |
| `llm/evals.md`, `../evals-README.md` | Eval contracts, gold-set rules | Eval step |
| `llm/routing.md`, `models.md`, `observability.md` | Call flow, model constraints, what every trace records | Runner + audit log |
| `llm/flow-diagram-source.txt`, `candidate-journey-*.png` | "Which AI does what" across the journey | Overview |
| `specs/gap-scoring-v1.md`, `gap-buckets-v1.md` | Gap size, priority, the 5 buckets (all arithmetic) | Gap map code |
| `specs/fit-labels-v1.md` | Strong fit / Stretch / Not yet (arithmetic) | Role Analyst code |
| `specs/beachhead-role-and-levels-v1.md` | Level bands from years; calibrated vs target level | Level code |
| `specs/jd-overlay-v1.md`, `rolebar-versioning-v1.md` | What a JD may change; bar versioning | Role Analyst (JD), later |
| `decisions/0008-*` | No orchestrator agent — the app owns sequence | Pipeline runner |
| `decisions/0007-*` | Grading stability without temperature | Evaluator |
| `decisions/0006-*`, `0009-*`, `0011-*` | Fake provider, model shelves, Claude-only dev cycle | Provider layer |
| `prompts/profiler/`, `prompts/role_analyst/` | Caliber's real prompt files, all versions (latest: cw1 v2, cw3 v1, cw4 v2, cw5 v5, cw6 v1) | Prompt style reference |
| `PAYWALL-MATRIX.md` | Free vs paid boundary (D3) | Paywall flag |

`../data/`:
- `rolebars/senior_ai_engineer/v0.1-placeholder/bar.yaml` — the role-bar (a **placeholder**, PRD Appendix D reshaped; 16 sub-skills, depths for mid/senior/staff)
- `config/scoring.yaml` — gap-scoring numbers (depth/evidence ordinals, weights, recency, buckets, JD bounds, fit thresholds)
- `config/experience_levels.yaml` — level bands (junior 0 / mid 2 / senior 5 / staff 9 / principal 14 years)
