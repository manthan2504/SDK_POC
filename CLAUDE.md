# Caliber Agent-SDK POC — read this before doing anything

@RULEBOOK.md

---

## 0. Session protocol

**Every session, in this order:**

1. **Read `RULEBOOK.md` fully.** It is imported above, so it is already in context — but read §2 (how we work), §3.6 (which SDK sections we use and which we refuse), §4 (architecture rules) and §16 (open decisions + every dated finding) before proposing anything. Most "good ideas" have already been settled there, with reasons.
2. **Read §2 below** — the rules that must never be broken, whatever the task looks like.
3. **Read §3 below** — where the project actually is, so you do not rebuild something that exists or claim something works that has never run.
4. **At the end of the session, update §3 of this file and RULEBOOK §1/§15.** A session that leaves the status stale has cost the next one an hour.

**This file is the dashboard. `RULEBOOK.md` is the law.** If they disagree, RULEBOOK wins and this file is out of date — fix it.

---

## 1. What this project is

A Python POC built on the **Claude Agent SDK**, reproducing Caliber's fixed 8-agent pipeline (PRD v1.7), to show the user's organisation what was learned about the SDK. The user is learning the SDK while building it.

- **Product spec:** `D:\SDKPOC\Caliber-PRD-v1.7.html` (and `-v1.6.pdf`, superseded)
- **Caliber's own design:** `reference/` — a snapshot of `D:\Caliber`, OpenClaw material stripped
- **Real Caliber repo:** `D:\Caliber` — read-only, never modify

---

## 2. Rules that are never relaxed

| # | Rule |
|---|---|
| **R1** | **No live LLM call without the user's explicit go-ahead for that run.** `run_agent()` refuses unless `CALIBER_ALLOW_LLM=1`; never set it in a shell profile, never leave it set. A previous approval does not cover the next call. |
| **R2** | **Never `git push`.** The repo is public on purpose (the org's agent reads it). Commit only when asked. |
| **R3** | **`runs/private/` holds a real person's resume.** Git-ignores it. Never print its contents — metadata, counts and short probe strings only. Never copy it elsewhere. |
| **R4** | **Secrets live in `.env`** (git-ignored). `app/envfile.py` loads **only `POC_*` keys**, so `CALIBER_ALLOW_LLM` can never be opened by a file. Never print a password or a full database URL. |
| **R5** | **Every agent uses the standard flow** (RULEBOOK §4.1/§4.2): `AgentSpec` → `run_agent()` → `build_options()` → `query()`. No agent file imports `query()`. |
| **R6** | **Never invent role content.** `data/rolebars/` skills, depths and aliases are authored by two senior engineers (PRD D5). Restructuring is fine; adding a skill or a depth number is not. See `data/rolebars/ROLE_BAR_SPEC.md`. |
| **R7** | **Report what actually ran.** "Built" and "verified live" are different claims; keep them apart in every status update. |

---

## 3. Status — last updated 2026-09-21

**Tests: 788 offline passing + 31 Postgres conformance** (`pytest`, then `pytest -m postgres`). Offline suite needs no database and makes no call.

### Pipeline steps

| Step | What | Built | Verified live |
|---|---|---|---|
| **[0]** | Extraction — PDF/DOCX → text (`app/extraction.py`) | ✅ | ✅ on the real resume |
| **[1]** | Profiler — all four workloads, below | ✅ | partial |
| **3** | Pipeline runner + Postgres (`app/pipeline/`) | ✅ | ✅ full run on Postgres |
| **[2]–[8]** | Role Analyst, Gap Analyst, Plan Builder, Question Generator, Evaluator, Guidance, Adaptation | ❌ | — |
| **11–12** | Evals (beyond CW-4's), CLI + FastAPI demo | ❌ | — |

### The Profiler's four workloads

| | Workload | Model | Built | Live | Note |
|---|---|---|---|---|---|
| **CW-1** | resume → schema | Haiku 4.5 | ✅ | ✅ ×3 | **Not repeatable** — same resume gave 2 required questions one run, 6 the next (§16.4). Needs a repeat-run count |
| **CW-2** | elicitation (wording the asks) | Haiku 4.5 | ✅ | ✅ | v1 drifted 6/8; **v2 fixed it, 0/10 drift** — the one workload verified to a standard worth defending |
| **CW-3** | skill normalise | Haiku 4.5 | ✅ | ⚠️ weak | 2/2 correct but each term had **one** candidate. Tests obedience, not judgement |
| **CW-4** | claim–evidence verdict | **Opus 5 · high** | ✅ | ❌ **never run** | `$0.50` ceiling — one call could cost more than everything spent so far. Gold set + scorer exist (`evals/cw4.py`) |

### Infrastructure

- **PostgreSQL 18** is the system of record; SQLite backs the offline tests. Same `Store` interface, conformance-tested both ways. Databases `caliber_poc` / `caliber_poc_test`, role `caliber_poc`, **separate from Caliber's own database**.
- **Git:** 73 uncommitted files, one commit ever (`173da2c`). Never pushed.
- **Live spend to date: ≈ $0.89** across ~10 approved calls. The expensive lesson: a default-config `hello.py` cost **$0.378** for one question (§3.5).

### Known problems, in the order they matter

1. **CW-1 is not repeatable.** Same input, materially different profile. Fix by measuring (N runs, count the variance), not by tweaking wording.
2. **The role bar is a placeholder.** 16 skills, 81% coverage after a tools pass, every depth number a guess. Only 3 of 37 test terms offer the model a real choice, which is why CW-3 cannot be properly tested. Authoring is D5's job (R6).
3. **CW-4 has never run**, and its budget question is unsettled.
4. **CW-2's gate checks wording, not meaning, beyond a keyword list** — good enough for the measured failures, unproven beyond them.

### Suggested next step

**[2] Role Analyst** — the first agent to slot into the pipeline runner, and the test of whether `PIPELINE.append(...)` really is all it takes. Alternatively, the CW-1 repeatability harness, which is cheap and settles problem 1.

---

## 4. Where things are

| Path | What |
|---|---|
| `RULEBOOK.md` | **The law.** Rules, SDK boundary, architecture, models per agent, open decisions O1–O21, and §16.1–16.7 — every dated finding, which is also the session history |
| `app/agents/` | `base.py` (the shared runner), `profiler.py`, `elicitor.py`, `skill_normaliser.py`, `claim_verdict.py`, `probe.py` |
| `app/pipeline/` | `store.py` (two backends), `runner.py` (sequence, retries, resume), `steps.py` (the fixed list) |
| `app/` | `extraction.py`, `candidate_profile.py`, `skillcanon.py`, `policy.py`, `schemas.py`, `textmatch.py`, `textquality.py`, `signals.py`, `vague.py`, `envfile.py`, `config.py` |
| `prompts/` | Versioned, immutable once used: `profiler.v2`, `elicitation.v2`, `skill_normalise.v1`, `claim_verdict.v1`, `probe.v1` |
| `data/rolebars/` | The role bar + `ROLE_BAR_SPEC.md` (what every field means, who may author it) |
| `evals/cw4.py` | CW-4's asymmetric cost-matrix scorer + 56-row gold set |
| `step0_demo.py` … `step3_demo.py` | Offline demos; only `step1/2` have a `--live` flag, both gated |
| `reference/plan/` | Imported Caliber design + the research documents written for this POC |
| `runs/private/` | **Real PII.** Git-ignored. See R3 |

---

## 5. Ending a session

1. `pytest -q` green, and say the number.
2. Update **§3 above** — the status table, known problems, next step.
3. Add a dated subsection to **RULEBOOK §16** for anything learned that a future session would otherwise rediscover, especially anything that cost money to find out.
4. Update **RULEBOOK §1 and §15** (status row, roadmap).
5. Leave `CALIBER_ALLOW_LLM` unset. Do not commit unless asked. Never push.
