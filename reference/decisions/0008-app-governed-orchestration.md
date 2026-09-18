# ADR-0008: App-governed orchestration — no orchestrator agent

## Status
Accepted — 2026-09-01 (user decision)

## Context
Multi-agent platforms commonly put a manager/orchestrator *agent* at the top: an LLM that
decomposes work and routes to other LLMs. The reference study (AI-Agent-Fleet) is built that
way. Caliber's journey, by contrast, is a **fixed pipeline** the PRD already sequences
(§7.1 → §7.7): parse, confirm, bar, gaps, plan, probe, grade, guide. There is nothing for a
model to decide about *order* — only about *content* at each step.

## Decision
**Deterministic Python code + a per-user state row call the dedicated agents step by step in
the fixed §7 order.** Agents never talk to each other; the app validates and saves between
every step. An LLM never routes, never dispatches, never owns the loop. This is the
"deterministic task routing" idea taken one step further: Caliber's routing table is the
product flow itself, so it is code, not even a classifier.

The **Adaptation agent** (in-assessment "next move" suggester) is DEFERRED; when it comes,
it suggests from a menu and the app decides — the pattern is preserved.

## Alternatives considered
- **Executive-orchestrator agent (reference-study shape).** Rejected: adds a reasoning loop
  whose every correct output equals what the FSM already encodes, and whose every incorrect
  output is a new failure mode. Suits open-ended objectives; Caliber's objective is fixed.
- **Workflow engine / LangGraph.** Rejected for now per TECH_STACK ("no heavyweight
  framework"); revisit only if a real branching flow appears.

## Consequences
- Task ownership, retries, and failure states live in `job_run` + app code — observable and
  testable without a model call.
- Agent-to-agent injection surface is structurally absent (no agent consumes another agent's
  raw output without the app validating between).
- The division of labour stays intact: *arithmetic owns dated facts; the model owns
  ambiguity; the app owns sequence.*

## Enforced by
`docs/llm/04-routing.md` §4 (call-flow rule); code review gate — a diff introducing an
agent-calls-agent path is an architecture violation.

## Sources
Plan `soft-kindling-pony` § Orchestration settled (2026-09-01); `docs/TECH_STACK.md` AI-agent layer.
