# BAR-01 — Beachhead role identity & the experience-level band taxonomy (v1, DRAFT)

Sources: PRD §3 (beachhead = "senior AI / AI-agent engineers (3–10+ yrs)"), §6 (Ravi, 6-yr
AI engineer targeting Senior AI Agent), D6 (experience-calibrated), §7.3 depth ladder
("aware → can build → can design → can defend under load"), Appendix D ("calibrated to
~5 yrs"), `policy.py` `TITLE_RANKS` (generic English title modifiers), the frontend's
provisional `LEVELS` list in `target-role.tsx`.

## 1. Beachhead role identity

| Field | Value | Why |
|---|---|---|
| `role_key` | `senior_ai_engineer` | The backlog already uses it (`GRD2-08` → `senior_ai_engineer.rubric.yaml`); a key is an identifier, not a marketing name |
| Display name | Senior AI Engineer | PRD Appendix B/D wording; "AI-agent" is the market framing, not the bar's name |
| Bar path | `rolebars/senior_ai_engineer/<version>/bar.yaml` | BAR-12 authoring format |
| Authorship | Founder + one second senior AI engineer (D5) | The bar's credibility *is* the product |
| Family | `engineering.ai` | Free-text taxonomy hint for future role expansion; carries no behaviour |

**Naming rule for future roles (D9):** `<level-free role noun>_<discipline>` in snake_case,
level-free because the *same* bar serves every level through its depth matrix (D6). The
beachhead key carries "senior" only because the PRD names the beachhead that way and the
backlog already references it; it is grandfathered, not a precedent.

## 2. The level enum (ordered)

Five bands. The names are the ones the frontend already uses as placeholders, so ratifying
this replaces a placeholder with config, not a rename.

| Order | `level` | Label | Years band (total professional, inclusive lower) | Depth anchor at this level (§7.3 ladder) |
|---|---|---|---|---|
| 0 | `junior` | Junior | 0 – <2 | aware; builds with guidance |
| 1 | `mid` | Mid | 2 – <5 | can build |
| 2 | `senior` | Senior | 5 – <9 | can design |
| 3 | `staff` | Staff | 9 – <14 | can defend under load; sets direction |
| 4 | `principal` | Principal / Lead | 14+ | as staff, broader scope |

The depth anchor is a *default expectation shape*, not a rule: each bar's depth matrix
(BAR-16) states the required depth per sub-skill per level explicitly, and may sit above or
below the anchor for any given sub-skill. The anchor exists so an author starting a matrix
has a defensible baseline.

**Beachhead bar v1 supports:** `mid`, `senior`, `staff` — the PRD's 3–10+ year window. A
candidate whose calibrated level falls outside the supported set is **clamped to the
nearest supported level and told so** ("*We're reading you at the Mid bar — the Senior AI
Engineer bar doesn't go lower yet*"). Never silently, never by refusing them.

## 3. Calibrated level vs target level (the D6 split)

Two different things the current code already stores separately:

| Term | Source | Used for |
|---|---|---|
| **`calibration_level`** | `band(years_experience)` — derived, deterministic | Reading the bar's expected depth. D6: "what a candidate at *their years* should know" |
| **`target_level`** | Candidate's own choice on the target-role step | Ambition (§7.2 "their ambition"); the honest read compares the two |

Rules:
1. `years_experience` is the candidate's stated total, validated against the dated stints by
   the existing consistency flag (`years_mismatch`, `policy.YEARS_TOLERANCE`). A flagged
   mismatch does **not** change the band — it is surfaced, and the probe-first mechanism does
   the verifying. Arithmetic never quietly overrules the candidate; it asks.
2. `years_experience` null → `calibration_level` is unknown → the gap engine cannot run;
   the target-role step already requires the field for the completeness gate to pass.
3. **The bar is read at `calibration_level`, never at `target_level`.** A 3-year candidate
   targeting Senior is measured as a Mid *reaching* for Senior: the gap map shows the Mid
   gaps first (must close) and the Senior delta as the "reach" (§7.2 "realistic launch point
   AND reach goal"). This is the arithmetic form of the motivation guardrail.
4. `target_level > calibration_level + 1` is allowed (user keeps control) and flagged in the
   honest read as a longer path; `< calibration_level` is allowed and flagged as possible
   underselling (§7.2 "it cuts both ways").

## 4. Where the enum lives

`config/experience_levels.yaml` is the source; `enums.py` gains `ExperienceLevel` generated
from it (ARC-03's single-enum-module rule) with a drift test; the frontend `LEVELS` array is
replaced by the same list served from the API. One list, three consumers.

## Ratification checklist

1. `role_key = senior_ai_engineer`, display "Senior AI Engineer" — ok / change?
2. Five bands with these year boundaries (2 / 5 / 9 / 14) — ok / change?
3. Beachhead v1 supports mid + senior + staff; outside → clamp with a visible note — ok?
4. Bar read at **calibrated** (years-derived) level, target level is ambition only — ok?
5. Years mismatch flag surfaces but never re-bands — ok?
