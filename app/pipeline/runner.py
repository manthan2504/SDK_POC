"""The pipeline runner — plain Python owns the sequence (D11 / ADR-0008).

There is no orchestrator agent, and this file is the proof: the order of steps,
the retries, the pauses and the saving are ordinary code that can be read,
tested offline, and stepped through in a debugger. An agent is a function this
code calls; it never calls back.

Four rules from RULEBOOK §4 live here, and nowhere else:

  4. Save before next   — a step's output is persisted before the next step runs
  5. Retry then fail    — up to 2 retries, then the step is failed and the run
                          stops; downstream never sees invalid data (FR-I9)
  6. Audit every step   — every attempt becomes a step_runs row, failures too
 11. Checkpoints        — the app pauses and returns; nothing blocks on input

Two rules were bought with real money on 2026-09-21 (RULEBOOK §16.2):

  * **Never retry a salvaged result.** It already validated and was already paid
    for. Retrying would buy a second copy of an answer we hold.
  * **Never retry a ceiling.** A budget or turn ceiling with no usable payload
    will be hit again in exactly the same place; a retry pays the full price for
    the same failure. Fail the step and let a human change the ceiling.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import (
    CLIConnectionError,
    CLIJSONDecodeError,
    CLINotFoundError,
    ProcessError,
)

from app.agents.base import (
    AgentOutputError,
    AgentRunError,
    CallMeta,
    LLMCallsDisabled,
)
from app.pipeline.store import (
    DONE,
    FAILED,
    FAILED_ATTEMPT,
    OK,
    RUNNING,
    SALVAGED,
    SERVED_FAKE,
    SERVED_PROVIDER,
    WAITING,
    Store,
    _now,
)

# PRD says 2 retries; Caliber's code does 1. O4 settled it: the PRD wins.
MAX_ATTEMPTS = 3  # the first try plus two retries


# ---------------------------------------------------------------------------
# What a step is
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StepResult:
    """What a step hands back. `output` must be JSON-serialisable for the store."""

    output: Any
    meta: CallMeta | None = None
    salvaged: bool = False


@dataclass(frozen=True)
class Step:
    """One position in the fixed pipeline.

    `execute(state, feedback)` does the work. `feedback` carries the validation
    problems from the previous attempt, so a repair retry can tell the model what
    was wrong — the runner never inspects it.

    `checkpoint_for(output)` names a pause to take AFTER the step, or None to go
    straight on. A checkpoint whose key is in `repeat_after` sends the run back
    through this same step once the candidate has answered (that is the Profiler's
    completeness loop); any other checkpoint advances.
    """

    number: int
    key: str
    title: str
    execute: Callable[[dict[str, Any], list[str]], Awaitable[StepResult]]
    checkpoint_for: Callable[[Any], str | None] = lambda _output: None
    repeat_after: frozenset[str] = frozenset()
    # Rebuild the step's own type from the JSON the store handed back, so a
    # resumed run works with the same object a fresh run produced. Without this,
    # step [2] would receive a CandidateProfile on Tuesday and a dict on Wednesday.
    revive: Callable[[Any], Any] = lambda raw: raw


@dataclass
class PipelineOutcome:
    run_id: str
    status: str  # done | waiting | failed
    at_step: int | None = None
    waiting_for: str | None = None
    error: str | None = None
    outputs: dict[str, Any] = field(default_factory=dict)
    attempts: int = 0

    @property
    def finished(self) -> bool:
        return self.status == DONE


# ---------------------------------------------------------------------------
# Retry classification (RULEBOOK §3.6 N1)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Verdict:
    retry: bool
    reason: str
    kind: str


# A ceiling we set ourselves. Reaching it again costs the same money for the same
# outcome, so these are fatal to the step (see §16.2).
_CEILINGS = frozenset({"error_max_budget_usd", "error_max_turns"})

# The SDK already retried the schema internally before giving up; our own retry
# sends the identical prompt to the identical model.
_ALREADY_RETRIED = frozenset({"error_max_structured_output_retries"})

# Transport faults worth trying again — the call never reached a conclusion.
_RETRYABLE_CAUSES = (CLIConnectionError, ProcessError)

# Something is wrong with the installation or the protocol, not with this call.
_FATAL_CAUSES = (CLINotFoundError, CLIJSONDecodeError)


def classify(exc: BaseException) -> Verdict:
    """Decide whether one failed attempt is worth repeating.

    `run_agent()` wraps every SDK exception as AgentRunError(kind="transport"),
    so the useful detail is on `__cause__` — that is what N1 exists to read.
    """
    if isinstance(exc, LLMCallsDisabled):
        return Verdict(False, "live calls are disabled; this is a decision, not a fault", "gate")

    if isinstance(exc, AgentOutputError):
        # The model answered but broke its contract. A repair retry gets the
        # problems fed back, which is the one retry that reliably changes.
        return Verdict(True, "output failed validation; retrying with the problems fed back", "schema")

    if isinstance(exc, AgentRunError):
        if exc.kind in _CEILINGS:
            return Verdict(False, f"{exc.kind}: a ceiling we set; a retry pays the same price for the same stop", exc.kind)
        if exc.kind in _ALREADY_RETRIED:
            return Verdict(False, f"{exc.kind}: the SDK already retried the schema internally", exc.kind)

        cause = exc.__cause__
        if isinstance(cause, _FATAL_CAUSES):
            return Verdict(False, f"{type(cause).__name__}: the installation or protocol is wrong, not this call", exc.kind)
        if isinstance(cause, _RETRYABLE_CAUSES):
            return Verdict(True, f"{type(cause).__name__}: transport fault, worth another attempt", exc.kind)
        return Verdict(True, f"{exc.kind}: unknown failure, worth another attempt", exc.kind)

    # A bug in our own code (bad input, missing prompt file). Identical input
    # would fail identically.
    return Verdict(False, f"{type(exc).__name__}: not a provider failure", "internal")


# ---------------------------------------------------------------------------
# Running one step
# ---------------------------------------------------------------------------
async def run_step(
    step: Step,
    state: dict[str, Any],
    store: Store,
    run_id: str,
) -> tuple[StepResult | None, str | None]:
    """Run one step until it succeeds or gives up. Returns (result, error).

    Every attempt is written to step_runs before this returns — including the
    failures, and including the last one.
    """
    feedback: list[str] = []
    last_error: str | None = None
    # A fake `query_fn` means a test or an offline demo. Caliber's own gate
    # asserts on this column so a fixture reply can never be counted as billed.
    served_from = SERVED_FAKE if state.get("query_fn") is not None else SERVED_PROVIDER

    for _ in range(MAX_ATTEMPTS):
        attempt = store.next_attempt(run_id, step.number)
        started = _now()
        # Rule 9: the row exists BEFORE the call. A step that dies mid-call —
        # process killed, machine rebooted — leaves a `running` row saying so,
        # instead of no evidence that it ever ran.
        attempt_id = store.start_attempt(
            run_id=run_id,
            step=step.number,
            step_key=step.key,
            attempt=attempt,
            started_at=started,
            served_from=served_from,
        )
        try:
            result = await step.execute(state, feedback)
        # Exception, never BaseException: a Ctrl-C or a SystemExit is not a step
        # failure to be classified and retried — it must propagate. The `running`
        # row stays open, which is the honest record of a call that was cut off.
        except Exception as exc:  # noqa: BLE001 - classified immediately below
            verdict = classify(exc)
            store.finish_attempt(
                attempt_id,
                status=FAILED_ATTEMPT,
                meta=getattr(exc, "meta", None),
                error_kind=verdict.kind,
                problems=list(getattr(exc, "problems", []) or []) or [verdict.reason],
                served_from=served_from,
            )
            last_error = f"{step.key}: {exc}"
            if not verdict.retry:
                return None, f"{last_error} [{verdict.reason}]"
            feedback = list(getattr(exc, "problems", []) or [])
            continue

        store.finish_attempt(
            attempt_id,
            status=SALVAGED if result.salvaged else OK,
            meta=result.meta,
            output=_jsonable(result.output),
            served_from=served_from,
        )
        # A salvaged result is finished work. Nothing below re-runs it.
        return result, None

    return None, f"{last_error} [gave up after {MAX_ATTEMPTS} attempts]"


# ---------------------------------------------------------------------------
# Running the pipeline
# ---------------------------------------------------------------------------
async def run_pipeline(
    steps: list[Step],
    state: dict[str, Any],
    store: Store,
    run_id: str | None = None,
    inputs: dict[str, Any] | None = None,
) -> PipelineOutcome:
    """Run the fixed sequence from wherever it left off.

    Call it again with the same run_id after answering a checkpoint and it picks
    up at the same place — completed steps are read back from the store, not
    re-run, so resuming costs nothing (FR-I8).

    `inputs` is the run's OWN material (resume text, and later the target role):
    saved on the first call, reloaded on every later one. Step outputs alone are
    not enough — step [1]'s input is nobody's output, so without this a resume in
    a fresh process could not re-run step [1] at all.

    `state` also carries things that cannot be persisted, such as a `query_fn`;
    those are passed fresh each call and never stored.
    """
    record = store.create_run() if run_id is None else store.get_run(run_id)
    run_id = record.run_id
    outcome = PipelineOutcome(run_id=run_id, status=RUNNING)

    for key, value in (inputs or {}).items():
        store.save_input(run_id, key, value)
        state[key] = value
    # A resumed run may arrive with an empty state; the store is the source.
    for key, saved in store.inputs(run_id).items():
        state.setdefault(key, saved.payload)

    done = store.completed(run_id)
    for step in sorted(steps, key=lambda s: s.number):
        previous = done.get(step.number)
        if previous is not None:
            restored = step.revive(previous.output)
            outcome.outputs[step.key] = restored
            state[step.key] = restored
            checkpoint = step.checkpoint_for(restored)
            if checkpoint and not store.decided(run_id, checkpoint):
                return _pause(store, outcome, step, checkpoint)
            if checkpoint in step.repeat_after:
                # The candidate has answered; this step runs again with the answer.
                # Answers accumulate across loops and are saved as a run input, so
                # the second round is reproducible from the store alone.
                answers = [*state.get("answers", []), *(store.decision(run_id, checkpoint) or [])]
                state["answers"] = answers
                store.save_input(run_id, "answers", answers)
                store.clear_decision(run_id, checkpoint)
            else:
                continue  # already done and confirmed

        store.set_status(run_id, RUNNING, current_step=step.number)
        result, error = await run_step(step, state, store, run_id)
        outcome.attempts = len(store.attempts(run_id))

        if error is not None:
            store.set_status(run_id, FAILED, current_step=step.number, failed_reason=error)
            outcome.status, outcome.at_step, outcome.error = FAILED, step.number, error
            return outcome

        assert result is not None
        outcome.outputs[step.key] = result.output
        state[step.key] = result.output

        checkpoint = step.checkpoint_for(result.output)
        if checkpoint and not store.decided(run_id, checkpoint):
            return _pause(store, outcome, step, checkpoint)

    store.set_status(run_id, DONE)
    outcome.status = DONE
    return outcome


def _pause(store: Store, outcome: PipelineOutcome, step: Step, checkpoint: str) -> PipelineOutcome:
    """A checkpoint is an app pause, not a prompt: we return, we do not block."""
    store.set_status(outcome.run_id, WAITING, current_step=step.number, waiting_for=checkpoint)
    outcome.status, outcome.at_step, outcome.waiting_for = WAITING, step.number, checkpoint
    return outcome


def _jsonable(output: Any) -> Any:
    """Pydantic models go in as plain JSON so the row is readable without our code."""
    dump = getattr(output, "model_dump", None)
    return dump(mode="json") if callable(dump) else output
