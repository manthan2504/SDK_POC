# S2 entry specs — BAR-01 … BAR-06 (DRAFT, awaiting ratification)

The backlog gates S2 ("role bar + assessment plan") on six decisions being made before any
S2 code. These drafts make each decision concrete enough to ratify or correct. Nothing here
is built yet; once ratified, `config/*.yaml` becomes the single source the engine reads
(same rule as `policy.py`: no module hard-codes a number that lives here), and the locked
scoring model is recorded as an ADR.

| Item | Spec | Config | Decides |
|---|---|---|---|
| BAR-01 | `beachhead-role-and-levels-v1.md` | `config/experience_levels.yaml` | The beachhead role key; the ordered level enum with year bands; which level a candidate is *calibrated* at (D6) vs *targets* |
| BAR-02 | `gap-scoring-v1.md` §1 | `config/scoring.yaml` → `depth`, `evidence` | Depth ordinals, evidence ordinals, the evidence→depth crosswalk, gap-size arithmetic |
| BAR-03 | `gap-scoring-v1.md` §2–3 | `config/scoring.yaml` → `weights`, `recency` | Weight scale + normalization, recency factor, the priority formula |
| BAR-04 | `gap-buckets-v1.md` | `config/scoring.yaml` → `buckets` | The five canonical buckets, precedence rules, display order |
| BAR-05 | `jd-overlay-v1.md` | `config/scoring.yaml` → `jd_overlay` | What a JD may and may not change, with bounds |
| BAR-06 | `rolebar-versioning-v1.md` | — | Version scheme, publish gate, pinning, migration matrix |

**Reading order:** BAR-01 → BAR-02 → BAR-03 → BAR-04 → BAR-05 → BAR-06. Each later spec
consumes terms the earlier one defines.

**Ratification protocol:** each spec ends with a numbered checklist. Reply per item with
"ok" or a correction. Anything not explicitly ratified stays DRAFT and blocks the engine
(BAR-21) from being marked done — a number nobody signed is a guess.

**Standing invariants every spec honours**
- *Arithmetic owns dated facts; the model owns ambiguity; the app owns sequence.* Every
  formula here is deterministic; the only model-produced inputs are the JD decomposition
  (CW-6) and gap reasons (CW-24 fallback templates exist).
- **D6** — the bar is read at the candidate's calibrated level; nothing resets to zero.
- **D9 / FR-I5** — nothing here names a role's content; the beachhead role appears only as a
  `role_key` string in config, never in app code.
- **The system proposes; the human decides** — the bar is founder-authored (D5) and every
  gap carries a resolvable citation back to it.
