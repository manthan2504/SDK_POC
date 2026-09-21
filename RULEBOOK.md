# Caliber Agent-SDK POC — Rule Book

> **Read this first, every session.** It records how we work, what the SDK lets us use, and every Caliber
> rule the build must respect. Update §1 and §15 whenever a step finishes.
>
> **`CLAUDE.md` is the dashboard** — current status, the never-relaxed rules, and the session protocol.
> **This file is the law.** If the two disagree, this file wins and `CLAUDE.md` is stale; fix it.
> §16.1–16.7 are the dated findings, and double as the history of what previous sessions learned.
> Last updated: 2026-09-21 (live run + fixes).

---

## 1. Current situation

| | |
|---|---|
| **Goal** | Build a Python POC of Caliber's **fixed agent pipeline** ([1]→[8]) with the **Claude Agent SDK**, close to PRD v1.7, to show the org what was learned |
| **Who builds** | The user writes the code, **one agent / one step at a time**. Claude explains, scaffolds only when asked, reviews, and checks understanding |
| **SDK surface** | **Whole Python reference in scope** (2026-09-21 — the old "up to `PermissionResult`" limit is lifted). Anything unused is now a *design* choice with a reason in §3.6 |
| **Folder** | `D:\SDKPOC\caliber-poc` (this folder) |
| **Done so far** | Folder tree · `.venv` (Python 3.11.9) · `claude-agent-sdk 0.2.154`, `pydantic 2.13.5`, `fastapi 0.141.1`, `uvicorn 0.53.0`, `pyyaml 6.0.3`, `pytest 9.1.1` · Caliber data + reference snapshot (`data/`, `reference/`) · Step 0 `hello.py` · **Step 1: shared `run_agent()` + schema rules + example probe agent** · **Step 2: Profiler v1.1** (prompt v2, Path A + Path B, all PRD §7.1 fields, answer-quality gate, vague terms, ownership / seniority / depth signals, `cw-1` tag) · **v1.2 review fixes** (independent review: 7 bugs + 9 gaps fixed) · **Step [0] document extraction** (`app/extraction.py`, ported from Caliber + 3 fixes) · **N2 stream reading** (§3.6) · **first live run** (§16.2) → word-spacing fix (O21) + paid-result salvage · **Step 3: pipeline runner + SQLite** (sequence, retries, resume, checkpoints, audit) · **PostgreSQL as system of record** (SQLite kept for the offline suite) · **all four Profiler workloads built**: CW-1/2/3 (Haiku) + **CW-4 claim verdict (Opus 5 · high)**, CW-4 never run · **role-bar upgrades** (aliases/tools split, stated scales, collision lint) · **788 offline tests + 31 Postgres conformance tests passing** |
| **Not yet** | Real Caliber agents. LLM login/key parked. **No live LLM calls without the user's explicit permission** (§2 rule 7) |
| **Next step** | Step 4 — [2] Role Analyst (the first agent to slot into the runner, and the test of whether `PIPELINE.append(...)` is all it takes). Cheap alternative first: the CW-1 repeatability harness (§16.4 / known problem 1) |
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
| `app/policy.py` | **Every Profiler threshold and word list** (mirrors Caliber `policy.py`): text-quality field specs, decision/quantity/causal words, vague terms, lead roles, seniority thresholds, depth-score constants, team-size parsing, education years, clipping limits. Change a value → bump `POLICY_VERSION` |
| `app/textquality.py` | Answer-quality ladder empty < noise < thin < substantive < specific (`read_text`, `read_project_fields` with near-duplicate demotion) |
| `app/vague.py` | `is_vague_skill()` / `vague_reason()` — "various tools", "cloud technologies"… are never skills |
| `app/signals.py` | Ownership level, seniority signals (scope / tradeoffs / ambiguity / cross-team), per-skill depth score, team size + people-leading from a team quote, education weight |
| `app/textmatch.py` | Grounding: `normalise_for_match()`, `GroundingText.contains()` (None/empty never counts), `mentions()` |
| `app/schemas.py` (Profiler part) | `ProfileDraft` **v2** = flat lists `roles` / `projects` / `skills` / `educations` linked by ids (`r1`, `p1`); every quote field comes before the label it justifies (`role_quote` → `your_role`) |
| `app/candidate_profile.py` | **Profiler code half:** grounding, dates, years (stated vs dated), recency, `your_role` check (team language never supports led/owned/built_solo), vague stack items split off, evidence cap + weaker-wins, depth score, ownership + seniority signals, education, clipping, completeness (**required** vs **optional** questions; thin answers re-asked) → `CandidateProfile` |
| `app/agents/profiler.py` | `PROFILER` spec (Haiku, prompt **v2**, `cw="cw-1"`), `build_user_prompt()` — **Path A** resume (+ answers) or **Path B** answers only — `run_profiler()` → `ProfilerRun(draft, profile, meta)` |
| `prompts/profiler.v1.md`, `profiler.v2.md` | v1 kept (immutable). **v2** is live: 14 rules, 2 examples (a resume, and an empty answers-only case). Tests check the examples obey the rules and pass the code unchanged |
| `data/fixtures/ravi_resume.txt` | Synthetic resume (PRD persona Ravi, 6-yr AI engineer) |
| `data/fixtures/ravi_draft_example.json` | Hand-written v2 model-style draft with **7 planted mistakes** (fabricated title, fabricated skill, quote about another skill, two team-language over-claims, team-language `your_role: led`, vague stack item) |
| `step2_demo.py` | Offline by default: request summary + code half on the example draft. `--live` needs the gate |
| `app/extraction.py` | **Step [0], no model:** PDF (pdfplumber, column-aware) and DOCX (python-docx, incl. table cells) → plain text. `Extraction(text, pages, layout)` · `load_resume_text()` → `ResumeSource` · errors `UnsupportedFileType` (415) / `FileTooLarge` (413) / `UnreadableDocument` (400) / `NoTextLayer` (422), all `ValueError` subclasses |
| `data/fixtures/extraction/` | **9** synthetic files: 1-column, two-column (two draw orders), table+bullets, DOCX, scanned/image-only, truncated, not-a-PDF, **tight-spacing** (every glyph placed individually, no space characters — the only one that reproduces O21) |
| `scripts/make_extraction_fixtures.py` | Regenerates those fixtures (needs `reportlab`, dev only) |
| `step0_demo.py` | Extraction over the fixtures or a real file. **No `--live` flag exists** — this step never calls a model |
| `data/rolebars/ROLE_BAR_SPEC.md` | **What a role bar is and what every field means** — who authors it (D5: two seniors for the beachhead, agent-generated + expert-reviewed for the rest), the depth/weight scales, `aliases` vs `tools`, the validation rules, and the current placeholder's known limits |
| `app/agents/claim_verdict.py` | **CW-4 (Opus 5 · high, `cw-4`)** — the only non-Haiku agent. Judges whether a *real* quote is **about** the skill, on the four-level ladder. `demote_only()` is the gate: CW-4 may lower a verdict, never raise it. **Never run live** |
| `prompts/claim_verdict.v1.md` | 14 rules; the four levels made operational; the D10 Terraform case as a worked **wrong** answer |
| `evals/cw4.py` | The CW-4 eval gate: **asymmetric** cost matrix (over-crediting costs far more than under-crediting), confusion matrix, per-slice scores. `python -m evals.cw4` prints a perfect-run report, no model call |
| `data/fixtures/cw4_gold.json` | 56 hand-labelled claims — 19 in the **D10 slice**. Synthetic and single-rater; a stand-in for the human-rated set the reference requires |
| `app/pipeline/store.py` | **Two backends, one vocabulary** (§16.3): `PostgresStore` (system of record) and `SqliteStore` (offline tests, demos), chosen by `POC_DATABASE_URL`. Tables: `runs` · `step_runs` (**one row per attempt**, failures included, opened *before* the call) · `checkpoints` · `run_inputs` (the run's own material — step [1]'s input is nobody's output). `Store.completed()` is what a resume reads instead of re-calling; `Store.cost()` counts failed attempts too |
| `app/pipeline/runner.py` | **The sequence, in plain Python (D11):** `classify()` (N1 retry verdicts) · `run_step()` (attempts, repair feedback, audit rows) · `run_pipeline()` (order, save-before-next, resume, pauses). No agent is imported here |
| `app/pipeline/steps.py` | The fixed step list. Today: `PROFILER_STEP` (+ `ANSWERS_NEEDED` / `CONFIRM_PROFILE` checkpoints). Agents [2]–[8] append to `PIPELINE`; `runner.py` does not change |
| `step3_demo.py` | The runner end to end with a fake agent: a repair retry, a completeness pause, a resume, a confirm. `--runs` lists stored runs |
| `tests/` | Offline tests. `conftest.py` unsets the gate and replaces the real `query` with a tripwire; `fakes.py` = shared `FakeQuery` / `make_result` |
| `pytest.ini` | `python -m pytest -q` from the project root |

---

## 2. How we work (learning mode)

1. **One concept per step.** Explain the SDK idea → give a small task or skeleton → user writes and runs it → review → user explains it back → only then move on.
2. **Never bulk-generate the pipeline.** Boilerplate/scaffolding only when the user asks for it.
3. **Use the SDK deliberately (§3).** The whole reference is in scope; before adopting a section, say which Caliber rule it serves and add it to §3.6. Unused ≠ unknown.
4. **Verify SDK details against the docs** (https://code.claude.com/docs/en/agent-sdk/python) before using them. Never from memory.
5. **Every step ends with:** code runs · user can explain *why* · §1 and §15 of this file updated.
6. **Plan is not build.** Decisions marked OPEN (§16) are settled with the user before the step that needs them.
7. **No live LLM calls without explicit permission** for that run. Code is written and tested offline (fake `query`, dry runs). Live calls are gated in code: `run_agent()` refuses unless `CALIBER_ALLOW_LLM=1`, and Claude never sets it without the user's go-ahead.
8. **No SDK section is off-limits.** Every part of the Python reference may be used; what we leave out is refused in §3.6 with a reason (D11, offline testability, cost), never "not learned yet".
9. **Every agent uses the standard flow in §4.1 and the detailed call sequence in §4.2** (`AgentSpec` → `run_agent()` → `build_options()` → `query()`, with agent-specific work only before and after the shared middle); new agents copy it and never call the SDK directly.

---

## 3. SDK surface — what we use, and what we refuse

### 3.1 The whole reference is in scope (from 2026-09-21)
The earlier limit — "understood from the top through `PermissionResult`, build only with that" — is **lifted**.
Every section of the Python reference is now available: `ThinkingConfig`, all message and content-block types,
hooks, errors, sandbox, sessions and `SessionStore`, `TaskBudget`, betas, plugins, skills.

**What changes in practice:** nothing we already built is wrong; it gains reasons. From here, a section we do
*not* use must be refused in §3.6 with a design reason (D11, offline testability, cost, statelessness) —
"not learned yet" is no longer an answer, and neither is using something merely because it exists.

### 3.2 The two decisions the old boundary forced (both still stand, now by choice)
- **Audit log and the D8 "no teaching" guard stay plain Python in the runner, not hooks.** A hook only fires
  while a session is running; our guarantees must also hold in the 788 offline tests, on a saved `StepRun`, and
  on a re-validated result. Code that runs in both places is the stronger guard. Hooks may still be added as a
  *second* lane check (§3.6).
- **`ResultMessage` is read in full** (§3.5 lists the observed fields) — that was the "allowed look-ahead" and is
  now simply the contract.

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
| `Transport` | Not needed — the bundled CLI transport is the one we want |
| SDK error types (`CLINotFoundError`, `CLIConnectionError`, `ProcessError`, `CLIJSONDecodeError`, `ResultError`, `MessageParseError`) | **Retry classification** (§4 rule 5): connection/process = retryable, CLI-not-found / JSON-decode = fatal. Replaces today's bare `except Exception` |
| Message + content-block types (`AssistantMessage`, `TextBlock`, `ThinkingBlock`, `ToolUseBlock`, `ToolResultBlock`, `SystemMessage`, `RateLimitEvent`, `StreamEvent`) | Read the stream by type: prove `StructuredOutput` was called, capture the assistant's text when `structured_output` is missing (much better error messages), record rate-limit events |
| `ThinkingConfig` / `max_thinking_tokens` / `ThinkingBlock` | Reasoning-heavy agents only ([2] Role Analyst, [3] Gap Analyst, [6] Evaluator). Thinking text is **never** persisted or shown (D8); only its token count reaches the audit record |
| `fallback_model` | A spec field, per agent. **Never on the Evaluator** (§10) — a silent model swap would make two candidates' scores incomparable |
| `strict_mcp_config=True` | Hardening for `build_options()`: ignore any project/user `.mcp.json` so only our own in-process servers exist |
| Hook types (`HookMatcher`, `PreToolUse`, `PostToolUse`, `Stop`, …) | Optional **second** lane guard beside `can_use_tool`, and one labelled demo. Never the only place a rule lives (§3.2) |
| Sessions (`session_id`, `tag_session`, `rename_session`, `get_session_messages`, `SessionStore`, `InMemorySessionStore`) | Audit replay: one session id per `StepRun`, tagged with the run + step. **Never** `resume` / `continue_conversation` for correctness — agents are stateless (FR-I7) |
| `include_partial_messages` + `StreamEvent` | Step 12 only: live progress in the CLI / FastAPI demo. No effect on correctness |
| `SandboxSettings` | Only if a real tool ever executes something. **macOS/Linux only** — a no-op on this Windows box, so it can never be our only containment |
| `TaskBudget` | Token-budget awareness for tool-using agents. Our agents make one call with no tool loop, so `max_turns` + `max_budget_usd` already bound them |
| `skills`, `plugins`, `betas`, `enable_file_checkpointing` / `rewind_files`, `permission_prompt_tool_name` | Not used — see §3.6 for each reason |

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

### 3.6 Adoption plan — every remaining section, with a verdict

**Now (shared runner `app/agents/base.py`; no agent file changes).** N2 is built; the rest were judged
not worth a standalone step and move to the step that first uses them:

| # | SDK section | Why now |
|---|---|---|
| N1 | Typed SDK errors | ✅ **done in Step 3.** `classify()` in `app/pipeline/runner.py` reads `AgentRunError.__cause__` — `CLIConnectionError` / `ProcessError` retry; `CLINotFoundError` / `CLIJSONDecodeError` do not (the installation is wrong, not the call) |
| N2 | Message / content-block types | ✅ **done 2026-09-21** (and it paid for itself the same day — the stream capture is what makes the salvage in §16.2 possible). `_read_blocks()` reads `TextBlock` / `ThinkingBlock` / `ToolUseBlock` from every `AssistantMessage`; `CallMeta` gains `tools_called`, `assistant_text_chars`, `thinking_blocks`, `thinking_chars` and `structured_output_called`. Errors now quote the model's prose (clipped to `MAX_MODEL_TEXT_CHARS = 300`) and say whether `StructuredOutput` was never called or called with nothing usable. 9 tests |
| N3 | `strict_mcp_config=True` | One-line hardening; matches `setting_sources=[]` in intent |
| N4 | `fallback_model` on `AgentSpec` | Make the Evaluator's "no fallback" rule explicit in data, not a comment |
| N5 | `RateLimitEvent` | Already appears in every subscription run (§3.5); record it instead of dropping it |

**At the step that needs it:**

| Step | SDK section |
|---|---|
| 3 — pipeline runner | `session_id` per `StepRun` + `tag_session` / `rename_session` (audit replay) · retry classification from N1 · optional `SessionStore` backed by the same SQLite file (the SDK ships a conformance suite at `claude_agent_sdk.testing.session_store_conformance`) |
| 4 / 5 / 8 — Role Analyst, Gap Analyst, Evaluator | `ThinkingConfig` + `max_thinking_tokens` (token counts audited, thinking text never stored) · `effort` already in the spec |
| 7 — Question Generator | The O1 tool demo: `tool()` + `ToolAnnotations` (`read_only_hint`, `max_result_size_chars`) + `create_sdk_mcp_server()` + `get_mcp_status()`, all behind `can_use_tool` · optional `PreToolUse` hook as a second, independent lane check |
| 12 — CLI + FastAPI demo | `include_partial_messages` + `StreamEvent` for progress · `ClaudeSDKClient` **only** if the demo needs an interruptible long run; one-shot `query()` stays the default |

**Refused, with the reason (not "unlearned"):**

| SDK section | Why not |
|---|---|
| `AgentDefinition` / `agents=` | Subagents are delegation; D11 forbids it. The app owns sequence |
| `ClaudeSDKClient` for the pipeline | Agents are stateless (FR-I7); a persistent session would let state leak between steps |
| `resume`, `continue_conversation`, `fork_session`, `resume_session_at` | Same reason. A re-run must start clean from saved inputs (FR-I8), not from a conversation |
| `SystemPromptFile` | We read the prompt ourselves so we can hash it **before** sending (§11 audit). Handing the SDK a path loses that |
| `SystemPromptPreset` / `ToolsPreset` `claude_code` | Loads Claude Code's own prompt and tools — 37k tokens of context we measured at $0.378 a call (§3.5) |
| `skills`, `plugins` | Developer-workflow features; Caliber runtime agents get their instructions from their versioned prompt file |
| `betas` (`context-1m`) | Our prompts are small by design; a 1M window would hide a prompt that grew too big |
| `enable_file_checkpointing` / `rewind_files` | No agent writes files |
| `permission_prompt_tool_name`, `PermissionMode` other than default | `can_use_tool` denying by default is stricter and testable offline |
| `SandboxSettings` | macOS/Linux only — a no-op on this machine, so it can never be the guard we rely on |
| `TaskBudget` | For tool loops pacing themselves; our agents make one call bounded by `max_turns` + `max_budget_usd` |
| `Transport` | The bundled CLI transport is what we want |

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
9. **Record before you call.** A `StepRun` row (status `running`) is written *before* the agent call and updated after, in its own transaction — a failed or dying step is recorded, never lost (Caliber lesson: a rolled-back request took the trace with it).
10. **The confirmed profile is a fingerprinted checkpoint.** Downstream steps refuse to run unless it is confirmed; any edit un-confirms it (Caliber `confirmation.py`). Full lessons: `reference/plan/SEQUENCING.md` §6, §8.

### 4.1 The standard agent flow — every agent, no exceptions

**Every agent — [1] through [8], and any example agent — is wired the same four-step way.** New agents copy this pattern; they never call `query()` or build `ClaudeAgentOptions` themselves.

```
<agent>.py:  <AGENT> = AgentSpec(...)              ← 1. we DESCRIBE the agent (data only)
                        │
             run_<agent>() → run_agent(<AGENT>, prompt)   ← 2. the shared runner receives the spec
                        │
base.py:     options = build_options(spec)         ← 3. spec → the SDK's ClaudeAgentOptions
                        │
base.py:     query(prompt=..., options=options)    ← 4. the SDK makes the Claude call
```

Today: `PROFILER` in `app/agents/profiler.py` → `run_profiler()` → `run_agent(PROFILER, prompt)` → `build_options()` (`app/agents/base.py`) → `query()`. The probe agent follows the same path.

**What each layer owns**

| Layer | Owns | Never does |
|---|---|---|
| `app/agents/<agent>.py` — the `AgentSpec` | The agent's **identity**: `name`, `prompt` (`load_prompt(name, version)`), `output_model`, **`model`**, `effort`, `max_turns`, `max_budget_usd`, tool names / servers, `cw` tag | Import or call `query()`; build `ClaudeAgentOptions`; hard-code SDK settings |
| `run_<agent>()` in the same file | Building the fenced user prompt, calling `run_agent(SPEC, prompt)`, then the agent's own code checks (grounding, validators) | Choose a model at call time; bypass `run_agent()` |
| `app/agents/base.py` — `run_agent()` / `build_options()` | Everything **shared by all agents**: the live-call gate, lean options (`tools=[]`, `setting_sources=[]`, `allowed_tools=[]`), the `can_use_tool` gate, the output schema, the audit record (`CallMeta`), error types | Name a model or a prompt; contain agent-specific logic |
| The SDK (`claude_agent_sdk.query`) | The actual Claude call | — (only `run_agent()` calls it) |

**Rules that follow (checked in review):**
1. **One place per fact.** A model id lives only in `app/config.py` (`OPUS` / `SONNET` / `HAIKU`) and is *named* only in the agent's spec (`model=HAIKU`). `base.py` never names a model.
2. **Per-agent differences are spec values, not code.** A stronger model, an `effort`, a tool or a different schema is a different spec field — `build_options()` stays untouched. If a new agent seems to need a change to `base.py`, treat it as a shared rule for *all* agents and raise it first.
3. **Only `run_agent()` calls `query()`.** No agent file imports it. This keeps the live-call gate, the audit record and the tool gate un-bypassable.
4. **Specs are immutable data.** Build them once at import (`PROFILER = AgentSpec(...)`); never mutate one at run time.
5. **A new agent = a new file + a new prompt file + a schema + a spec + `run_<agent>()` + tests.** Nothing else in `base.py` changes.
6. **Tests for every new agent** assert its spec (model, effort, `cw`, prompt label), that `build_options(SPEC)` is lean (`tools == []`, `setting_sources == []`), and that `run_<agent>()` refuses without the live-call gate.

Template for a new agent:

```python
# app/agents/<agent>.py
<AGENT> = AgentSpec(
    name="<agent>",
    prompt=load_prompt("<agent>", 1),      # prompts/<agent>.v1.md
    output_model=<OutputSchema>,           # derives from AgentSchema; check_schema_rules() == []
    model=<HAIKU | SONNET | OPUS>,         # RULEBOOK §10
    effort=<None | "low" | "medium" | "high">,   # never on Haiku, never "max"
    max_budget_usd=<ceiling>,
    cw="<cw-n>",                           # Caliber workload tag
)

async def run_<agent>(<inputs>, *, query_fn=None):
    prompt = build_user_prompt(<inputs>)              # fence untrusted content
    result = await run_agent(<AGENT>, prompt, query_fn=query_fn)
    return <code checks on result.output>
```

### 4.2 The detailed call sequence — the same for every agent

Every agent's request travels the **same path, in the same order**. Only the boxes marked **(agent)** differ per agent; the boxes marked **(shared)** are one implementation in `app/agents/base.py`. Example values are the Profiler's.

```
input (resume text / answers / a topic …)
        │
        ▼
┌─ 1. run_<agent>(inputs)                          (agent) app/agents/<agent>.py ─┐
│  BEFORE the call: validate the input, wrap untrusted text with fence()          │
│  (→ prompt string), then call run_agent(<AGENT>, prompt).                       │
└─────────────────────────────────────────────────────────────────────────────────┘
        │   <AGENT> = AgentSpec: name · prompt file · output_model · model · effort · cw
        ▼
┌─ 2. run_agent(spec, prompt)                      (shared) base.py ───────────────┐
│  BEFORE the call: refuse unless CALIBER_ALLOW_LLM=1; start the audit record      │
│  (prompt version + sha256, input sha256, model, cw); call build_options(spec)    │
│  then query(...).                                                                │
└─────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ 3. build_options(spec)                          (shared) base.py:237 ───────────┐
│  Translates the AgentSpec into the SDK's ClaudeAgentOptions (below).             │
└─────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ ClaudeAgentOptions                              (the SDK's settings object) ────┐
│  system_prompt  = the agent's prompt file text     model  = spec.model           │
│  effort         = spec.effort (never on Haiku)     output_format = output_model's│
│  tools=[]  allowed_tools=[]  setting_sources=[]      JSON schema                 │
│  can_use_tool   = gate (own tools + StructuredOutput only)                       │
│  max_turns / max_budget_usd / cwd from the spec and app/config.py                │
└─────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ 4. query(prompt, options)                       (SDK) base.py:290 ──────────────┐
│  The only call that reaches Claude. Streams messages; the last is ResultMessage  │
│  (subtype, structured_output, usage, cost).                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
        │   ResultMessage.structured_output = the agent's JSON
        ▼
┌─ 2. run_agent (after the call)                   (shared) ────────────────────────┐
│  AFTER: check success + the JSON validates against output_model; fill the audit  │
│  record (tokens, cost, latency, session id, models served); return               │
│  AgentResult(output, meta) — or raise AgentRunError / AgentOutputError.          │
└─────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ 1. run_<agent> (after the call)                 (agent) ────────────────────────┐
│  AFTER: the agent's own code checks — grounding, arithmetic, validators          │
│  (RULEBOOK §13) — then return the agent's result. Code decides; the model only   │
│  proposes.                                                                       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Who owns what**

| Step | Owner | Same for every agent? |
|---|---|---|
| `AgentSpec` (identity, model, prompt, schema) | the agent's file | **No** — this is the only per-agent configuration |
| `run_<agent>` before the call (validate input, `fence()`) | the agent's file | No — knows the agent's inputs |
| `run_agent` before/after, `build_options`, `query` | `base.py` | **Yes — one shared implementation** |
| `run_<agent>` after the call (code checks) | the agent's file | No — knows the agent's rules |

**Per-agent examples of the two agent-specific ends** (the shared middle never changes):

| Agent | Before the call (`run_<agent>`) | After the call (code checks) |
|---|---|---|
| [1] Profiler | fence resume / answers; size limits | ground every quote, parse dates, cap over-claims, build missing questions |
| [2] Role Analyst | compute level, fit label, direction, top gaps; pass them in | echo checks (level, direction), numbers-verbatim |
| [3] Gap Analyst | compute the whole gap map; pass rows | numbers-verbatim; reason keyed to a real gap |
| [4] Plan Builder | topic set fixed by code | output topics == gap map topics |
| [5] Question Generator | topic, projects, prior questions | not a repeat of an earlier question |
| [6] Evaluator | question, answer (fenced), rubric, reference answer | dimension totals recomputed in code; quotes found in the answer; verdict from the ≥70 rule |
| [7] Guidance | the saved Grade only | D8 no-teaching check |
| [8] Adaptation | app-built menu of allowed moves | chosen move ∈ menu |

**New-agent checklist (a step is not done until every box is true)**
- [ ] The agent has an `AgentSpec` and its file has **no** `query()` / `ClaudeAgentOptions` import — the SDK is reached only through `run_agent()`.
- [ ] The model, effort and `cw` are set in the spec (values from `app/config.py`); `base.py` was not edited for this agent.
- [ ] The prompt is a versioned file loaded with `load_prompt()`; the output schema passes `check_schema_rules()`.
- [ ] `run_<agent>` validates input and fences untrusted text **before** the call, and runs its code checks **after** it.
- [ ] Offline tests cover: the spec, `build_options(SPEC)` being lean, the live-call gate refusing, a fake-`query` end-to-end run, and each code check.
- [ ] No step in this sequence is skipped, reordered or duplicated; the pipeline runner (Step 3) wraps `run_<agent>` and never `query()`.

### 4.3 Retry rules (`classify()` — what is worth a second call)

The runner retries **up to 2 times** (O4: the PRD's number, not Caliber's 1), then fails the step and stops the
run. Every attempt becomes a `step_runs` row, failures included — "succeeded" and "succeeded on the third try"
are different facts about the prompt.

| Failure | Retry? | Why |
|---|---|---|
| `AgentOutputError` (schema / validation) | **yes**, with the problems fed back | The one retry that reliably changes something: the model is told what was wrong (`build_user_prompt(..., feedback=...)`) |
| `CLIConnectionError`, `ProcessError` | **yes** | The call never reached a conclusion |
| Unknown error subtype | **yes** | Fail safe, bounded by `MAX_ATTEMPTS` |
| `CLINotFoundError`, `CLIJSONDecodeError` | **no** | The installation or protocol is wrong; three attempts just prove it three times |
| `error_max_budget_usd`, `error_max_turns` | **no** | A ceiling *we* set. The retry pays full price to stop in the same place (§16.2) |
| `error_max_structured_output_retries` | **no** | The SDK already retried the shape internally; ours would be the same prompt to the same model |
| `LLMCallsDisabled` | **no** | A decision, not a fault |
| Any other Python exception | **no** | Our own bug — identical input fails identically |

**A salvaged result is never re-run.** It validated and it was paid for; it is recorded `status="salvaged"` and
the pipeline moves on. Retrying would buy a second copy of an answer we already hold.

**Checkpoints are returns, not prompts** (FR-I11). `run_pipeline()` records the pause and returns; the caller
collects the answer, calls `store.decide()`, and calls `run_pipeline()` again with the same `run_id`. A
checkpoint listed in a step's `repeat_after` sends the run back through that same step — that is the Profiler's
completeness loop, and it is a *loop*, not a retry: same resume, new answers.

**Resuming costs nothing.** Completed steps are read back from `step_runs` and revived into their own type
(`Step.revive`), so step [2] sees a `CandidateProfile` whether the run is fresh or three days old (FR-I8).

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
PDF / DOCX  ─► [0] EXTRACTION (plain Python, no model: pdfplumber / python-docx)
               reject before any token is spent: 415 wrong type · 413 too big
               · 400 corrupt · 422 no text layer (a scan)
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
| 1 | **Profiler** (CW-1, CW-3 in code, CW-4 style) | Completeness gate (required vs optional, thin answers re-asked) + `missing_fields`; evidence ladder + depth score; recency; ownership + seniority signals; vague terms; `your_role` check; verifies every copied field/quote; keeps the **weaker** of code rating vs agent verdict | Structures the candidate's material into roles / projects (all PRD §7.1 fields) / skills / education, copying every name, date and quote **verbatim**; per-skill verdict + quote | Resume text **and/or** answers (Path B) | ProfileDraft v2 → `CandidateProfile` |
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
2. **Evidence before label:** `quote` comes before the verdict/score/label it justifies (the subject — e.g. the skill name — may come first).
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

> Caliber's **as-built** rules (completeness weights, text-quality tiers, evidence ladder, depth score, gap map, plan, fit labels, state machine) are in `reference/plan/ARITHMETIC_RULES.md`. The POC keeps a simplified subset; where it differs, it says so here or in §16.

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

From `reference/llm/dev-cycle.md` §10.4 — full per-agent capabilities, workloads (CW), checkers, evals and costs in **`reference/agents/AGENT_CAPABILITIES_AND_MODELS.md`**. Models bind to the **workload**, not the agent (Caliber rule 2); each POC `AgentSpec` names its own model. Model ids: `claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5` (full id `claude-haiku-4-5-20251001`).

| Agent | Model | Effort | Hard constraints |
|---|---|---|---|
| [1] Profiler | Haiku 4.5 | **don't send** | Haiku rejects `effort`. Caliber puts the CW-4 claim verdict on **Opus 5 · high** (see O8) |
| [2] Role Analyst — narrative | Opus 5 | medium/high, **never max** | **Never Sonnet 5** (measured 9.1% sycophancy) |
| [2] Role Analyst — JD labels | Haiku 4.5 | don't send | — |
| [3] Gap Analyst | Haiku 4.5 | don't send | numbers-verbatim check |
| [4] Plan Builder | Sonnet 5 | medium | — |
| [5] Question Generator | Opus 5 (CW-9 questions + reference answers) · Sonnet 5 (CW-12 fresh variants) | high · medium | reference answers checked by a *different* model (blind solve) |
| [6] Evaluator | Opus 5 | **high, fixed, never max** | no fallback model; never cached |
| [7] Guidance | Haiku 4.5 (senior+ → Opus 5) | don't send on Haiku | never Sonnet on tone |
| [8] Adaptation | Haiku 4.5 | don't send | — |

- Opus 5 / Sonnet 5 reject `temperature`, `top_p`, `top_k`, `budget_tokens`, assistant prefill. **Effort is the only depth control**; `max` is discouraged for structured output.
- Haiku 4.5 has a retirement floor of **2026-10-15** (Caliber calendar) — keep the model a config value.

---

## 11. Audit record (`StepRun`, FR-I10 + Caliber trace fields)

`run_id` · step # · agent name · **prompt version + sha256 hash** · model requested / served · effort · input reference (hash of the input JSON) · output (or reference) · validation result + reasons · retry count · latency · tokens · cost · SDK session id · error class · timestamp · **what the stream showed** (`tools_called`, `structured_output_called`, `assistant_text_chars`, `thinking_blocks`, `thinking_chars`) · **`salvaged_from`** (the error subtype a kept payload was rescued from, else `None`).
**Counts only.** The model's prose is quoted in the exception a developer reads, never in the record; thinking text is never kept at all (D8).
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

**Profiler specifics:** grounding sources = resume **+ the candidate's answers**; project `name` is a label (not grounded); a fabricated field becomes `null` and is then asked for by the completeness check; stated years win over dated years; a gap wider than `max(2.0, 0.25 × stated)` years (Caliber's rule) is flagged, never corrected. **v1.1:** `your_role` stands only on a verified `role_quote`, and a lead-type role (led / owned / built_solo) on team language is lowered to `contributed` (`capped_roles`). Vague stack items are split into `vague_stack` and asked about (optional); a vague skill claim is dropped. Project text fields must reach **substantive** (`app/textquality.py`) or they are re-asked with the reason; impact without a number and a hardest problem without a decision get optional refinements. **Required** (block confirmation): role identity + dates, years, ≥1 project, per project: role link, `your_role`, summary, responsibilities, impact, hardest problem, scale, ≥1 concrete stack item. **Optional nudges:** employment type / domain / team context, processes, vague-term clarifications, refinements, education (only below 5 years). **v1.2 (review fixes):** ids are always unique (smallest free number); skill names and stack items match as **whole terms** ("SQL" is not in "PostgreSQL"), needles ≤ 3 chars too, and no quote may span two sources; team language = we / our / us / my team / the team / together with — but "I led the team" is the candidate leading (not team language); lead verbs in the **passive** ("led by my manager") never support `led`; `leads_people` counts only when the candidate (or a subject-less resume line) did the leading; a lead-type `your_role` with no named decision marks that project's skills **probe first** (Caliber's claimed-but-weak rule); stated years accept "6" and "six years"; a role with no project is required; future end dates count only to today; answers are capped at `MAX_ANSWERS_CHARS` in total; long skill quotes are clipped around the skill; near-duplicate demotion applies only to text the candidate typed (a resume bullet may serve as summary and impact); all thresholds and word lists live in `app/policy.py` (`POLICY_VERSION = poc-2`).

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
| 2 | [1] Profiler + completeness loop | `system_prompt`, structured output, grounding | ✅ **v1.2** built + independently reviewed · live run not yet approved |
| 2b | [0] `app/extraction.py` — PDF/DOCX → text | The deterministic half: code decides *before* the model is called | ✅ built · **41** offline tests · verified on 9 files (§16.1) · hardened by the live run (§16.2) |
| 3 | Pipeline runner + SQLite `PipelineRun`/`StepRun` | Fixed order, retries, audit, resume | ✅ built · 42 offline tests · `step3_demo.py` |
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
| O5 | Storage | **Resolved 2026-09-21: PostgreSQL is the system of record** (`PostgresStore`), SQLite stays for the offline suite and demos (`SqliteStore`) — the arrangement Caliber itself uses. One interface, one conformance suite, chosen by `POC_DATABASE_URL`. See §16.3 |
| O6 | Readiness formula, borderline band, topic verdict rule | POC choices in §9 / §14 until Caliber decides |
| O7 | ~~`tools=[]` really removes built-ins?~~ | **Resolved 2026-09-17:** yes — see §3.5 |
| O9 | ~~Years-mismatch tolerance~~ | **Resolved 2026-09-18:** POC now uses Caliber's `max(2.0, 0.25 × stated)` (`app/config.py`, `years_mismatch()`) |
| O10 | Topic verdict: Caliber has **two** constants (≈70 per answer, 80% per topic) and leaves aggregation open (DEC-3/3c) | POC grades the scenario probe only (Appendix E): topic passes when that answer ≥ 70. The 80% topic line is not used |
| O11 | Required vs optional capture items: Caliber gates *every* item (incl. employment type, domain, team context, processes) | POC makes those optional nudges to keep the capture loop short; the PRD's always-asked items (impact, hardest problem) and scale stay required |
| O12 | Seniority signals: Caliber counts near-duplicate answers once (clustering) | POC relies on text-quality near-duplicate demotion instead; add clustering only if evals show inflated signals |
| O13 | PRD §7.1 optional **demo/artifact link** per project is not captured | Deviation for the POC (D1: a link is never fetched anyway). Add a grounded `link_raw` in a future prompt version if the demo needs it |
| O14 | PRD §10.1 Profiler input "previous draft profile (on re-run)" | POC re-runs from resume + answers (answers are fenced with their question text); ids can shift between runs. Step 3 runner should carry the previous profile and map answers by key |
| O15 | "Impact and hardest problem always asked" | POC asks them only when missing or thin (PRD: "resume path pre-fills and asks only for gaps"); a substantive-but-unspecific answer gets an optional refinement |
| O16 | Education weight / CW-3 scope | Education is recorded and only *asked for* below 5 years (no weight is stored). CW-3 in the POC is vague-term detection only — no canonical skill taxonomy, so "Postgres" and "PostgreSQL" stay separate skills |
| O17 | `leads_people` edge cases (documented limits) | "Led by example" reads as passive (False); "The CTO and I led a team" reads as co-led (True); "I was hired and later led a team" reads as True |
| O18 | **Column-split guard.** Caliber's `_find_gutter()` accepts any clear vertical channel with no minimum width | POC adds `_MIN_CLEARANCE = 12.0` pt. Measured on this machine: a true two-column gap is **41.4 pt**, while accidental word-space alignment on single-column pages measured **3.5–3.9 pt** and made the extractor emit straddling words **twice, in halves**. Locked by `test_without_the_clearance_guard_the_same_page_is_corrupted` |
| O19 | **Unmappable glyphs.** pdfminer emits `(cid:NNN)` for any glyph it cannot map (Symbol/Wingdings bullets) | POC maps `(cid:\d+)` → `•` and strips C0 control characters (NUL included) in `_clean()`. Caliber passes both through to the model |
| O20 | **DOCX table position.** Caliber reads all paragraphs, then all tables, so an Experience table lands below Education | POC walks the document body in order, keeping each table under its own heading. Falls back to Caliber's order if python-docx internals move |
| O21 | **Inter-word spacing.** Most PDFs store no space characters; pdfplumber infers a break when the glyph gap exceeds `x_tolerance` (default 3 pt), so a tight font silently fuses words | POC sets `_TOLERANCE = {"x_tolerance_ratio": 0.15}` on **every** pdfplumber call (word boxes, plain text, both crops, the per-page fallback) — the column path must agree with the plain path on where words begin. A **ratio**, not a flat value: it scales with each glyph's font size, where a flat 1.5 pt shatters a tracked heading into `P r i y a`. Measured on a real resume: 55 → 16 `[a-z][A-Z]` joins, 0/4 → **4/4** probe phrases; all 8 earlier fixtures byte-identical. Locked by `test_with_pdfplumbers_default_tolerance_the_same_page_loses_its_spaces` |
| O8 | Profiler claim verdicts: one Haiku call vs a separate Opus verdict pass | **Built 2026-09-21 (§16.6), never run.** CW-1 keeps its inline verdict; CW-4 is an optional second opinion that can only demote. Per §16.5 the PRD never mandates the separate pass, so running it is a *quality* decision the gold set should settle — not a spec requirement |

---

### 16.1 Extraction — measured on this machine (2026-09-21)

Synthetic files, `pdfplumber 0.11.10` + `python-docx 1.2.0`, no model call.

| File | Time | Result |
|---|---|---|
| 1-column PDF, 2 pages | 38–42 ms | complete, both pages |
| Two-column PDF (both draw orders) | ~40 ms | columns de-interleaved, identical output |
| Table + bullets PDF | 16 ms | every row a line |
| DOCX with a table | ~90 ms | rows joined `A \| B \| C`, under their heading |
| Scanned / image-only PDF | 1.7 ms | `layout="empty"`, `is_usable=False` → 422 |
| Truncated / not-a-PDF | <2 ms | `UnreadableDocument` → 400 |

**Why not pypdf:** on the two-column resume both pypdf and plain pdfplumber interleaved the
skills sidebar into the job history ("Python, Scala, SQL" between a job title and its employer).
pypdf also drops the bullet glyph silently. Caliber's stated reason for rejecting it is correct.

**Known gap:** no OCR — an image-only PDF is a hard stop by design, surfaced as the 422 above.
`MIN_USEFUL_CHARS = 100` does **not** catch a *partial* text layer (a scan with a typed header
passes with ~120 junk chars). Caliber has the same hole.

### 16.2 First live run — 2026-09-21, one Haiku call, $0.1107

Real resume (2-page PDF, `runs/private/`, git-ignored). Extraction 162 ms. The model **succeeded**: one turn,
`StructuredOutput` called with a complete schema-valid draft (3 roles, 3 projects, 20 skills, 1 education),
18,191 output tokens. The run still failed — `error_max_budget_usd`, $0.1107 against our $0.10 ceiling — and
`run_agent()` raised, discarding a result we had paid for. The draft was recovered by hand from the local
session transcript and the code half re-run offline, which is what produced the findings below.

**What it exposed, and what changed:**

| # | Finding | Status |
|---|---|---|
| 1 | **Extraction silently fused words** (`BachelorofEngineering`) — the text passed every check, then grounding rejected 100% of claims because a verbatim substring cannot match a mangled source | ✅ fixed — O21 |
| 2 | **$0.10 is below what this schema costs** (18k output tokens ≈ $0.09 alone) | ✅ ceiling raised to **$0.25** (2026-09-21). It is a runaway guard, not a cost control — on a single-turn call it stops nothing, it only decides whether the run reports `success` or `error`. **Why the draft costs 18k output tokens is still open**, and belongs to the evals (step 11), not to this number |
| 3 | **A paid result was thrown away.** `structured_output` is absent on *every* error result (verified in the bundled CLI's zod schemas — only the `success` variant carries it) | ✅ fixed — `SALVAGEABLE_SUBTYPES` + `_salvage()`; the payload is read back from the `StructuredOutput` `ToolUseBlock` and kept when it validates, marked `meta.salvaged_from` |

**Salvage rule:** only ceilings *we* set (`error_max_budget_usd`, `error_max_turns`) are salvageable, and only a
payload that passes the agent's schema. `error_max_structured_output_retries` (the CLI's own gate already
rejected it), `error_during_execution` (a partial turn is not a result), a 429/500 behind `subtype="success"`,
and transport failures all still raise. A salvaged run is never silently indistinguishable from a clean one —
`AgentResult.salvaged` / `ProfilerRun.salvaged` read straight off the audit record.

**The lesson worth keeping:** every synthetic fixture I generated wrote real space glyphs, which pdfplumber
splits on before any tolerance test — so 528 offline tests *could not* have caught finding 1. One live run on
one real document did. Fixture corpora prove code correct against the documents you imagined.

### 16.3 PostgreSQL — the move from SQLite (2026-09-21)

**Postgres is the system of record; SQLite runs the offline suite.** Both implement one `Store` interface with
every method body written once, so the backends cannot drift in logic — only in the seven places the dialects
genuinely differ. `tests/test_pipeline_store.py` is a **conformance suite**: the same tests run against both,
the Postgres parameter marked `@pytest.mark.postgres` and skipped unless `POC_TEST_DATABASE_URL` is set.

**Why not Postgres-only**, which is what was first asked for: 42 of our tests touch the store and 548 do not.
A Postgres-only store means `pytest` needs a running service — and **Caliber itself ships Postgres and runs its
whole ~790-test suite on in-memory SQLite and fakes; zero of its tests connect to a database.** Its CI comment
says it outright: *"the whole point of this gate is that it needs NOTHING"*. Dumping SQLite would have made the
POC's test story weaker than the product's. `pytest` → 613 passed, no service. `pytest -m postgres` → the same
store tests against the real engine.

**No ORM, no Alembic.** Plain SQL with psycopg 3. Alembic's value is coordinating schema change across people
and environments; this is one developer, one machine, four tables and disposable demo data. The cost is real
and stated: we give up SQLAlchemy's dialect layer, which is exactly what lets Caliber run on two engines — so
we hand-maintain two `CREATE TABLE` blocks and let the conformance suite catch the difference.

**Decisions that differ from Caliber, with reasons:**

| Choice | Caliber | Ours | Why |
|---|---|---|---|
| Cost column | `double precision` | **`numeric(12,6)`** | §16.2 is a story about $0.1107 against a $0.10 ceiling. A number that decides an outcome should be exact — the guarantee is that the *sum across attempts* is exact |
| Vocabularies (`status`, `served_from`) | `varchar(n)` | **`text`, validated in the app** | No native enum, no CHECK, no width. `salvaged` joined the attempt statuses *this week*, and a `StringDataRightTruncation` would kill the audit row for a failed step — the row §4 rule 6 most wants kept |
| Trace prompt/response | `agent_call.prompt` is `Text NOT NULL`, full rendered prompt + response, resume included | **never stored** | Caliber's own `observability.md` says traces keep hashes and never candidate PII; its code contradicts its spec and the retention job is unbuilt. We keep §11 |
| pgvector | extension enabled | **not used** | Caliber enables it and has *zero* vector columns; ADR-0005 forbids semantically caching grades, and our grounding is verbatim substring matching |

**Copied from Caliber, and worth it:** `served_from` (`provider|fake|cache`) so a fixture reply can never be
counted as billed — we have 613 offline tests driven by fakes, so we have exactly that hazard; `timestamptz`
everywhere plus `ALTER DATABASE … SET timezone='UTC'` (their ops file records that this same Windows installer
defaulted the server to the machine locale); and NUL stripping on every input, because `\x00` raises a psycopg
`DataError` that would take the audit row with it.

**Verified against a real server (PostgreSQL 18.3, 2026-09-21).** `pytest -m postgres` → **31 passed** on the
first run, so the unverified list the store agent reported (DDL, `GENERATED ALWAYS AS IDENTITY` + `RETURNING`,
jsonb round-trip, the float → `numeric(12,6)` cast, timestamptz normalisation, `ON CONFLICT … DO UPDATE`,
`TRUNCATE … RESTART IDENTITY CASCADE`) is now evidence rather than a claim. Column types were read back from
`information_schema`: `timestamptz` ×6, `jsonb` ×4, `bigint` identity keys, `text` for `run_id`/`status`,
`numeric` for cost, 3 enforced foreign keys. A full pipeline run on Postgres — a schema failure, the repair
retry, a checkpoint, then a resume in a **fresh connection with an empty state dict** — reloaded `resume_text`
from `run_inputs` and finished. That last part is FR-I8, which the SQLite-only tests could only simulate.

**Setup on this machine:** own role `caliber_poc` and databases `caliber_poc` / `caliber_poc_test` on the
existing `postgresql-x64-18` service — **not** Caliber's `caliber` database, so a demo cannot touch product data.
Both databases are set to `timezone='UTC'`, `datestyle='ISO, YMD'`. Credentials live in `.env` (git-ignored),
loaded by `app/envfile.py`, which reads **only `POC_*` keys** — `CALIBER_ALLOW_LLM` can never be opened from a
file — and never lets a file override a variable already set.

**Known limit:** `served_from` is decided from `state["query_fn"]`, so a test that fakes the whole step's
`execute` (as the runner tests do) is recorded as `provider`. It is right for the real Profiler step, where
`query_fn` is the seam; any new step that fakes at a different seam must set it explicitly.

**Two bugs in the Step 3 runner that this work exposed, both now fixed:**
1. The attempt row was written *after* the call, breaking §4 rule 9 — the rule Caliber wrote after a rolled-back
   request took its trace row. Now `start_attempt()` opens a `running` row **before** the call and
   `finish_attempt()` closes it, in two transactions. A step killed mid-call leaves an open row saying so.
2. `run_inputs` did not exist, so FR-I8 was not actually satisfied: step outputs restore later steps, but step
   [1]'s own input is nobody's output. A resume in a fresh process could not have re-run it.

Also fixed while pinning rule 9: `run_step` caught `BaseException`, so a Ctrl-C mid-call was classified as a
step failure instead of stopping the program.

### 16.4 Live Haiku test of CW-1 / CW-2 / CW-3 — 2026-09-21, $0.2057

Real resume, clean extraction, **Haiku 4.5 only**. CW-4 (Opus 5 · high) deliberately not run.

**CW-1 resume → schema — $0.1065, 17,490 output tokens.** With the word-spacing fix in place the code half
dropped **nothing**: `dropped_fields=0, dropped_claims=0, capped_claims=0, capped_roles=0`, against 35 dropped
fields on the same resume before the fix. Required questions **26 → 2**. Dated experience 5.4 years agreed with
the stated 5. This is the §16.2/O21 fix proven end to end on a real call, not a replay.

**CW-3 skill normalise — no call made, and that is the correct outcome.** Retrieval offered candidates for
**0 of 17** terms: the resume is a Java/Spring backend CV and the only bar we have is Senior AI Engineer. The
code half behaved exactly as designed (offer nothing rather than a near miss), but **the model half is still
untested live**. Testing it needs a bar that covers the candidate's domain — which is also the PRD's
"no bar exists for your role" case that step [2] has to handle.

**CW-2 elicitation — $0.0992, and the honest result is mixed.**
The mechanical gates passed: **invented demands = 0**, template fallbacks = 0, every key echoed exactly, and the
tone is far better than the templates ("Eight quick questions — three on roles, five on projects.").
**But the model changed what was being asked in 6 of 8 questions**, and `_verify()` did not catch it because it
checks keys, not meaning:

| Gap | The code needs | What the model asked |
|---|---|---|
| `role:rN:context` ×3 | employment type · team size · did you lead anyone | "What was your focus area?" — **answers none of it** |
| `project:pN:processes` ×2 | how they worked: design review, code review, on-call, agile | "What processes did the system **change or automate**?" — asks about the product |
| `project:p3:hardest_problem` | the **decision** they made | "how did you solve it" — invites a narrative with no decision, which the quality gate then rejects |

So the gap list is safe (nothing invented, nothing dropped) but the answers would come back unfillable.
**Cause:** `elicitation.v1` told the model *which* gap to word, never what a valid answer must contain.

**Fixed the same day (CW-2 v2):**
* `app/policy.py` gains two halves that must agree — `FIELD_PURPOSE` (what a usable answer contains, sent to the
  model as `answer_must_give`) and `FIELD_ASK_TERMS` (whole words a question for that field must mention).
* `prompts/elicitation.v2.md` leads with the rule and shows all three measured drifts as worked wrong answers.
* `asks_for()` in `app/agents/elicitor.py` is the gate: a question that asks for something else falls back to the
  template, which is correct by construction, and records `refused="does not ask for <field>"`. The candidate is
  asked properly rather than asked something else.
* Deliberately permissive — one whole word is enough, and a field with no listed terms passes. A false reject
  only costs template wording. `"process"` is **excluded** from the processes terms: both the right question
  ("how did you work") and the wrong one ("what processes did the system automate") contain it.
* Replaying the live run's own eight answers through the new gate: **2 kept, 6 sent back to template.**
* 41 CW-2 tests, every drift case taken verbatim from this run. Suite **691 passing**.

**Still open:** whether v2's prompt makes the *model* stop drifting, rather than the gate catching it afterwards.
That needs one more live call to know.

**Cost note:** both calls ran ~$0.10, against Caliber's estimates of ~$0.01 (CW-1) and $0.02–0.05 (CW-2). The
driver is output tokens (17,490 and 12,667) — our analysis-first schemas ask for reasoning on every row. That is
the §16.2 question again and still belongs to the evals (step 11), not to a budget knob.

### 16.5 Who owns the claim–evidence verdict — both PRDs read, 2026-09-21

Checked because the workload looked like it might belong to [2] Role Analyst. Two agents read **v1.6** and
**v1.7** independently, neither seeing the other's document. They agree.

**"CW-4" is not PRD vocabulary.** The string appears in neither PRD. Nor does "Opus 5", nor any effort level:
v1.7 §9 says only "best model per task", and §10.1 lists model routing as something *the app* owns. The
CW-numbering, the model assignments and the two-pass design are all **engineering elaboration on top of the
PRD**, from `AGENT_CAPABILITIES_AND_MODELS.md`.

**What the PRDs do say.** The evidence ladder is defined at capture time, in passive voice, with **no agent
named** — v1.7 §7.1 and v1.6 §7.1 carry the same sentence: *"each claimed skill gets an evidence strength
(none / mentioned / demonstrated / led)"*. Four levels, not three. Ownership is then inferred through the data
model, not stated:

    §7.1 defines the ladder  →  v1.6 FR-A5 makes it the ingestion output
                             →  §10 makes it a SkillProfile field
                             →  §10.1 makes [1] Profiler the SkillProfile's owner

**[2] Role Analyst is ruled out in both.** v1.6 §10.1 defines it in one clause with no profile input at all —
*"understand the target role + analyze the JD; assemble/adapt the role-bar"* — and v1.7 row [2] outputs
*"RoleBar (JD overlay applied, versioned) + role recommendations with fit labels"*, carrying no evidence field.
v1.7 Appendix F narrows it further: *"[2] only applies the JD overlay and role recommendations."*

**Why the question was a good one.** v1.6 **§7.2 "Role selection + honest leveling"** puts a
claimed-vs-demonstrated judgement inside the *role* section, and its candidate-facing copy is CW-4's job
description written in the wrong place: *"the specific projects you delivered … your exact contributions … to
**verify genuine ownership**"*. So the document really does describe evidence-verifying work under a role
heading.

**Open and unowned in both PRDs:** "honest leveling" (*"you present as Senior but demonstrate Mid"*, v1.6 §7.2
and §7.5, v1.7 §7.5) is assigned to **no agent** in §10.1. v1.7 additionally assigns a *"leveling read (claimed
vs demonstrated level)"* to **[3] Gap Analyst**. So claimed-vs-demonstrated appears at up to three places with
no reconciliation. This must be settled before step 5 ([3] Gap Analyst), not now.

**Consequence for the POC (updates O8):** our single Haiku call with a code-side cap and weaker-wins is **closer
to the PRD than Caliber's own implementation is** — the PRD asks for an evidence strength on the SkillProfile
and never asks for a separately-routed Opus adjudication pass. An Opus verdict pass remains a *quality* option
to be justified by evals, not a spec requirement.

### 16.6 CW-4 claim–evidence verdict — built 2026-09-21, never run

The last unbuilt Profiler workload, and the only agent in the POC that is not Haiku: **Opus 5 · high**,
`max_budget_usd=0.50`, batch cap 20. Built by two agents in parallel — the agent itself, and the eval gate the
reference names for it — with **no live call made**.

**What it is for.** Our code already proves a quote is *real* (verbatim substring). It cannot prove the quote is
*about* the skill. The reference's own defect class: *"Terraform rated 'demonstrated' on 'I ran the schema
migrations'"*. CW-4 is the only thing in the design that catches that.

**Demote-only, and why it is not `final_evidence()`.** `demote_only(proposed, model_verdict)` returns the lower
of the two by `evidence_rank()`. It deliberately does **not** reuse `final_evidence()`, which floors at
`mentioned` — CW-4's whole finding is that a quote may support the skill *not at all*, and the floor would erase
the one thing the call buys. Every promotion attempt is kept in the audit record
(`AdjudicatedClaim.model_verdict` + `promotion_refused`), never silently dropped.

**A trap worth recording.** Comparing verdicts as strings looks correct and is not: alphabetically
`"demonstrated" < "none"`, so a string `min()` turns a refusal into a promotion — precisely the case CW-4
exists to catch. Rank, never strings.

**Two deliberate departures from the reference:**
* *"every 'demonstrated' re-adjudicated"* would leave a false **`led`** unexamined, and `led` is the more
  expensive error. Any claim may be sent; demote-only does the constraining.
* Caliber's **Sonnet citations second pass** is not built. Its job — prove the quote is real — is already done
  verbatim in `candidate_profile.py` before CW-4 sees anything. Consistent with §16.5.

**The eval gate (`evals/cw4.py`), which is the point of building this now.** The reference calls for an
*asymmetric cost-matrix gold set*, because *"a false 'demonstrated' is unrecoverable"* — past that line the
skill is never assessed again, while an under-credit is merely an extra question. The weights are a **POC
choice, not a Caliber number**, and what matters is the ordering they produce:

| Error | Cost |
|---|---|
| `led` → `none` (worst under-credit) | **3.0** |
| `none` → `mentioned` (over-credit, still below the probe line) | 4.0 |
| `mentioned` → `demonstrated` (**crosses the line**, one rung) | **10.0** |
| `none` → `demonstrated` (the reference's own D10 case) | 14.0 |
| `none` → `led` | 18.0 |

The worst under-credit is cheaper than the cheapest line-crossing over-credit, and the D10 case costs **7×** its
reverse. The line-crossing surcharge is flat, because *unrecoverable* is a threshold fact, not a distance fact.

**Gold set:** 56 rows, `none` 30% (it is a correct answer), **19 in the D10 slice**, plus team / passive /
stack-list / borderline slices scored separately. Rows are deliberately paired — the same sentence against three
skills with three different answers — so the set measures discrimination rather than vocabulary. It is
**synthetic and single-rater**; the reference requires 2–3 human raters at κ ≥ 0.6, and this is a stand-in.

**Settle before wiring:** the nine team-language rows are labelled `mentioned`, matching the existing code cap
(§13). That is correct on the merits — *"we migrated the services"* does not show the candidate doing it — but
if CW-4's verdict space is ever meant to sit *above* the cap (agent proposes, cap demotes), those rows need
re-labelling. Also unbuilt by design: the `SkillEvidence` → `Claim` adapter. `Claim(claim_id, skill, quote,
proposed, project)` is the seam.

**Cost warning.** At `$0.50` a CW-4 call could cost more than every call made in this project so far combined.
The ceiling is a runaway guard, not an estimate — but CW-4 must not be run live without deciding that first.

### 16.7 Role-bar structure — three changes, 2026-09-21

The bar is the checklist for one role, and it is what CW-3 matches against and what [3] Gap Analyst will measure
against. Three defects were found while testing CW-3; all three are fixed, and `data/rolebars/ROLE_BAR_SPEC.md`
now documents the format.

**1. `aliases` was doing two jobs.** `pgvector`, `ragas`, `langgraph`, `lora`, `nemo guardrails` were all filed
as "other words for the skill". They are **tools you use**, not other names for the skill — "pgvector" is not
another word for *embedding selection & trade-offs*, it is something a candidate may have used without ever
making a trade-off. Split into `aliases` (same claim) and `tools` (weaker evidence). Retrieval now caps a tool
hit at `TOOL_MATCH_CEILING = 75` so naming the skill always outranks naming a tool, and the match kind
(`matched_as: alias | tool`) is sent to the model so it can weigh it.

**2. The numbers had no stated meaning.** `senior: 3` and `weight: 4` appeared with no rubric anywhere in the
file. `depth_scale` and `weight_scale` blocks now sit at the top, **copied from ARITHMETIC_RULES §6** rather
than invented: 0 nothing captured · 1 aware of it · 2 can build with it · 3 can design with it · 4 can defend it
under load. Two authors can no longer mean different things by "3".

**3. Nothing checked for duplicate spellings.** ARITHMETIC_RULES §7 validates unique *keys* and says nothing
about spellings — and a duplicate is silent: retrieval simply offers both, so the model is asked to choose
between two entries a human meant as one. The placeholder bar shipped with one, `"long context"`, claimed by
both `systems.context` and `landscape.capability_limits`. `collisions()` is the lint; the duplicate is removed
(context-window management owns it — a CV saying "long context" describes context work, not market awareness).

**Nothing was invented.** Only existing terms were reclassified, and one duplicate removed. Adding a skill or an
alias is *authoring*, which D5 reserves for two senior engineers — the same reason `evidence_hints` was
considered and **not** added, despite being the field CW-4 would most benefit from.

**Coverage pass (same day, tools only).** Measured against 37 skills a senior AI engineer would plausibly
list, the bar matched **54%**. Four vector databases — FAISS, Chroma, Weaviate, Pinecone — were all absent, so a
candidate whose retrieval work was built on any of them showed **no evidence at all** for retrieval. 30 tool
entries were added to the 9 existing sub-skills that had an obvious home for them: **54% → 81%**, no collisions,
and every new hit correctly labelled `via=tool` rather than credited as naming the skill.

**Still not added, because each would be authoring** (D5): `Python`, `PyTorch`, `Hugging Face`, `Anthropic API`
— the bar has no sub-skill about general programming or model-training frameworks; and `reranking`,
`quantization`, `GPU inference` — techniques with no home in the current 16, which would need a new sub-skill
and a new depth row per level. Those are the shape of what a real authoring pass would add.

**The remaining structural limit:** only **3 of 37** terms offer the model more than one candidate, so CW-3 is
still mostly being asked yes/no rather than to discriminate. That needs more sub-skills, not more tools.

## 17. Scope

**In:** the [1]–[8] pipeline for Senior AI Engineer · checkpoints as CLI prompts / API endpoints · **PostgreSQL** persistence + audit (SQLite for the offline suite, O5) · arithmetic layer · per-agent evals (small) · Appendix E demo.
**Out:** orchestrator/router agents · agent-to-agent anything · teaching content · auth, payments (paywall = flag), frontend, Azure · other roles · Phase 2 (Interviewer, outcome loop) · repo/code ingestion (D1) · resume file parsing beyond plain text.
**Framing for the demo:** real Caliber calls Claude through its own provider layer (the Messages API); this POC shows how Caliber's pipeline looks with **Claude-backed steps on the Agent SDK**. The SDK is Claude-only (D10 caveat).

---

## 18. Demo story (PRD Appendix E)

Synthetic resume → Profiler → confirm → Role Analyst → pick role → gap map → plan (RAG topic is must-know) → Question Generator writes a probe from the candidate's own RAG project → buzzword answer → Evaluator **~21 → gap** ("claims RAG eliminates hallucinations") → Guidance: *go learn reranking, hybrid search, chunk-boundary failure, faithfulness vs relevance* (no teaching) → Adaptation: keep RAG open, move on → retry → **fresh variant** → good answer **~86 → pass** → readiness rises → audit log shows every step.

---

## 19. Environment notes (Windows)

- Python is `py` (plain `python` is the Store stub). Venv: `.venv\Scripts\Activate.ps1` (if blocked: `Set-ExecutionPolicy -Scope Process RemoteSigned`).
- Don't upgrade pip inside the venv on this box — it broke once on a file lock (venv was recreated).
- `pdftotext` exists in Git Bash (`/mingw64/bin`); `pdftoppm` does not.
- Real Caliber repo: `D:\Caliber`. Treat it as read-only from this project. Never copy its `.env` or anything under `ops/` (credentials).
- Needed later: `pip install pyyaml` (to read `data/*.yaml`).

---

## 20. Glossary

**Role-bar** — versioned YAML of what a role is tested on, depth per level. · **Sub-skill** — one bar row (`retrieval.rag_design`). · **Calibration level** — level from years (D6). · **Target level** — the candidate's ambition. · **Evidence strength** — none/mentioned/demonstrated/led. · **Gap map** — prioritised, bucketed gaps. · **Probe-first** — a claim the evidence doesn't back; tested first. · **Checkpoint** — pipeline pause for the candidate. · **StepRun** — one agent call + its audit record. · **CW-n** — Caliber workload id. · **Grounded or dropped** — quote must be verbatim or the claim is discarded. · **D-numbers** — PRD locked decisions (D1–D11). · **FR-I** — PRD AI-pipeline requirements.

## 21. Where things came from

PRD v1.7 (`../Caliber-PRD-v1.7.html`) · sequencing & gates (`reference/plan/SEQUENCING.md`, `BACKLOG.md`, `OPEN-WORK.md`) · as-built arithmetic (`reference/plan/ARITHMETIC_RULES.md`) · agent capabilities & models (`reference/agents/AGENT_CAPABILITIES_AND_MODELS.md`) · handoff (`../CALIBER-POC-CONTEXT.md`) · Caliber snapshot (`reference/README.md` indexes it) · SDK docs: `/agent-sdk/python`, `/agent-sdk/structured-outputs`, `/agent-sdk/quickstart`.
