"""The run store: what survives between steps (RULEBOOK §4 rules 4, 6 and 9).

This file is a **conformance suite**: every test runs twice, once against
SQLite and once against PostgreSQL, so the two backends cannot drift without a
red test. The Postgres parameter is marked `postgres` — excluded from the
default run by `pytest.ini` — and skips outright unless `POC_TEST_DATABASE_URL`
names a throwaway database. `pytest -q` therefore still needs no service, which
is the whole point (and is how Caliber runs its own ~790 tests).
"""

from __future__ import annotations

import pytest

from app.agents.base import CallMeta
from app.config import POC_TEST_DATABASE_URL
from app.pipeline.store import (
    DONE,
    FAILED_ATTEMPT,
    OK,
    RUNNING,
    SALVAGED,
    SERVED_FAKE,
    SERVED_PROVIDER,
    WAITING,
    PostgresStore,
    SqliteStore,
    Store,
    open_store,
    sha256_of,
)

# Real timestamps, because `timestamptz` is a real type: SQLite would take "t0"
# and Postgres would not, and a conformance suite may not lean on that.
T0 = "2026-09-21T10:00:00+00:00"
T1 = "2026-09-21T10:01:00+00:00"

BACKENDS = [
    pytest.param("sqlite", id="sqlite"),
    pytest.param("postgres", id="postgres", marks=pytest.mark.postgres),
]

_PG_TABLES = ("run_inputs", "checkpoints", "step_runs", "runs")


@pytest.fixture(params=BACKENDS)
def store_factory(request, tmp_path):
    """Opens stores on the SAME database, so "survives the process" is testable."""
    opened: list[Store] = []

    if request.param == "sqlite":
        path = tmp_path / "caliber.db"

        def make() -> Store:
            store = Store.open(path)
            opened.append(store)
            return store
    else:
        if not POC_TEST_DATABASE_URL:
            pytest.skip("POC_TEST_DATABASE_URL is not set — no Postgres to conform against")

        def make() -> Store:
            store = Store.from_url(POC_TEST_DATABASE_URL)
            opened.append(store)
            return store

        # A shared server keeps rows between tests; a fresh SQLite file does not.
        first = make()
        first.db.execute(
            "TRUNCATE " + ", ".join(_PG_TABLES) + " RESTART IDENTITY CASCADE"
        )
        first.db.commit()

    yield make

    for store in opened:
        store.close()


@pytest.fixture
def store(store_factory):
    return store_factory()


def make_meta(**overrides) -> CallMeta:
    fields = dict(
        agent="profiler",
        prompt_version="profiler.v2",
        prompt_sha256="abc123",
        model_requested="claude-haiku-4-5",
        effort=None,
        input_sha256="def456",
        started_at=T0,
        cw="cw-1",
    )
    meta = CallMeta(**fields)
    for key, value in overrides.items():
        setattr(meta, key, value)
    return meta


# --- backend selection ---------------------------------------------------
def test_the_url_picks_the_backend(tmp_path):
    """One place decides, and it is the URL — never a flag (§4B of the research)."""
    assert issubclass(PostgresStore, Store) and issubclass(SqliteStore, Store)
    assert PostgresStore.placeholder == "%s" and SqliteStore.placeholder == "?"
    for url in ("sqlite:///:memory:", f"sqlite:///{tmp_path / 'a.db'}", str(tmp_path / "b.db")):
        store = Store.from_url(url)
        try:
            assert isinstance(store, SqliteStore)
        finally:
            store.close()
    # Postgres is chosen by scheme alone — no connection is attempted here.
    assert "postgresql://x/y".split("://", 1)[0] == "postgresql"


def test_in_memory_still_needs_no_file_and_no_service():
    """42 existing tests construct their store this way; it must not change."""
    s = Store.in_memory()
    try:
        run = s.create_run()
        assert s.get_run(run.run_id).status == RUNNING
    finally:
        s.close()


# --- runs ----------------------------------------------------------------
def test_a_new_run_starts_running_with_an_id(store):
    run = store.create_run()
    assert run.status == RUNNING
    assert len(run.run_id) == 32
    assert store.get_run(run.run_id).created_at == run.created_at


def test_an_unknown_run_is_a_key_error(store):
    with pytest.raises(KeyError):
        store.get_run("nope")


def test_status_carries_why_it_stopped(store):
    run = store.create_run()
    store.set_status(run.run_id, WAITING, current_step=1, waiting_for="confirm_profile")
    again = store.get_run(run.run_id)
    assert (again.status, again.current_step, again.waiting_for) == (WAITING, 1, "confirm_profile")


def test_runs_are_listed_newest_first(store):
    store.create_run("older")
    store.create_run("newer")
    assert {r.run_id for r in store.list_runs()} == {"older", "newer"}


def test_an_unknown_status_is_refused_by_the_application(store):
    """The column is plain `text` on both backends; the vocabulary is checked here."""
    run = store.create_run()
    with pytest.raises(ValueError):
        store.set_status(run.run_id, "nearly-done")


# --- attempts ------------------------------------------------------------
def test_attempt_numbers_count_up_per_step(store):
    run = store.create_run()
    assert store.next_attempt(run.run_id, 1) == 1
    store.record_attempt(
        run_id=run.run_id, step=1, step_key="profile", attempt=1,
        status=FAILED_ATTEMPT, started_at=T0, error_kind="schema", problems=["bad"],
    )
    assert store.next_attempt(run.run_id, 1) == 2
    assert store.next_attempt(run.run_id, 2) == 1  # a different step starts over


def test_a_failed_attempt_is_kept_not_overwritten(store):
    """'Succeeded on the third try' is a different fact from 'succeeded'."""
    run = store.create_run()
    store.record_attempt(
        run_id=run.run_id, step=1, step_key="profile", attempt=1,
        status=FAILED_ATTEMPT, started_at=T0, error_kind="schema", problems=["roles: required"],
    )
    store.record_attempt(
        run_id=run.run_id, step=1, step_key="profile", attempt=2,
        status=OK, started_at=T1, meta=make_meta(total_cost_usd=0.01), output={"roles": []},
    )
    attempts = store.attempts(run.run_id)
    assert [a.status for a in attempts] == [FAILED_ATTEMPT, OK]
    assert attempts[0].problems == ["roles: required"]
    assert attempts[1].output == {"roles": []}


def test_completed_keeps_only_the_successful_attempt_per_step(store):
    run = store.create_run()
    store.record_attempt(run_id=run.run_id, step=1, step_key="profile", attempt=1,
                         status=FAILED_ATTEMPT, started_at=T0, error_kind="transport")
    store.record_attempt(run_id=run.run_id, step=1, step_key="profile", attempt=2,
                         status=OK, started_at=T1, output={"ok": True})
    done = store.completed(run.run_id)
    assert list(done) == [1]
    assert done[1].attempt == 2


def test_a_salvaged_attempt_counts_as_completed(store):
    """It validated and it was paid for — a resume must not run it again (§16.2)."""
    run = store.create_run()
    store.record_attempt(
        run_id=run.run_id, step=1, step_key="profile", attempt=1, status=SALVAGED,
        started_at=T0, meta=make_meta(salvaged_from="error_max_budget_usd", total_cost_usd=0.11),
        output={"roles": []},
    )
    record = store.completed(run.run_id)[1]
    assert record.succeeded
    assert record.salvaged_from == "error_max_budget_usd"


def test_cost_counts_failed_attempts_too(store):
    run = store.create_run()
    store.record_attempt(run_id=run.run_id, step=1, step_key="profile", attempt=1,
                         status=FAILED_ATTEMPT, started_at=T0,
                         meta=make_meta(total_cost_usd=0.02), error_kind="schema")
    store.record_attempt(run_id=run.run_id, step=1, step_key="profile", attempt=2,
                         status=OK, started_at=T1, meta=make_meta(total_cost_usd=0.03))
    assert store.cost(run.run_id) == pytest.approx(0.05)


def test_the_cost_of_a_run_that_hit_the_ceiling_is_exact(store):
    """§16.2: $0.1107 against a $0.10 ceiling is a number that decides an outcome.

    `numeric(12,6)` on Postgres, cast to float only at the dataclass boundary.
    """
    run = store.create_run()
    for n, spend in enumerate([0.0369, 0.0369, 0.0369], start=1):
        store.record_attempt(run_id=run.run_id, step=1, step_key="profile", attempt=n,
                             status=FAILED_ATTEMPT, started_at=T0,
                             meta=make_meta(total_cost_usd=spend), error_kind="schema")
    assert store.cost(run.run_id) == pytest.approx(0.1107)
    assert isinstance(store.attempts(run.run_id)[0].total_cost_usd, float)


def test_the_audit_row_carries_the_call_facts(store):
    run = store.create_run()
    store.record_attempt(
        run_id=run.run_id, step=1, step_key="profile", attempt=1, status=OK, started_at=T0,
        meta=make_meta(subtype="success", session_id="sess-9", total_cost_usd=0.012,
                       input_tokens=400, output_tokens=18191),
        output={"roles": []},
    )
    row = store.db.execute("SELECT * FROM step_runs").fetchone()
    assert row["prompt_version"] == "profiler.v2"
    assert row["prompt_sha256"] == "abc123"
    assert row["model_requested"] == "claude-haiku-4-5"
    assert row["cw"] == "cw-1"
    assert row["output_tokens"] == 18191
    assert row["session_id"] == "sess-9"


def test_the_audit_row_holds_no_prompt_text(store):
    """§11: hashes and versions, never the candidate's words."""
    run = store.create_run()
    store.record_attempt(run_id=run.run_id, step=1, step_key="profile", attempt=1,
                         status=OK, started_at=T0, meta=make_meta())
    row = dict(store.db.execute("SELECT * FROM step_runs").fetchone())
    assert "resume" not in str(row).lower()


# --- record before you call (RULEBOOK §4 rule 9) -------------------------
def test_an_attempt_is_recorded_before_the_call_and_closed_after(store):
    """A step that dies mid-call still left a row. That is the whole rule."""
    run = store.create_run()
    attempt_id = store.start_attempt(
        run_id=run.run_id, step=1, step_key="profile", attempt=1,
        started_at=T0, meta=make_meta(),
    )

    in_flight = store.attempts(run.run_id)[0]
    assert in_flight.status == RUNNING
    assert in_flight.finished_at is None
    assert in_flight.agent == "profiler"          # the pre-call facts are already there
    assert in_flight.input_sha256 == "def456"
    assert store.completed(run.run_id) == {}      # and a resume does not mistake it for done

    store.finish_attempt(attempt_id, status=OK, meta=make_meta(total_cost_usd=0.01),
                         output={"roles": []})

    closed = store.attempts(run.run_id)[0]
    assert (closed.status, closed.output) == (OK, {"roles": []})
    assert closed.finished_at is not None
    assert len(store.attempts(run.run_id)) == 1   # updated, not a second row


def test_record_attempt_is_the_same_two_writes(store):
    """The runner's 26 tests still call `record_attempt`; it must not change."""
    run = store.create_run()
    record = store.record_attempt(
        run_id=run.run_id, step=2, step_key="role", attempt=1, status=OK,
        started_at=T0, meta=make_meta(), output={"fit": "stretch"},
    )
    assert record.status == OK and record.finished_at is not None
    assert store.completed(run.run_id)[2].output == {"fit": "stretch"}


def test_finishing_an_unknown_attempt_is_a_key_error(store):
    store.create_run()
    with pytest.raises(KeyError):
        store.finish_attempt(9999, status=OK)


# --- provenance columns --------------------------------------------------
def test_served_from_keeps_a_fixture_reply_out_of_the_billed_column(store):
    """Caliber's S0 gate asserts on this field; 590 offline tests need it too."""
    run = store.create_run()
    store.record_attempt(run_id=run.run_id, step=1, step_key="profile", attempt=1,
                         status=OK, started_at=T0, meta=make_meta(), served_from=SERVED_FAKE)
    store.record_attempt(run_id=run.run_id, step=2, step_key="role", attempt=1,
                         status=OK, started_at=T0, meta=make_meta(),
                         served_from=SERVED_PROVIDER)
    assert [a.served_from for a in store.attempts(run.run_id)] == [SERVED_FAKE, SERVED_PROVIDER]

    with pytest.raises(ValueError):
        store.record_attempt(run_id=run.run_id, step=3, step_key="gap", attempt=1,
                             status=OK, started_at=T0, served_from="probably-real")


def test_the_served_model_is_recorded_beside_the_requested_one(store):
    """observability.md §8.2: a provider that echoes a different model must be caught."""
    run = store.create_run()
    store.record_attempt(
        run_id=run.run_id, step=1, step_key="profile", attempt=1, status=OK, started_at=T0,
        meta=make_meta(models_served=["claude-haiku-4-5-20251001"]),
    )
    record = store.attempts(run.run_id)[0]
    assert record.model_requested == "claude-haiku-4-5"
    assert record.model_served == "claude-haiku-4-5-20251001"


def test_the_hashes_are_computed_in_python_not_over_the_json_column(store):
    """jsonb reorders keys and normalises numbers — a recomputed hash would not match."""
    run = store.create_run()
    output = {"b": 1, "a": [1.0, 2]}
    store.record_attempt(run_id=run.run_id, step=1, step_key="profile", attempt=1,
                         status=OK, started_at=T0, meta=make_meta(), output=output)
    record = store.attempts(run.run_id)[0]
    assert record.output_sha256 == sha256_of(output)
    assert record.output_sha256 == sha256_of({"a": [1.0, 2], "b": 1})  # key order is not a fact
    assert record.input_sha256 == "def456"  # promoted out of `meta` (FR-I10)


def test_an_attempt_with_no_output_has_no_output_hash(store):
    run = store.create_run()
    store.record_attempt(run_id=run.run_id, step=1, step_key="profile", attempt=1,
                         status=FAILED_ATTEMPT, started_at=T0, error_kind="transport")
    assert store.attempts(run.run_id)[0].output_sha256 is None


# --- \x00 ----------------------------------------------------------------
def test_a_nul_byte_never_reaches_the_database(store):
    """psycopg raises DataError on a NUL in text, and the audit row dies with it.

    Caliber strips NULs on every input model; text out of a PDF is how they
    arrive. Stripped on BOTH backends, or the two would disagree about what was
    stored.
    """
    run = store.create_run()
    store.record_attempt(
        run_id=run.run_id, step=1, step_key="pro\x00file", attempt=1,
        status=FAILED_ATTEMPT, started_at=T0, error_kind="sch\x00ema",
        problems=["quote not \x00 found"],
        output={"su\x00mmary": "built a \x00 thing", "list": ["a\x00b"]},
    )
    record = store.attempts(run.run_id)[0]
    assert record.step_key == "profile"
    assert record.error_kind == "schema"
    assert record.problems == ["quote not  found"]
    assert record.output == {"summary": "built a  thing", "list": ["ab"]}
    assert "\x00" not in str(dict(store.db.execute("SELECT * FROM step_runs").fetchone()))


def test_a_nul_byte_is_stripped_from_a_decision_and_an_input(store):
    run = store.create_run()
    store.decide(run.run_id, "confirm_profile", {"note": "fi\x00ne"})
    store.save_input(run.run_id, "resume_text", "Ravi \x00 Kumar")
    assert store.decision(run.run_id, "confirm_profile") == {"note": "fine"}
    assert store.inputs(run.run_id)["resume_text"].payload == "Ravi  Kumar"


# --- run inputs (FR-I8) --------------------------------------------------
def test_a_runs_own_inputs_are_saved_and_read_back(store):
    """Step [1]'s input is nobody's output; without this table a resume cannot find it."""
    run = store.create_run()
    store.save_input(run.run_id, "resume_text", "Ravi Kumar — AI engineer")
    store.save_input(run.run_id, "answers", [{"key": "role:r1:title", "answer": "Engineer"}])

    saved = store.inputs(run.run_id)
    assert set(saved) == {"resume_text", "answers"}
    assert saved["resume_text"].payload == "Ravi Kumar — AI engineer"
    assert saved["answers"].payload == [{"key": "role:r1:title", "answer": "Engineer"}]
    assert saved["resume_text"].payload_sha256 == sha256_of("Ravi Kumar — AI engineer")


def test_saving_an_input_twice_keeps_the_latest_and_does_not_erase_the_first(store):
    """Append-only: the answers a re-run was given do not overwrite the earlier round."""
    run = store.create_run()
    store.save_input(run.run_id, "answers", ["first"])
    store.save_input(run.run_id, "answers", ["first", "second"])
    assert store.inputs(run.run_id)["answers"].payload == ["first", "second"]
    rows = store.db.execute("SELECT * FROM run_inputs").fetchall()
    assert len(rows) == 2


def test_an_unsaved_input_is_a_key_error(store):
    run = store.create_run()
    assert store.inputs(run.run_id) == {}
    with pytest.raises(KeyError):
        store.input(run.run_id, "resume_text")


# --- checkpoints ---------------------------------------------------------
def test_a_checkpoint_is_undecided_until_it_is_answered(store):
    run = store.create_run()
    assert not store.decided(run.run_id, "confirm_profile")
    store.decide(run.run_id, "confirm_profile", {"confirmed": True})
    assert store.decided(run.run_id, "confirm_profile")
    assert store.decision(run.run_id, "confirm_profile") == {"confirmed": True}


def test_reading_an_undecided_checkpoint_raises(store):
    run = store.create_run()
    with pytest.raises(KeyError):
        store.decision(run.run_id, "confirm_profile")


def test_a_decision_can_be_re_armed_for_a_repeating_step(store):
    run = store.create_run()
    store.decide(run.run_id, "answers_needed", [{"key": "role:r1:title", "answer": "Engineer"}])
    store.clear_decision(run.run_id, "answers_needed")
    assert not store.decided(run.run_id, "answers_needed")


def test_deciding_twice_keeps_the_latest_answer(store):
    """`INSERT OR REPLACE` on SQLite, `ON CONFLICT ... DO UPDATE` on Postgres."""
    run = store.create_run()
    store.decide(run.run_id, "confirm_profile", {"confirmed": False})
    store.decide(run.run_id, "confirm_profile", {"confirmed": True})
    assert store.decision(run.run_id, "confirm_profile") == {"confirmed": True}
    rows = store.db.execute("SELECT * FROM checkpoints").fetchall()
    assert len(rows) == 1


# --- referential integrity ----------------------------------------------
def test_an_attempt_cannot_belong_to_a_run_that_does_not_exist(store):
    """Enforced on Postgres always, on SQLite only because we set the PRAGMA."""
    with pytest.raises(Exception):
        store.record_attempt(run_id="ghost", step=1, step_key="profile", attempt=1,
                             status=OK, started_at=T0)


# --- on disk -------------------------------------------------------------
def test_a_run_survives_the_process(store_factory):
    """FR-I8: resuming reads the database, it does not re-call anything."""
    store = store_factory()
    run = store.create_run("run-1")
    store.record_attempt(run_id=run.run_id, step=1, step_key="profile", attempt=1,
                         status=OK, started_at=T0, output={"roles": [{"role_id": "r1"}]})
    store.save_input(run.run_id, "resume_text", "Ravi Kumar — AI engineer")
    store.set_status(run.run_id, DONE)
    store.close()

    reopened = store_factory()
    assert reopened.get_run("run-1").status == DONE
    assert reopened.completed("run-1")[1].output == {"roles": [{"role_id": "r1"}]}
    assert reopened.inputs("run-1")["resume_text"].payload == "Ravi Kumar — AI engineer"


def test_open_store_still_takes_a_path(tmp_path):
    """`step3_demo.py` calls `open_store(DB)` with a Path; that must keep working."""
    path = tmp_path / "caliber.db"
    with open_store(path) as store:
        assert isinstance(store, SqliteStore)
        store.create_run("run-1")
    with open_store(str(path)) as reopened:
        assert reopened.get_run("run-1").status == RUNNING
