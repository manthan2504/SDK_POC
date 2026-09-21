"""The pipeline runner: sequence, retries, resume and pauses — all offline.

No agent is called here. Steps are plain async functions, which is exactly the
point of D11: the sequence is testable without a model.
"""

from __future__ import annotations

import asyncio

import pytest
from claude_agent_sdk import (
    CLIConnectionError,
    CLIJSONDecodeError,
    CLINotFoundError,
    ProcessError,
)

from app.agents.base import AgentOutputError, AgentRunError, LLMCallsDisabled
from app.pipeline.runner import (
    MAX_ATTEMPTS,
    Step,
    StepResult,
    classify,
    run_pipeline,
    run_step,
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
)


@pytest.fixture
def store():
    s = Store.in_memory()
    yield s
    s.close()


def run(coro):
    return asyncio.run(coro)


def make_step(execute, **overrides) -> Step:
    fields = dict(number=1, key="profile", title="[1] test step", execute=execute)
    fields.update(overrides)
    return Step(**fields)


def always(value) -> "callable":
    async def _execute(_state, _feedback):
        return StepResult(output=value)

    return _execute


def raises(exc, *, times: int = 99, then=None):
    """A step that fails `times` times and then succeeds."""
    calls = {"n": 0}

    async def _execute(_state, feedback):
        calls["n"] += 1
        if calls["n"] <= times:
            raise exc
        return StepResult(output={"ok": True, "attempts": calls["n"], "feedback": feedback})

    _execute.calls = calls  # type: ignore[attr-defined]
    return _execute


def cause(exc_type, *args):
    """An AgentRunError wrapping an SDK exception, as run_agent builds it."""
    error = AgentRunError("profiler: call failed", "transport")
    error.__cause__ = exc_type(*args)
    return error


# --- classification (N1) -------------------------------------------------
def test_a_schema_failure_is_retried_with_the_problems_fed_back():
    verdict = classify(AgentOutputError("bad", ["roles: required"]))
    assert verdict.retry
    assert verdict.kind == "schema"


def test_a_dropped_connection_is_retried():
    assert classify(cause(CLIConnectionError, "connection lost")).retry


def test_a_crashed_cli_process_is_retried():
    assert classify(cause(ProcessError, "exited 1")).retry


def test_a_missing_cli_is_never_retried():
    """Retrying a missing binary spends three attempts proving it is still missing."""
    verdict = classify(cause(CLINotFoundError, "claude not found"))
    assert not verdict.retry
    assert "installation" in verdict.reason


def test_unreadable_cli_output_is_never_retried():
    assert not classify(cause(CLIJSONDecodeError, "{", ValueError("boom"))).retry


def test_a_budget_ceiling_is_never_retried():
    """§16.2: the ceiling is ours. The next attempt pays the same price to stop
    in the same place."""
    verdict = classify(AgentRunError("stopped", "error_max_budget_usd"))
    assert not verdict.retry
    assert "ceiling" in verdict.reason


def test_a_turn_ceiling_is_never_retried():
    assert not classify(AgentRunError("stopped", "error_max_turns")).retry


def test_the_sdks_own_schema_retries_are_not_repeated():
    verdict = classify(AgentRunError("gave up", "error_max_structured_output_retries"))
    assert not verdict.retry
    assert "already retried" in verdict.reason


def test_a_closed_gate_is_a_decision_not_a_fault():
    verdict = classify(LLMCallsDisabled("gate closed"))
    assert not verdict.retry
    assert verdict.kind == "gate"


def test_our_own_bug_is_never_retried():
    verdict = classify(ValueError("resume text is empty"))
    assert not verdict.retry
    assert verdict.kind == "internal"


def test_an_unknown_failure_gets_another_attempt():
    assert classify(AgentRunError("odd", "no_result")).retry


# --- one step ------------------------------------------------------------
def test_a_step_that_works_is_recorded_once(store):
    run_id = store.create_run().run_id
    result, error = run(run_step(make_step(always({"roles": []})), {}, store, run_id))
    assert error is None and result.output == {"roles": []}
    assert [a.status for a in store.attempts(run_id)] == [OK]


def test_a_retryable_failure_is_retried_and_every_attempt_is_kept(store):
    run_id = store.create_run().run_id
    execute = raises(AgentOutputError("bad", ["roles: required"]), times=1)
    result, error = run(run_step(make_step(execute), {}, store, run_id))
    assert error is None
    assert result.output["attempts"] == 2
    assert [a.status for a in store.attempts(run_id)] == [FAILED_ATTEMPT, OK]


def test_the_repair_retry_feeds_the_problems_back(store):
    run_id = store.create_run().run_id
    execute = raises(AgentOutputError("bad", ["roles.0.title: required"]), times=1)
    result, _ = run(run_step(make_step(execute), {}, store, run_id))
    assert result.output["feedback"] == ["roles.0.title: required"]


def test_retries_stop_at_the_limit(store):
    run_id = store.create_run().run_id
    execute = raises(AgentOutputError("bad", ["nope"]))
    result, error = run(run_step(make_step(execute), {}, store, run_id))
    assert result is None
    assert "gave up" in error
    assert len(store.attempts(run_id)) == MAX_ATTEMPTS


def test_a_fatal_failure_is_not_retried_at_all(store):
    run_id = store.create_run().run_id
    execute = raises(AgentRunError("stopped", "error_max_budget_usd"))
    result, error = run(run_step(make_step(execute), {}, store, run_id))
    assert result is None
    assert "ceiling" in error
    assert len(store.attempts(run_id)) == 1  # not 3


def test_a_salvaged_result_is_never_run_again(store):
    """It is finished work: validated, and already paid for."""
    calls = {"n": 0}

    async def execute(_state, _feedback):
        calls["n"] += 1
        return StepResult(output={"roles": []}, salvaged=True)

    run_id = store.create_run().run_id
    result, error = run(run_step(make_step(execute), {}, store, run_id))
    assert error is None and result.salvaged
    assert calls["n"] == 1
    assert [a.status for a in store.attempts(run_id)] == [SALVAGED]


def test_a_failed_attempt_still_records_its_audit_meta(store):
    """A failure that cost money must still say what it cost."""
    from tests.test_pipeline_store import make_meta

    error = AgentOutputError("bad", ["nope"], meta=make_meta(total_cost_usd=0.02))
    run_id = store.create_run().run_id
    run(run_step(make_step(raises(error)), {}, store, run_id))
    assert store.cost(run_id) == pytest.approx(0.06)  # three attempts, all charged


# --- the whole pipeline --------------------------------------------------
def test_a_pipeline_runs_its_steps_in_number_order(store):
    order = []

    def recorder(name):
        async def _execute(_state, _feedback):
            order.append(name)
            return StepResult(output=name)

        return _execute

    steps = [
        make_step(recorder("second"), number=2, key="b"),
        make_step(recorder("first"), number=1, key="a"),
    ]
    outcome = run(run_pipeline(steps, {}, store))
    assert order == ["first", "second"]
    assert outcome.status == DONE
    assert store.get_run(outcome.run_id).status == DONE


def test_one_step_can_read_what_the_previous_step_produced(store):
    async def first(_state, _feedback):
        return StepResult(output={"years": 6})

    async def second(state, _feedback):
        return StepResult(output={"level": "mid" if state["a"]["years"] < 8 else "senior"})

    steps = [make_step(first, number=1, key="a"), make_step(second, number=2, key="b")]
    outcome = run(run_pipeline(steps, {}, store))
    assert outcome.outputs["b"] == {"level": "mid"}


def test_a_failing_step_stops_the_pipeline_before_the_next_one(store):
    """FR-I9: downstream never runs on invalid data."""
    reached = []

    async def second(_state, _feedback):
        reached.append(True)
        return StepResult(output="never")

    steps = [
        make_step(raises(AgentRunError("stopped", "error_max_budget_usd")), number=1, key="a"),
        make_step(second, number=2, key="b"),
    ]
    outcome = run(run_pipeline(steps, {}, store))
    assert outcome.status == FAILED and outcome.at_step == 1
    assert reached == []
    assert store.get_run(outcome.run_id).failed_reason.startswith("a:")


# --- checkpoints (FR-I11) ------------------------------------------------
def test_the_run_pauses_at_a_checkpoint_and_returns(store):
    steps = [
        make_step(always("done"), number=1, key="a", checkpoint_for=lambda _o: "confirm_profile"),
        make_step(always("next"), number=2, key="b"),
    ]
    outcome = run(run_pipeline(steps, {}, store))
    assert outcome.status == WAITING
    assert outcome.waiting_for == "confirm_profile"
    assert "b" not in outcome.outputs
    assert store.get_run(outcome.run_id).status == WAITING


def test_answering_the_checkpoint_resumes_without_re_running_the_step(store):
    calls = {"n": 0}

    async def first(_state, _feedback):
        calls["n"] += 1
        return StepResult(output="done")

    steps = [
        make_step(first, number=1, key="a", checkpoint_for=lambda _o: "confirm_profile"),
        make_step(always("next"), number=2, key="b"),
    ]
    paused = run(run_pipeline(steps, {}, store))
    store.decide(paused.run_id, "confirm_profile", {"confirmed": True})
    resumed = run(run_pipeline(steps, {}, store, run_id=paused.run_id))

    assert resumed.status == DONE
    assert calls["n"] == 1  # FR-I8: resuming reads the store, it does not re-call
    assert resumed.outputs["a"] == "done"


def test_a_repeating_checkpoint_runs_the_same_step_again(store):
    """The Profiler's completeness loop: answers come back, the step runs again."""
    calls = {"n": 0}

    async def profiler(state, _feedback):
        calls["n"] += 1
        complete = bool(state.get("answers"))
        return StepResult(output={"complete": complete})

    step = make_step(
        profiler,
        checkpoint_for=lambda out: None if out["complete"] else "answers_needed",
        repeat_after=frozenset({"answers_needed"}),
        revive=lambda raw: raw,
    )
    paused = run(run_pipeline([step], {}, store))
    assert paused.waiting_for == "answers_needed"

    store.decide(paused.run_id, "answers_needed", [{"key": "role:r1:title", "answer": "Engineer"}])
    resumed = run(run_pipeline([step], {}, store, run_id=paused.run_id))

    assert resumed.status == DONE
    assert calls["n"] == 2  # ran again, with the answers
    assert resumed.outputs["profile"] == {"complete": True}


def test_a_resumed_step_is_revived_into_its_own_type(store):
    """Step [2] must not receive a dict on a resumed run and an object on a fresh one."""

    class Profile:
        def __init__(self, years):
            self.years = years

        def model_dump(self, mode="json"):
            return {"years": self.years}

    steps = [
        make_step(always(Profile(6)), number=1, key="a",
                  checkpoint_for=lambda _o: "confirm_profile",
                  revive=lambda raw: Profile(raw["years"])),
        make_step(always("next"), number=2, key="b"),
    ]
    paused = run(run_pipeline(steps, {}, store))
    store.decide(paused.run_id, "confirm_profile", {"confirmed": True})
    resumed = run(run_pipeline(steps, {}, store, run_id=paused.run_id))
    assert isinstance(resumed.outputs["a"], Profile)
    assert resumed.outputs["a"].years == 6


def test_a_finished_run_can_be_replayed_without_calling_anything(store):
    calls = {"n": 0}

    async def once(_state, _feedback):
        calls["n"] += 1
        return StepResult(output="done")

    steps = [make_step(once, number=1, key="a")]
    first = run(run_pipeline(steps, {}, store))
    again = run(run_pipeline(steps, {}, store, run_id=first.run_id))
    assert again.status == DONE
    assert calls["n"] == 1


# --- rule 9: the row exists before the call ------------------------------
def test_the_attempt_row_exists_while_the_step_is_still_running(store):
    """RULEBOOK §4 rule 9. Caliber wrote that rule after a rolled-back request
    took the trace row with it — a step that dies mid-call must leave evidence."""
    seen = {}

    async def execute(_state, _feedback):
        rows = store.attempts(run_id)
        seen["during"] = [(r.status, r.finished_at) for r in rows]
        return StepResult(output="done")

    run_id = store.create_run().run_id
    run(run_step(make_step(execute), {}, store, run_id))

    assert seen["during"] == [(RUNNING, None)]  # open row, no finish time yet
    assert [a.status for a in store.attempts(run_id)] == [OK]


def test_a_step_that_dies_mid_call_still_left_a_row(store):
    """The process-killed case: nothing closes the row, but it is not lost."""

    async def execute(_state, _feedback):
        raise KeyboardInterrupt("pretend the machine rebooted")

    run_id = store.create_run().run_id
    with pytest.raises(KeyboardInterrupt):
        run(run_step(make_step(execute), {}, store, run_id))
    rows = store.attempts(run_id)
    assert [r.status for r in rows] == [RUNNING]
    assert rows[0].finished_at is None


def test_a_fake_query_fn_is_never_counted_as_a_billed_call(store):
    """Caliber's `served_from`: a fixture reply must not look like provider traffic."""
    run_id = store.create_run().run_id
    run(run_step(make_step(always("x")), {"query_fn": lambda **_: None}, store, run_id))
    assert store.attempts(run_id)[0].served_from == SERVED_FAKE

    other = store.create_run().run_id
    run(run_step(make_step(always("x")), {}, store, other))
    assert store.attempts(other)[0].served_from == SERVED_PROVIDER


# --- FR-I8: the run's own inputs survive ---------------------------------
def test_the_runs_own_inputs_are_saved_and_reloaded(store):
    """Step [1]'s input is nobody's output, so step outputs alone cannot resume it."""
    steps = [make_step(always("done"), checkpoint_for=lambda _o: "confirm_profile")]
    paused = run(run_pipeline(steps, {}, store, inputs={"resume_text": "Ravi Menon…"}))
    assert store.inputs(paused.run_id)["resume_text"].payload == "Ravi Menon…"

    # A fresh process: empty state, no inputs passed again.
    fresh: dict = {}
    store.decide(paused.run_id, "confirm_profile", {"confirmed": True})
    run(run_pipeline(steps, fresh, store, run_id=paused.run_id))
    assert fresh["resume_text"] == "Ravi Menon…"


def test_answers_accumulate_across_completeness_loops(store):
    """Two rounds of questions must not erase the first round's answers."""
    rounds = {"n": 0}

    async def profiler(state, _feedback):
        rounds["n"] += 1
        return StepResult(output={"complete": len(state.get("answers", [])) >= 2})

    step = make_step(
        profiler,
        checkpoint_for=lambda out: None if out["complete"] else "answers_needed",
        repeat_after=frozenset({"answers_needed"}),
    )
    outcome = run(run_pipeline([step], {}, store))
    for answer in ("first", "second"):
        store.decide(outcome.run_id, "answers_needed", [{"key": answer, "answer": answer}])
        outcome = run(run_pipeline([step], {}, store, run_id=outcome.run_id))

    assert outcome.status == DONE
    saved = store.inputs(outcome.run_id)["answers"].payload
    assert [a["key"] for a in saved] == ["first", "second"]
