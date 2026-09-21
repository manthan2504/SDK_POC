# Role bar — what the file is, and what every field in it means

> A **role bar** is the checklist for one job: what a person in this role is
> expected to be able to do, and how well, at each seniority level.
>
> One bar per **role**, not per candidate. Everyone targeting "Senior AI
> Engineer" is measured against the same file — which is the only reason two
> candidates' gaps are comparable.

Bars live at `data/rolebars/<role_key>/<version>/bar.yaml`. Today there is one:
`senior_ai_engineer/v0.1-placeholder/`, and it says in its own header that it is
a scaffold, not the authored bar.

---

## 1. Who writes it

| Which bar | Author | Status |
|---|---|---|
| The **beachhead** role (Senior AI Engineer) | **Two senior engineers**, by hand | PRD D5: *"The credibility of the bar is the product; two-senior calibration hardens it"* |
| **Every other role** | **Agent-generated**, then expert spot-reviewed | PRD D5 / D10, and **Phase 2** — a non-goal for the MVP |

The generating agent (CW-17) is the one part of the system allowed to use the
web, because it runs at **library time**: once per role, with no candidate's
data anywhere near it, and a human signs the result off before it serves anyone.
Runtime agents are forbidden web access — holding private data *and* untrusted
content *and* a channel out is the "lethal trifecta" that turns hidden text in a
PDF into a data leak.

**Nothing in this folder may be invented by a coding assistant.** Restructuring
existing content is fine; adding a skill or an alias is authoring, and authoring
is D5's job.

---

## 2. Where the bar is used

```
resume text ─▶ [1] Profiler ─▶ skills the candidate claims
                                   │
                  CW-3 skill normalise: match each claim to a bar key
                                   │
                              [3] Gap Analyst: required depth − shown depth = gap
                                   │
                              [4]/[5]: what to test, and how
```

Two different jobs from one file:

- **`aliases` / `tools`** drive the *matching* — is this resume line the same
  skill the bar means?
- **`depth` / `weight` / `how_tested`** drive the *gap* — how good do they need
  to be, how much does it matter, and what kind of question tests it.

---

## 3. The file, field by field

### Header

| Field | Meaning |
|---|---|
| `schema_version` | Format version of this file |
| `role_key` | Stable id. **Must equal the directory name** — the directory is how a bar is found, the field is what citations resolve against, and drift makes `source_ref` unresolvable |
| `display_name` | What a human calls the role |
| `version` | This bar's version, matching its directory |
| `status` | `draft` / `in_review` / `published` / `retired` / `placeholder`. Anything but `published` is a placeholder |
| `supported_levels` | The levels this bar has depths for, e.g. `[mid, senior, staff]` |
| `role_aliases` | Free-text target roles that land on this bar. Level words are ignored when matching, so "Senior AI Engineer" and "AI Engineer" both arrive here. A candidate whose target role is **not** listed is told no bar exists for their role — they never get another role's gaps under their own role's name |

### The scales

`depth_scale` and `weight_scale` say what the numbers below *mean*, so the
rubric sits next to the values an author is choosing. Without them, two people
writing two bars mean different things by "3".

```yaml
depth_scale:
  0: nothing captured          # out of scope at this level
  1: aware of it
  2: can build with it
  3: can design with it
  4: can defend it under load  # `required: 4` means assessment-only
```

`weight_scale` runs 1–5 and feeds `priority = gap × weight/5 × recency_factor`,
so 5 is full contribution and 1 is a fifth of it. **3 is the default** when a
sub-skill omits `weight`.

Both are copied from `reference/plan/ARITHMETIC_RULES.md` §6 — they are not this
file's invention, and changing them here would silently change the arithmetic.

### A sub-skill

```yaml
- key: retrieval.embeddings            # the join key. Never changes.
  name: Embedding selection & trade-offs
  weight: 4
  how_tested: [open_ended, mcq]
  aliases: [embeddings, embedding]     # OTHER WORDS for this same skill
  tools:   [sentence transformers, pgvector, bge]   # things you USE for it
  depth: { mid: 2, senior: 3, staff: 3 }
```

| Field | Meaning |
|---|---|
| `key` | The stable id everything downstream joins on. Distinct from `name` so the label can be reworded without breaking stored profiles |
| `name` | The human label, used in question text |
| `weight` | 1–5, per `weight_scale`. Default 3 |
| `how_tested` | Which question kinds suit it: `open_ended`, `mcq`, `practical` |
| **`aliases`** | Other words for **the same skill**. "rag" and "retrieval augmented generation" are the same claim |
| **`tools`** | Products and libraries used *while doing* the skill. **Not the same claim.** "pgvector" is not another word for judging embedding trade-offs — it is something you may have used without ever making one |
| `depth` | Required depth per level, 0–4 per `depth_scale`. `0` means out of scope at that level |
| `tier` *(optional)* | Author override for display grouping: `must_know` / `should_know` / `optional`. Derived from required depth when absent (3–4 must_know · 2 should_know · 1 optional) |

**Why `aliases` and `tools` are separate.** Retrieval scores a tool hit below a
skill-name hit and labels which kind it was, so a candidate whose only evidence
is a tool in a stack list cannot be credited as though they had named the skill
itself. Before the split, both were one list and the distinction was invisible.

### `landscape`

A flat list, same fields, for market awareness rather than engineering skill —
"where model capability sits today". Each entry needs a **dated source** before
a real bar publishes, hence the `source` field.

---

## 4. Rules a bar must satisfy

From `reference/plan/ARITHMETIC_RULES.md` §7, plus one of ours:

- `tier` ∈ `{must_know, should_know, optional}`
- `depth` values 0–4
- **`key` unique** across the whole file
- every `supported_levels` entry has a depth
- `role_key` equals the directory name
- **no spelling claimed by two skills** *(ours — `collisions()` in
  `app/skillcanon.py`)*. ARITHMETIC_RULES validates unique keys and says nothing
  about unique spellings, and a duplicate is silent: retrieval just offers both,
  so the model is asked to choose between two entries a human meant as one. The
  placeholder bar shipped with one — `"long context"`, claimed by both
  `systems.context` and `landscape.capability_limits`.

---

## 5. Choosing which bar serves

**Named in config, never discovered from the filesystem** — so an unfinished
draft cannot start serving candidates by accident. `data/config/experience_levels.yaml`:

```yaml
beachhead:
  role_key: senior_ai_engineer
  version: v0.1-placeholder
```

---

## 6. Known limits of the current placeholder

- **16 skills is too few.** Nine of eleven skills on a test AI-engineer resume
  retrieved nothing. That is *coverage*, not structure — adding entries needs no
  code change, and it is D5's job, not ours.
- **Every depth number is a placeholder**, as the file's own header says.
- **`landscape` has one entry**, carrying a placeholder source.
- **No `evidence_hints`.** A field saying what a resume line demonstrating this
  skill looks like would feed CW-4, which currently judges "is this quote about
  this skill" with nothing but the skill's name. Not added here, because writing
  those hints is authoring role content.
