# Caliber Agent-SDK POC — Rule Book

> **Read this first, every session.** It records where we are, how we work, what the SDK lets us use,
> and every Caliber rule the build must respect. Update §1 and §15 whenever a step finishes.
> Last updated: 2026-09-17.

---

## 1. Current situation

| | |
|---|---|
| **Goal** | Build a Python POC of Caliber's **fixed agent pipeline** ([1]→[8]) with the **Claude Agent SDK**, close to PRD v1.7, to show the org what was learned |
| **Who builds** | The user writes the code, **one agent / one step at a time**. Claude explains, scaffolds only when asked, reviews, and checks understanding |
| **SDK knowledge boundary** | Python reference understood **from the top through `PermissionResult`** (§3). Build only with that |
| **Folder** | `D:\SDKPOC\caliber-poc` (this folder) |
| **Done so far** | Folder tree · `.venv` (Python 3.11.9) · `claude-agent-sdk 0.2.154`, `pydantic 2.13.5`, `fastapi 0.141.1`, `uvicorn 0.53.0`, `pyyaml 6.0.3`, `pytest 9.1.1` · Caliber data + reference snapshot (`data/`, `reference/`) · Step 0 `hello.py` · **Step 1: shared `run_agent()` + schema rules + example probe agent** · **Step 2: Profiler (code + prompt + offline demo)** · 95 offline tests passing |
| **Not yet** | Real Caliber agents. LLM login/key parked. **No live LLM calls without the user's explicit permission** (§2 rule 7) |
| **Next step** | Optional approved live Profiler run (`step2_demo.py --live`) → Step 3 (pipeline runner + SQLite) |
| **Source of truth** | `D:\SDKPOC\Caliber-PRD-v1.7.html` (product) · `reference/` (Caliber's design, snapshot of `D:\Caliber`) · this file (POC rules) |

### 1.1 Code map

| File | What it is |
|---|---|
| `hello.py` | Step 0 throwaway test script. Nothing imports it |
| `app/config.py` | Paths, model ids (`OPUS`, `SONNET`, `HAIKU`), which models accept `effort`, the live-call gate name, default ceilings |
| `app/schemas.py` | `AgentSchema` base (extra fields forbidden) · `check_schema_rules()` enforcing §8 · `ProbeQuestion` example contract |
| `app/agents/base.py` | **The shared runner:** `load_prompt()` (text + sha256) · `fence()` · `AgentSpec` · `build_options()` (lean, isolated) · `make_tool_gate()` (`can_use_tool`) · `run_agent()` · `CallMeta` (audit facts) · errors `LLMCallsDisabled` / `AgentRunError` / `AgentOutputError` |
| `app/agents/probe.py` | Example agent (not Caliber): spec + `ask_probe(topic)` — the pattern every real agent copies |
| `prompts/probe.v1.md` | The example agent's versioned system prompt |
| `step1_demo.py` | Dry run by default (prints options, schema, user prompt). `--live` needs `CALIBER_ALLOW_LLM=1` |
| `app/rules.py` | Loads `data/config/scoring.yaml` and `experience_levels.yaml` (numbers live there, not in code) |
| `app/textmatch.py` | Grounding: `normalise_for_match()`, `GroundingText.contains()` (None/empty never counts), `mentions()` |
| `app/schemas.py` (Profiler part) | `ProfileDraft` = flat lists `roles` / `projects` / `skills` linked by ids (`r1`, `p1`) — keeps nesting at one level |
| `app/candidate_profile.py` | **Profiler code half:** grounding, date parsing, years (stated vs dated), recency, evidence cap + weaker-wins, completeness → `CandidateProfile` |
| `app/agents/profiler.py` | `PROFILER` spec (Haiku), `build_user_prompt()` (fenced resume + answers), `run_profiler()` → `ProfilerRun(draft, profile, meta)` |
| `prompts/profiler.v1.md` | Profiler system prompt (10 rules, 2 examples — one empty). A test checks the examples obey the code rules |
| `data/fixtures/ravi_resume.txt` | Synthetic resume (PRD persona Ravi, 6-yr AI engineer) |
| `data/fixtures/ravi_draft_example.json` | Hand-written model-style draft with **5 planted mistakes** for the offline demo/tests |
| `step2_demo.py` | Offline by default: request summary + code half on the example draft. `--live` needs the gate |
| `tests/` | Offline tests. `conftest.py` unsets the gate and replaces the real `query` with a tripwire; `fakes.py` = shared `FakeQuery` / `make_result` |
| `pytest.ini` | `python -m pytest -q` from the project root |

---

## 2. How we work (learning mode)

1. **One concept per step.** Explain the SDK idea → give a small task or skeleton → user writes and runs it → review → user explains it back → only then move on.
2. **Never bulk-generate the pipeline.** Boilerplate/scaffolding only when the user asks for it.
3. **Stay inside the SDK boundary (§3).** If something past it is unavoidable, flag it as a *look-ahead*, explain it, and keep it minimal.
4. **Verify SDK details against the docs** (https://code.claude.com/docs/en/agent-sdk/python) before using them. Never from memory.
5. **Every step ends with:** code runs · user can explain *why* · §1 and §15 of this file updated.
6. **Plan is not build.** Decisions marked OPEN (§16) are settled with the user before the step that needs them.
7. **No live LLM calls without explicit permission** for that run. Code is written and tested offline (fake `query`, dry runs). Live calls are gated in code: `run_agent()` refuses unless `CALIBER_ALLOW_LLM=1`, and Claude never sets it without the user's go-ahead.

---

## 3. SDK boundary — what we may use

### 3.1 Learned (allowed)
Installation · choosing `query()` vs `ClaudeSDKClient` · `query()` · `tool()` + `ToolAnnotations` · `create_sdk_mcp_server()` · session functions (`list_sessions`, `get_session_messages`, `get_session_info`, `rename_session`, `tag_session`) · `ClaudeSDKClient` · `SdkMcpTool` · `Transport` · `ClaudeAgentOptions` · `OutputFormat` · `SystemPromptPreset` / `SystemPromptCustom` / `SystemPromptFile` · `SettingSource` · `AgentDefinition` · `PermissionMode` · `EffortLevel` · `CanUseTool` · `PermissionResult`

### 3.2 Not learned yet (don't build on these)
`PermissionResultAllow/Deny` details and everything after: `ThinkingConfig`, **Message types** (`AssistantMessage`, `ResultMessage` fields), **Hook types**, errors, sandbox, etc.
- **Consequence:** the audit log and the D8 "no teaching" guard are **plain Python in the runner**, not hooks.
- **Allowed look-ahead:** the minimum of `ResultMessage` needed to read results (`subtype`, `structured_output`, cost/usage fields — confirm names in `hello.py`).

### 3.3 How each concept maps into Caliber

| SDK concept | Use in this POC |
|---|---|
| `query()` | **Every agent = one `query()` call.** Agents are stateless (FR-I7), so no `ClaudeSDKClient` |
| `ClaudeAgentOptions` | One options object per agent: own prompt, model, effort, tools, schema |
| `system_prompt` / `SystemPromptFile` | Prompts live in `prompts/<agent>.vN.md`; version + hash go in the audit record |
| `model`, `fallback_model`, `EffortLevel` | Model per agent (§10). **Never** a fallback on the Evaluator |
| `OutputFormat` / `output_format` | `{"type": "json_schema", "schema": Model.model_json_schema()}` = the agent's output contract |
| `tool()` + `create_sdk_mcp_server()` | Only where §16-O1 allows. Tool names in `allowed_tools` are `mcp__<server>__<tool>` |
| `tools`, `allowed_tools`, `disallowed_tools` | `tools=[]` drops built-in tools (verified, §3.5). `allowed_tools=[]` so nothing bypasses the gate. `allowed_tools` only auto-approves; it does **not** restrict |
| `CanUseTool` → `PermissionResult` | Shared callback: **deny any tool not on that agent's list** — code-enforced "stay in your lane" |
| `PermissionMode` | Default, so unlisted tools fall through to `can_use_tool` and are denied |
| `SettingSource` | `setting_sources=[]` so the user's Claude Code settings / CLAUDE.md never leak into Caliber agents |
| `max_turns`, `max_budget_usd`, `cwd` | Per-step turn and cost ceilings; fixed working dir |
| Session functions | Optional: store each step's session id on `StepRun` for audit replay |
| `AgentDefinition` / `agents=` | **Deliberately NOT used** — subagents = delegation, which D11 forbids |
| `Transport` | Not needed |

### 3.4 Verified SDK facts (docs, 2026-09-17)
- Package `claude-agent-sdk`; Python ≥ 3.10; bundles its own Claude Code binary.
- `query(*, prompt, options=None, transport=None) -> AsyncIterator[Message]`; iterate with `async for`.
- Structured output: pass `output_format={"type": "json_schema", "schema": ...}`; the final `ResultMessage` carries `structured_output`. Treat as success **only** when `subtype == "success"` **and** `structured_output` is present.
- Schema failure after the SDK's own retries → `subtype == "error_max_structured_output_retries"`. A single-shot `query()` raises after yielding an error result → wrap in `try/except`.
- The SDK validates JSON Schema **draft-07**; `Model.model_json_schema()` is the documented Pydantic path. `format` is annotation-only.
- `CanUseTool = Callable[[str, dict, ToolPermissionContext], Awaitable[PermissionResult]]`; `PermissionResultAllow(updated_input=None)`, `PermissionResultDeny(message, interrupt=False)`. Called **only** when a call is not already auto-approved.
- `setting_sources=None` loads user + project + local settings (CLI default); `[]` disables them.
- The SDK does **not** load `.env` files by itself.
- Read from the installed SDK source (0.2.154): `EffortLevel = low|medium|high|xhigh|max`; `PermissionResultDeny(message='', interrupt=False)`; a tool listed in `allowed_tools` skips `can_use_tool` (the SDK warns about this "shadowing"), so we keep `allowed_tools=[]` and let the gate decide.
- `output_format` results arrive through an internal tool named **`StructuredOutput`** (seen in the Ollama test) — the gate always allows it.

### 3.5 Observed in `hello.py` (2026-09-17, SDK 0.2.154, Claude Code login)
- **Stream order:** `SystemMessage` → `RateLimitEvent` → `AssistantMessage` → `ResultMessage` (the lean run showed extra `SystemMessage`s and two `AssistantMessage`s — don't rely on exact counts; filter by type).
- **`ResultMessage` fields seen:** `subtype`, `is_error`, `result`, `structured_output`, `stop_reason`, `terminal_reason`, `num_turns`, `duration_ms`, `duration_api_ms`, `session_id`, `uuid`, `total_cost_usd`, `usage` (input/output/cache tokens), `model_usage` (per model: tokens, `costUSD`, `canonicalModel`), `permission_denials`, `errors`, `api_error_status`.
- `RateLimitEvent` appears because the run uses the Claude Code (subscription) login. `total_cost_usd` is a list-price estimate.
- **Defaults are expensive.** With no `model`, `tools` or `setting_sources`, the run inherited the user's Claude Code model (`claude-opus-5[1m]`) and loaded **37,565 input tokens** of context → **$0.378** for one question.
- **Lean config:** `model="claude-haiku-4-5"`, `tools=[]`, `setting_sources=[]` → **434 input tokens, $0.0027**. `tools=[]` + `setting_sources=[]` work as intended (O7 resolved).
- **Rule:** every agent's options **must** set `model`, `tools=[]` (plus only its own MCP tools), and `setting_sources=[]`.
- **First live `run_agent()` (probe agent, Haiku, approved by the user, 2026-09-17):** `subtype=success`, valid `ProbeQuestion`, `stop_reason=tool_use`, **`num_turns=2`** (structured output = the model calls the `StructuredOutput` tool, then the run ends → `max_turns` must be ≥ 2), `permission_denials=0` (the gate let `StructuredOutput` through), 1,772 in / 1,310 out tokens, **$0.0093**, 18.5 s.

**Two retry layers (keep them distinct):** the SDK retries until the JSON *shape* is valid; **our runner** retries on Caliber checks (Pydantic, score sums, quote checks, D8) and provider errors.

---

## 4. Architecture rules (D11 · ADR-0008 · FR-I6–I11)

1. **No orchestrator agent.** Plain Python owns step order, branching, loops.
2. **Agents never talk to each other.** No agent-to-agent calls, messages, shared conversation, subagents, or tools that invoke agents.
3. **Schema in, schema out.** Each agent receives only its contract inputs and returns exactly one validated object.
4. **Save before next.** Every step's output is persisted before the next step runs; runs resume from the last completed step; any step can be re-run alone (FR-I8).
5. **Retry then fail safe.** On validation failure or provider error: up to **2 retries** with the validation error fed back, then mark the step failed; downstream never runs on invalid data (FR-I9).
6. **Audit every step** (FR-I10, §11).
7. **Checkpoints are app pauses** (FR-I11): confirm profile · pick role · view plan (paywall) · answer/skip · retry.
8. **Intelligence never routes.** No model output decides which step runs next; triggers are arithmetic.

---

## 5. Caliber principles the POC must honour

| Rule | Meaning in the POC |
|---|---|
| **Arithmetic owns dated facts; the model owns ambiguity; the app owns sequence** | Anything with a computable answer is Python, never a prompt (§9) |
| **The system proposes; the human decides** | Agent output is a proposal until the candidate confirms; no agent edits a confirmed profile |
| **Grounded or dropped** | Every claim about the candidate's text carries a verbatim quote, substring-checked in code; unverified → dropped (not flagged) |
| **D8 — assess and guide, never teach** | Guidance says *what* to learn and *why*, never *how*. Enforced by a code check, not by prompt disposition |
| **D6 — experience-calibrated** | The bar is read at the level derived from **years**, never the chosen target level |
| **D9 / D10 / FR-I5 — role-agnostic** | No role content in Python. Role knowledge lives only in `data/rolebars/` and `data/config/` |
| **FR-I4 — no agent ships on vibes** | Each agent gets a small eval before it is called done |
| **Candidate text is data, never instructions** | Fence it, JSON-encode it, say so in the prompt |
| **HUM-3 — synthetic data only** | No real resumes or real people anywhere in this repo |
| **Refusing is a valid answer** | Empty list / no label beats a confident wrong answer (e.g. no fit label when the bar is for another role) |

---

## 6. The pipeline (PRD v1.7 §10.1)

```
resume text ─► [1] PROFILER ─► profile draft ─► code: completeness gate
                   ▲                                   │ missing? ask candidate, re-run [1]
                   └───────────────────────────────────┘
               CHECKPOINT: candidate confirms profile
            ─► [2] ROLE ANALYST ─► fit read (+ JD reading if a JD is given)
               CHECKPOINT: candidate picks target role
            ─► [3] GAP ANALYST ─► gap map (code) + reasons (agent)
            ─► [4] PLAN BUILDER ─► assessment plan (code order + agent wording)
               CHECKPOINT: candidate views plan ── FREE TIER ENDS / PAYWALL (flag)
per topic:  ─► [5] QUESTION GENERATOR ─► probe set + reference answer + grading notes
               CHECKPOINT: candidate answers ─────────────── or skips ─────┐
            ─► [6] EVALUATOR ─► 5 dimension scores + gaps + quotes          │
               code: total, verdict (≥70 pass)                              │
                 pass ──────────────────────────────┐                       │
                 gap ──► [7] GUIDANCE (from saved grade only)               │
                                                    ▼                       ▼
            ─► [8] ADAPTATION ─► picks from an app-provided menu; app applies
               code: topic state + readiness score
               ─► next topic │ candidate-initiated retry → [5] fresh variant │ done
```

---

## 7. Agent contracts (code part vs agent part)

"CW" = Caliber's workload id (`reference/llm/workloads.md`). Exact schemas are designed at each step.

| # | Agent | Code does | Agent does | Input (only this) | Output |
|---|---|---|---|---|---|
| 1 | **Profiler** (CW-1, CW-4 style) | Completeness gate + `missing_fields`; evidence ladder; recency; verifies every copied field/quote; keeps the **weaker** of code rating vs agent verdict | Structures resume text into roles/projects/skills, copying names & dates **verbatim**; per-skill "what does the text show" verdict + quote | Resume text (+ previous draft on re-run) | Profile draft (nullable fields, `analysis` first) |
| 2 | **Role Analyst** (CW-5, CW-6) | Level from years (clamped to bar's levels); loads bar; coverage; fit label; direction (overshoot/undersell/aligned) | Narrates the standing read it is **handed** (cannot change the label); optional: labels JD segments against bar sub-skill keys | Level, label, direction, top gaps, gaps_total (+ JD segments) | Standing narrative (level echo, direction echo, standing, reach, distance) |
| 3 | **Gap Analyst** (CW-7) | **The whole gap map** (§9): gap size, priority, bucket, order | Plain-English reason per gap; **every number must appear verbatim in its input** | Gap rows (numbers precomputed) | Reasons keyed by sub-skill |
| 4 | **Plan Builder** (CW-8) | One topic per open gap, priority order; topic set is fixed | For each topic: what it probes, why it's here (tied to profile + bar), question types from `how_tested`. May not add/drop topics | Gap map, bar sub-skills, profile projects | Assessment plan |
| 5 | **Question Generator** (CW-9/12) | Difficulty; prior question list; checks the new variant isn't a repeat | 7-question probe set grounded in the candidate's own project **plus reference answer + grading notes** | Topic, candidate projects, bar sub-skill, difficulty, prior questions | Question set |
| 6 | **Evaluator** (CW-13) | Sum of dimensions; verdict (≥70); quotes found in answer; median-of-3 in borderline band; harshness offset (0 for now); **never cached** | Scores 5 dimensions with **reasoning before scores**, lists gaps + evidence quotes | Question, answer, rubric, reference answer, grading notes, level expectation | Grade |
| 7 | **Guidance** (CW-14) | D8 no-teaching check; length limits | What to strengthen, why it matters at this level, kind of resource, optional Socratic hint | **Only** the saved Grade + topic + role + level | Guidance |
| 8 | **Adaptation** (menu-only) | Triggers; builds the menu of allowed moves; applies the choice | Picks one move from the menu with a reason | Plan + topic states, latest grade/skip, attempt history, menu | Chosen move |
| — | *(no agent)* | Readiness score, topic state machine, paywall flag | — | — | — |

---

## 8. Output-schema rules (both Caliber and Agent SDK friendly)

1. **Reasoning first:** every object starts with `analysis: str` (one or two sentences).
2. **Evidence before label:** `quote` comes before the verdict/skill/score it justifies.
3. **Required-and-nullable, no defaults:** `x: str | None` with **no** `= None` (defaults change what is sent to the model).
4. `model_config = ConfigDict(extra="forbid")`.
5. **Banned in schemas:** `Any`, `dict[str, Any]`, `pattern`, `minLength/maxLength`, `minimum/maximum`, `minItems>1`, `maxItems`, `uniqueItems`, `multipleOf`, `allOf/oneOf/not`, recursion. Put bounds in Pydantic validators **after** parsing.
6. **Closed vocabularies:** `Literal[...]`; sub-skill keys built **from the loaded bar at runtime**, never typed in Python.
7. **Keep it flat.** Deep/complex schemas lower recall; one level of nesting max.
8. **The model never emits a number that code can compute** (totals, labels, comparisons, multipliers).
9. **Class docstrings and `Field(description=...)` are sent to the model** as schema `description`s — write them for the model, or leave them out.
10. `check_schema_rules(Model)` must return `[]` for every agent contract (a test per agent).

---

## 9. Arithmetic reference (lives in code, reads `data/config/*.yaml`)

**Levels (`experience_levels.yaml`):** junior 0 · mid 2 · senior 5 · staff 9 · principal 14 years (lower bound inclusive). Bar supports `mid, senior, staff` → **clamp to nearest and tell the candidate**. Unknown years → no level → no gap map, no label.

**Ordinals:** depth `none 0 · aware 1 · can_build 2 · can_design 3 · can_defend 4` · evidence `none 0 · mentioned 1 · demonstrated 2 · led 3` (evidence→depth is identity). **Capture ceiling = 3**; depth 4 is earned only by passing an assessment.

**Gap map (`gap-scoring-v1`):**
```
required      = bar.depth[sub_skill][calibration_level]     # 0 → out of scope
demonstrated  = evidence_rank(profile, sub_skill)            # 0 if unmatched; 4 after a pass
gap_size      = max(0, required - demonstrated)              # 0 → proven, not in map
weight_norm   = weight / 5
recency       = current|recent 1.00 · dated(>36 mo) 1.25 · unknown 1.10 · no evidence 1.00
priority      = round(gap_size * weight_norm * recency, 2)
order         = priority desc → weight desc → bar order
```

**Buckets (`gap-buckets-v1`), first match wins:** landscape item (if gap>0) → `ai_landscape` · `probe_first` → `claimed_but_unproven` (even at gap 0) · gap 0 → proven (excluded) · tier from required depth: 3–4 `must_know`, 2 `should_know`, 1 `optional`. Display order: must_know, should_know, claimed_but_unproven, optional, ai_landscape. Headline count = must_know + claimed_but_unproven.

**Fit label (`fit-labels-v1`):** over rows with required>0 and required<4:
`coverage = Σ(weight × min(demonstrated, required)) / Σ(weight × required)`.
Strong fit = coverage ≥ 0.85 **and** no must_know gap **and** no unproven depth-4 row · Stretch ≥ 0.55 · else Not yet. No label if bar ≠ target role or years unknown. Direction: target > calibrated → overshoot · < → undersell · equal/none → aligned. Reach coverage computed separately at target level.

**JD overlay (`jd-overlay-v1`, later):** changes emphasis only — weight ×[0.5, 2.0] (result clamped [0.1, 1.0]), tier up one step; never depth, level or the sub-skill set; ≤40% of sub-skills; every entry needs a verbatim JD quote. The agent emits `leading|required|mentioned`; code maps it to a multiplier.

**Topic states (FR-C4):** `not_started → in_progress → passed | gap_open | skipped`; `gap_open → in_progress` on retry; `skipped` stays an open gap. A pass lifts that sub-skill's demonstrated depth to 4.

**Readiness (POC choice — Caliber hasn't built it):** over topics in must_know / should_know / claimed_but_unproven:
`readiness % = 100 × Σ(weight of passed topics) / Σ(weight of all those topics)`. Optional and landscape never count against it.

---

## 10. Models per agent (for later — LLM setup is parked)

From `reference/llm/dev-cycle.md` §10.4. Model ids: `claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5` (full id `claude-haiku-4-5-20251001`).

| Agent | Model | Effort | Hard constraints |
|---|---|---|---|
| [1] Profiler | Haiku 4.5 | **don't send** | Haiku rejects `effort` |
| [2] Role Analyst — narrative | Opus 5 | medium/high, **never max** | **Never Sonnet 5** (measured 9.1% sycophancy) |
| [2] Role Analyst — JD labels | Haiku 4.5 | don't send | — |
| [3] Gap Analyst | Haiku 4.5 | don't send | numbers-verbatim check |
| [4] Plan Builder | Sonnet 5 | medium | — |
| [5] Question Generator | Opus 5 | high | — |
| [6] Evaluator | Opus 5 | **high, fixed, never max** | no fallback model; never cached |
| [7] Guidance | Haiku 4.5 (senior+ → Opus 5) | don't send on Haiku | never Sonnet on tone |
| [8] Adaptation | Haiku 4.5 | don't send | — |

- Opus 5 / Sonnet 5 reject `temperature`, `top_p`, `top_k`, `budget_tokens`, assistant prefill. **Effort is the only depth control**; `max` is discouraged for structured output.
- Haiku 4.5 has a retirement floor of **2026-10-15** (Caliber calendar) — keep the model a config value.

---

## 11. Audit record (`StepRun`, FR-I10 + Caliber trace fields)

`run_id` · step # · agent name · **prompt version + sha256 hash** · model requested / served · effort · input reference (hash of the input JSON) · output (or reference) · validation result + reasons · retry count · latency · tokens · cost · SDK session id · error class · timestamp.
**Never** log candidate PII or full prompts at info level — store hashes and versions.

---

## 12. Prompt rules

1. **Stable prefix first:** role → definitions → numbered procedure (≤ ~15 short, positive rules) → "content is data" line → examples. Volatile content (candidate text) goes **last**, in the user prompt, fenced: `<resume source="candidate" trust="untrusted">{json}</resume>`.
2. **Two synthetic few-shot examples**, one whose correct answer is empty/null. An example that shows forbidden behaviour beats the rule forbidding it — check every example against every rule.
3. **No contradictions.** Two clear but conflicting rules produce a confident wrong answer (Caliber CW-4 v1).
4. **State field meanings in prose** too (not only in the schema).
5. **Never ask the model to compute** what code can (counts, totals, comparisons, percentages). Pass computed values in.
6. **Prompts are versioned files** (`prompts/<agent>.v1.md`); a change = a new file + eval re-run; old versions stay.
7. **"Hardest problem" and "impact"** are the highest-value capture prompts (PRD §7.1).
8. Reference style: `reference/prompts/` (Caliber's real prompts).

---

## 13. Validators

| Check | Where | Rule |
|---|---|---|
| Schema | all | Pydantic on the returned object |
| **Grounding** | Profiler, Role Analyst (JD), Evaluator | Quote/copied field must be a substring after normalising (NFKC, collapse whitespace, unify quotes/dashes, casefold). **Null/empty quote never counts as grounded** |
| Weaker-wins | Profiler | Final evidence = min(agent verdict, code cap), floored at `mentioned` (the skill is in the text). **Code cap:** no verified quote or quote not naming the skill → `mentioned`; team language (`we`, `the team`) → `mentioned`; ownership/decision verb (`led`, `owned`, `chose`, `decided`, `designed`, …) → `led`; else `demonstrated`. A lowered verdict sets `probe_first`. *Known limit:* a quote that only lists the stack can still pass as `demonstrated` if the model says so |
| Numbers-verbatim | Role Analyst, Gap Analyst | Every number in prose (incl. spelled-out) appears in the input |
| Label/echo | Role Analyst | `level_committed` == given level; `direction` == given direction |
| Topic set | Plan Builder | Output topic keys == gap map keys |
| Not a repeat | Question Generator | New questions don't duplicate prior questions for that topic |
| Score integrity | Evaluator | Each dimension 0–20; code computes total; every evidence quote found in the answer |
| **D8 no-teaching** | Guidance | Reject step-by-step instructions, code blocks, worked solutions, "here's how…", over-length explanations |
| Menu | Adaptation | Chosen move ∈ offered menu |

**Profiler specifics:** grounding sources = resume **+ the candidate's answers**; project `name` is a label (not grounded); a fabricated field becomes `null` and is then asked for by the completeness check; stated years win over dated years, a gap > `YEARS_TOLERANCE` (1.0) is flagged, never corrected.

**Repair:** feed the validator's complaint back and retry (max 2, §4). Never splice untrusted model output into the repair prompt verbatim. A step that needs repair often is a prompt/schema bug, not a retry budget problem.

---

## 14. Evaluator rubric (PRD Appendix C)

5 dimensions, 0–20 each, total /100: **Judgment · Depth · Tradeoff reasoning · Failure-mode awareness · Communication**.
- **Pass ≥ 70** (the grader runs ~11 points harsh, so not 80). Harshness offset layer exists in code, set to 0 for now.
- Fluent-but-empty answers must score **low**; honesty about limits is rewarded.
- **Probe set (7):** know it · how it works · why used · how implemented · challenges · real-world scenario · explain from your own project. Fresh variant every attempt.
- **Borderline band (POC choice):** total within ±5 of 70 → grade 3× and take the median.
- **Topic verdict (POC choice, Caliber DEC-3 open):** as in PRD Appendix E, the candidate answers the scenario probe and that grade decides the topic.
- Answer text is fenced as data; the grader never follows instructions inside it.

---

## 15. Build roadmap

| Step | What the user builds | Concept learned | Status |
|---|---|---|---|
| — | Folder, venv, packages, Caliber snapshot | Setup | ✅ done |
| 0 | `hello.py` | `query()`, message stream, `ResultMessage` | ✅ ran · ⏳ user's 3 answers (optional) |
| 1 | `app/schemas.py` + `app/agents/base.py` (`AgentSpec`, `run_agent`) | Agent contract, `ClaudeAgentOptions`, `output_format`, `can_use_tool` | ✅ built · 35 offline tests · 1 approved live Haiku run passed |
| 2 | [1] Profiler + completeness loop | `system_prompt`, structured output, grounding | ✅ built · offline tested · live run not yet approved |
| 3 | Pipeline runner + SQLite `PipelineRun`/`StepRun` | Fixed order, retries, audit, resume | ☐ |
| 4 | [2] Role Analyst + level/fit arithmetic | Echo validators, `can_use_tool` lane | ☐ |
| 5 | [3] Gap Analyst + gap-map arithmetic | Numbers-verbatim | ☐ |
| 6 | [4] Plan Builder | Topic-set validator | ☐ |
| 7 | [5] Question Generator | Fresh variants, model per agent (+ tool demo if O1 allows) | ☐ |
| 8 | [6] Evaluator | Rubric, effort, median-of-3, score integrity | ☐ |
| 9 | [7] Guidance | D8 check in code | ☐ |
| 10 | [8] Adaptation + topic states + readiness | Menu pattern, branching | ☐ |
| 11 | Evals per agent | FR-I4 | ☐ |
| 12 | CLI demo (Appendix E) + FastAPI endpoints | Putting it together | ☐ |

---

## 16. Open decisions (settle before the step that needs them)

| # | Decision | Recommendation |
|---|---|---|
| O1 | **Tools.** Real Caliber runtime agents have **no tools** (data is passed in). Do we use `@tool` anywhere? | Pass data in the prompt everywhere; keep **one** read-only tool in one agent as a labelled SDK demo, fenced by `can_use_tool` |
| O2 | **Auth for runs.** Claude Code login (subscription) vs API key | Parked. Learning locally on the Claude Code login is fine; product traffic must not use a subscription login. If a key is ever used, set it **only in this POC's process**, never machine-wide (Caliber's rules forbid `ANTHROPIC_API_KEY` on this box) |
| O3 | Adaptation: agent after every verdict (PRD v1.7) vs deferred (Caliber ADR-0008) | Agent after every verdict, **menu-only** — satisfies both |
| O4 | Retries: PRD says 2, Caliber code does 1 | 2 (PRD wins) |
| O5 | Storage | SQLite in `runs/` |
| O6 | Readiness formula, borderline band, topic verdict rule | POC choices in §9 / §14 until Caliber decides |
| O7 | ~~`tools=[]` really removes built-ins?~~ | **Resolved 2026-09-17:** yes — see §3.5 |

---

## 17. Scope

**In:** the [1]–[8] pipeline for Senior AI Engineer · checkpoints as CLI prompts / API endpoints · SQLite persistence + audit · arithmetic layer · per-agent evals (small) · Appendix E demo.
**Out:** orchestrator/router agents · agent-to-agent anything · teaching content · auth, payments (paywall = flag), frontend, Postgres, Azure · other roles · Phase 2 (Interviewer, outcome loop) · repo/code ingestion (D1) · resume file parsing beyond plain text.
**Framing for the demo:** real Caliber calls Claude through its provider layer (Messages API / OpenClaw gateway); this POC shows how Caliber's pipeline looks with **Claude-backed steps on the Agent SDK**. The SDK is Claude-only (D10 caveat).

---

## 18. Demo story (PRD Appendix E)

Synthetic resume → Profiler → confirm → Role Analyst → pick role → gap map → plan (RAG topic is must-know) → Question Generator writes a probe from the candidate's own RAG project → buzzword answer → Evaluator **~21 → gap** ("claims RAG eliminates hallucinations") → Guidance: *go learn reranking, hybrid search, chunk-boundary failure, faithfulness vs relevance* (no teaching) → Adaptation: keep RAG open, move on → retry → **fresh variant** → good answer **~86 → pass** → readiness rises → audit log shows every step.

---

## 19. Environment notes (Windows)

- Python is `py` (plain `python` is the Store stub). Venv: `.venv\Scripts\Activate.ps1` (if blocked: `Set-ExecutionPolicy -Scope Process RemoteSigned`).
- Don't upgrade pip inside the venv on this box — it broke once on a file lock (venv was recreated).
- `pdftotext` exists in Git Bash (`/mingw64/bin`); `pdftoppm` does not.
- Real Caliber repo: `D:\Caliber`. Treat it as read-only from this project. Never copy its `.env` or `ops/.openclaw-token`.
- Needed later: `pip install pyyaml` (to read `data/*.yaml`).

---

## 20. Glossary

**Role-bar** — versioned YAML of what a role is tested on, depth per level. · **Sub-skill** — one bar row (`retrieval.rag_design`). · **Calibration level** — level from years (D6). · **Target level** — the candidate's ambition. · **Evidence strength** — none/mentioned/demonstrated/led. · **Gap map** — prioritised, bucketed gaps. · **Probe-first** — a claim the evidence doesn't back; tested first. · **Checkpoint** — pipeline pause for the candidate. · **StepRun** — one agent call + its audit record. · **CW-n** — Caliber workload id. · **Grounded or dropped** — quote must be verbatim or the claim is discarded. · **D-numbers** — PRD locked decisions (D1–D11). · **FR-I** — PRD AI-pipeline requirements.

## 21. Where things came from

PRD v1.7 (`../Caliber-PRD-v1.7.html`) · handoff (`../CALIBER-POC-CONTEXT.md`) · Caliber snapshot (`reference/README.md` indexes it) · SDK docs: `/agent-sdk/python`, `/agent-sdk/structured-outputs`, `/agent-sdk/quickstart`.
