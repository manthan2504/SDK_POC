"""Where a run lives between steps (RULEBOOK §4 rules 4, 6 and 9; FR-I8, FR-I10).

Four tables, because a run, an attempt, a pause and an input are different facts:

    runs        one row per pipeline run — where it got to, what it is waiting for
    step_runs   one row per ATTEMPT at a step, including the ones that failed
    checkpoints the candidate's answer at an app pause (FR-I11)
    run_inputs  the run's OWN inputs (resume text, answers) — what FR-I8's
                "any step can be re-run on its own from saved inputs" needs and
                what `step_runs.output` alone cannot give: step [1]'s input is
                nobody's output.

Keeping failed attempts is the point. "Step 1 succeeded" and "step 1 succeeded
on the third try after two schema failures" cost different money and mean
different things about the prompt, and only the second is worth acting on.

The step's own output is stored as JSON next to the audit facts, so a run can
resume from the last completed step without re-calling any agent (FR-I8), and
so any step can be re-run alone against exactly the input it had.

Not stored: prompts, resume text, or anything the candidate wrote. §11 keeps the
audit record to hashes, versions and counts.

TWO BACKENDS, ONE VOCABULARY
----------------------------
`SqliteStore` and `PostgresStore` implement the same ~19 methods and return the
same dataclasses. PostgreSQL is the system of record; SQLite is what lets the
590 offline tests run on a machine with no database service — the same
arrangement the real Caliber repo uses for its own ~790 tests.

`Store` is the shared base: every method body lives here exactly once, and the
subclasses supply only the five places the dialects genuinely differ (parameter
style, JSON, timestamps, numerics, upsert/identity syntax). That is deliberate:
the conformance suite in `tests/test_pipeline_store.py` runs the *same* tests
against both, so a divergence has to be a divergence in SQL, never in logic.

Pick a backend by URL, never by a flag: `postgresql://...` → PostgresStore,
anything else → SQLite. `app/config.py` owns the URL (`POC_DATABASE_URL`).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

from app.agents.base import CallMeta
from app.config import POC_DATABASE_URL, RUNS_DIR

# psycopg is optional at import time: a machine that only ever runs the offline
# suite must not need the driver installed to import this module.
try:  # pragma: no cover - exercised by whichever half of the `if` is true
    import psycopg
    from psycopg.rows import dict_row as _dict_row
    from psycopg.types.json import Jsonb as _Jsonb
except ModuleNotFoundError:  # pragma: no cover
    psycopg = None  # type: ignore[assignment]
    _dict_row = None  # type: ignore[assignment]
    _Jsonb = None  # type: ignore[assignment]

DEFAULT_DB = RUNS_DIR / "caliber.db"

# ---------------------------------------------------------------------------
# Vocabularies — plain `text` columns, validated here, never a PG enum
# ---------------------------------------------------------------------------
# No native enum and no CHECK constraint, for the reason Caliber states on
# `UserEntitlement.feature`: "an ALTER TYPE per addition buys nothing when the
# application validates the value on the way in anyway". Ours moves — `salvaged`
# joined the attempt statuses on 2026-09-21 (§16.2) — and `subtype`,
# `error_kind` and `salvaged_from` carry values the SDK invents, so a constraint
# there would turn an SDK upgrade into a failed insert, losing the audit row for
# a failed step: exactly the row RULEBOOK §4 rule 6 most wants kept.

# A run is in exactly one of these states.
RUNNING = "running"  # a step is in flight
WAITING = "waiting"  # paused at a checkpoint, needs the candidate (FR-I11)
DONE = "done"
FAILED = "failed"
RUN_STATUSES = frozenset({RUNNING, WAITING, DONE, FAILED})

# An attempt ended in exactly one of these — or is still RUNNING (rule 9).
OK = "ok"
SALVAGED = "salvaged"  # output kept from a run the SDK stopped at a ceiling (§16.2)
FAILED_ATTEMPT = "failed"
ATTEMPT_STATUSES = frozenset({RUNNING, OK, SALVAGED, FAILED_ATTEMPT})

# Where the answer came from. Caliber's `agent_call.served_from`, and their S0
# gate asserts on it "so a fixture reply cannot be mistaken for a billed call".
# We have 590 offline tests driven by fake `query` functions, so we have the
# same hazard and want the same column.
SERVED_PROVIDER = "provider"
SERVED_FAKE = "fake"
SERVED_CACHE = "cache"
SERVED_FROM_VALUES = frozenset({SERVED_PROVIDER, SERVED_FAKE, SERVED_CACHE})

# ---------------------------------------------------------------------------
# Database-level settings the POSTGRES database needs — NOT executed here
# ---------------------------------------------------------------------------
# The Windows installer on this box takes the server's timezone and datestyle
# from the machine locale (Asia/Calcutta, `iso, dmy`). Every timestamp column
# below is `timestamptz` and every audit row correlates against logs, so the
# database must speak UTC and ISO. These are DDL for the database OWNER to run
# once, at creation time — the store never issues them (it may not even have the
# right; and `ALTER DATABASE` cannot run inside a transaction block).
#
#     psql -d caliber_poc -c "ALTER DATABASE caliber_poc SET timezone = 'UTC';"
#     psql -d caliber_poc -c "ALTER DATABASE caliber_poc SET datestyle = 'ISO, YMD';"
#
# `_ts_out()` converts to UTC before formatting, so the store reads back the
# same ISO string whatever the server's timezone happens to be. These settings
# are for everyone else who opens a psql prompt.
PG_DATABASE_SETTINGS = (
    "ALTER DATABASE caliber_poc SET timezone = 'UTC';",
    "ALTER DATABASE caliber_poc SET datestyle = 'ISO, YMD';",
)

# Columns whose value is a JSON document / an ISO timestamp. The base class
# routes every bind and every read through these two sets, so a column cannot be
# handled one way on SQLite and another on Postgres.
_JSON_COLUMNS = frozenset({"problems", "meta", "output", "payload"})
_TS_COLUMNS = frozenset({"created_at", "updated_at", "started_at", "finished_at",
                         "decided_at", "saved_at"})

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    status        TEXT NOT NULL,
    current_step  INTEGER,
    waiting_for   TEXT,
    failed_reason TEXT
);

CREATE TABLE IF NOT EXISTS step_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    step            INTEGER NOT NULL,
    step_key        TEXT NOT NULL,
    attempt         INTEGER NOT NULL,
    status          TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    agent           TEXT,
    prompt_version  TEXT,
    prompt_sha256   TEXT,
    model_requested TEXT,
    model_served    TEXT,
    served_from     TEXT,
    cw              TEXT,
    subtype         TEXT,
    salvaged_from   TEXT,
    session_id      TEXT,
    latency_ms      INTEGER,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    total_cost_usd  REAL,
    error_kind      TEXT,
    input_sha256    TEXT,
    output_sha256   TEXT,
    problems        TEXT,
    meta            TEXT,
    output          TEXT,
    UNIQUE (run_id, step, attempt)
);

CREATE TABLE IF NOT EXISTS checkpoints (
    run_id     TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    key        TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    payload    TEXT,
    PRIMARY KEY (run_id, key)
);

CREATE TABLE IF NOT EXISTS run_inputs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    key            TEXT NOT NULL,
    payload        TEXT,
    payload_sha256 TEXT,
    saved_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_step_runs_run_step_attempt ON step_runs (run_id, step, attempt);
CREATE INDEX IF NOT EXISTS ix_step_runs_cw ON step_runs (cw);
CREATE INDEX IF NOT EXISTS ix_runs_created_at ON runs (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_run_inputs_run_key ON run_inputs (run_id, key, id);
"""

# The same four tables in PostgreSQL's own types. Differences from the SQLite
# DDL above, each one deliberate (and each one named in the report):
#   * timestamptz, not TEXT           — real ordering and real interval maths
#   * jsonb, not TEXT                 — rejected at insert, queryable in the demo
#   * numeric(12,6), not REAL         — $0.1107 against a $0.10 ceiling (§16.2)
#   * bigint IDENTITY, not AUTOINCREMENT
#   * run_id stays TEXT, not uuid     — tests pass literal handles ("older")
POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id        text PRIMARY KEY,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    status        text NOT NULL,
    current_step  integer,
    waiting_for   text,
    failed_reason text
);

CREATE TABLE IF NOT EXISTS step_runs (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id          text NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    step            integer NOT NULL,
    step_key        text NOT NULL,
    attempt         integer NOT NULL,
    status          text NOT NULL,
    started_at      timestamptz NOT NULL,
    finished_at     timestamptz,
    agent           text,
    prompt_version  text,
    prompt_sha256   text,
    model_requested text,
    model_served    text,
    served_from     text,
    cw              text,
    subtype         text,
    salvaged_from   text,
    session_id      text,
    latency_ms      integer,
    input_tokens    integer,
    output_tokens   integer,
    total_cost_usd  numeric(12,6),
    error_kind      text,
    input_sha256    text,
    output_sha256   text,
    problems        jsonb,
    meta            jsonb,
    output          jsonb,
    CONSTRAINT uq_step_runs_run_step_attempt UNIQUE (run_id, step, attempt)
);

CREATE TABLE IF NOT EXISTS checkpoints (
    run_id     text NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    key        text NOT NULL,
    decided_at timestamptz NOT NULL,
    payload    jsonb,
    PRIMARY KEY (run_id, key)
);

CREATE TABLE IF NOT EXISTS run_inputs (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id         text NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    key            text NOT NULL,
    payload        jsonb,
    payload_sha256 text,
    saved_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_step_runs_run_step_attempt ON step_runs (run_id, step, attempt);
CREATE INDEX IF NOT EXISTS ix_step_runs_cw ON step_runs (cw);
CREATE INDEX IF NOT EXISTS ix_runs_created_at ON runs (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_run_inputs_run_key ON run_inputs (run_id, key, id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def strip_nuls(value: Any) -> Any:
    """Remove `\\x00` from every string, at any depth.

    PostgreSQL text and jsonb cannot store a NUL byte: psycopg raises
    `DataError` and the transaction is lost — which would take the audit row for
    a failed step with it. Caliber strips NULs on every input model
    (`api/tests/test_nul_byte_guard.py`: "It reaches us the ordinary way: text
    copied out of a PDF. So it is stripped, not refused.").

    SQLite stores NULs happily, so this runs on BOTH backends: a value must not
    survive one store and vanish from the other.
    """
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, dict):
        return {strip_nuls(k): strip_nuls(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [strip_nuls(v) for v in value]
    return value


def _dumps(value: Any) -> str:
    """One JSON encoder for both backends, so neither is stricter than the other.

    `default=str` is what the SQLite store has always done; Postgres gets the
    same, or a datetime inside a step's output would store on one backend and
    raise on the other.
    """
    return json.dumps(value, default=str)


def sha256_of(value: Any) -> str:
    """Hash a JSON-able value over its canonical serialisation, in Python.

    Never `sha256(col::text)`: jsonb does not preserve key order, drops
    duplicate keys and normalises numbers, so a hash recomputed from the column
    would not match the one computed here — and the two backends would disagree.
    """
    blob = json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    created_at: str
    updated_at: str
    status: str
    current_step: int | None
    waiting_for: str | None
    failed_reason: str | None


@dataclass(frozen=True)
class StepRecord:
    """One attempt at one step. `output` is already decoded from JSON.

    `finished_at` is None exactly while the attempt is in flight (status
    `running`): the row is written BEFORE the agent call and updated after
    (RULEBOOK §4 rule 9).
    """

    run_id: str
    step: int
    step_key: str
    attempt: int
    status: str
    started_at: str
    finished_at: str | None
    agent: str | None
    model_requested: str | None
    model_served: str | None
    served_from: str | None
    subtype: str | None
    salvaged_from: str | None
    total_cost_usd: float | None
    error_kind: str | None
    input_sha256: str | None
    output_sha256: str | None
    problems: list[str]
    output: Any

    @property
    def succeeded(self) -> bool:
        """Salvaged counts as succeeded: the output is validated and already paid for."""
        return self.status in (OK, SALVAGED)


@dataclass(frozen=True)
class InputRecord:
    """One saved input to a run — the half FR-I8 was missing."""

    run_id: str
    key: str
    payload: Any
    payload_sha256: str | None
    saved_at: str


# ---------------------------------------------------------------------------
# The shared vocabulary
# ---------------------------------------------------------------------------
class Store(ABC):
    """The run store's vocabulary. One connection, plain SQL, no ORM.

    Every method body is here once. A subclass supplies only what the dialects
    disagree about: the parameter marker, JSON in/out, timestamp in/out, the
    numeric cast, the DDL, and two statements that have no common spelling
    (identity insert, upsert).
    """

    placeholder = "?"
    schema: str = ""

    def __init__(self, connection: Any) -> None:
        self.db = connection
        self._prepare()
        self._create_schema()

    # -- dialect hooks -----------------------------------------------------
    def _prepare(self) -> None:
        """Connection-level settings, before any DDL."""

    @abstractmethod
    def _create_schema(self) -> None: ...

    @abstractmethod
    def _json_in(self, value: Any) -> Any: ...

    @abstractmethod
    def _json_out(self, value: Any) -> Any: ...

    @abstractmethod
    def _ts_in(self, value: Any) -> Any: ...

    @abstractmethod
    def _ts_out(self, value: Any) -> Any: ...

    @abstractmethod
    def _insert_returning_id(self, sql: str, params: Sequence[Any]) -> int: ...

    @abstractmethod
    def _upsert_checkpoint_sql(self) -> str: ...

    def _num_out(self, value: Any) -> float | None:
        """Postgres `numeric` arrives as Decimal; the dataclass promises float."""
        return None if value is None else float(value)

    # -- plumbing ----------------------------------------------------------
    def _q(self, sql: str) -> str:
        """Every statement is written with `?`; Postgres wants `%s`."""
        return sql if self.placeholder == "?" else sql.replace("?", self.placeholder)

    def _bind(self, column: str, value: Any) -> Any:
        """One place decides how a column's value reaches the driver."""
        value = strip_nuls(value)
        if column in _JSON_COLUMNS:
            return self._json_in(value)
        if column in _TS_COLUMNS:
            return self._ts_in(value)
        return value

    def _read(self, column: str, value: Any) -> Any:
        if column in _JSON_COLUMNS:
            return self._json_out(value)
        if column in _TS_COLUMNS:
            return self._ts_out(value)
        return value

    def _execute(self, sql: str, params: Sequence[Any] = ()) -> Any:
        return self.db.execute(self._q(sql), list(params))

    def _insert(self, table: str, values: dict[str, Any]) -> None:
        columns = list(values)
        marks = ", ".join(["?"] * len(columns))
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({marks})"
        self._execute(sql, [self._bind(c, values[c]) for c in columns])
        self.db.commit()

    def _insert_id(self, table: str, values: dict[str, Any]) -> int:
        columns = list(values)
        marks = ", ".join([self.placeholder] * len(columns))
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({marks})"
        row_id = self._insert_returning_id(sql, [self._bind(c, values[c]) for c in columns])
        self.db.commit()
        return row_id

    def _update(self, table: str, values: dict[str, Any], where: str, args: Sequence[Any]) -> None:
        sets = ", ".join(f"{c} = ?" for c in values)
        params = [self._bind(c, values[c]) for c in values] + list(args)
        self._execute(f"UPDATE {table} SET {sets} WHERE {where}", params)
        self.db.commit()

    # -- lifecycle ---------------------------------------------------------
    @classmethod
    def open(cls, path: str | Path = DEFAULT_DB) -> "Store":
        """A SQLite file. Unchanged from the day this store had one backend."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return SqliteStore(sqlite3.connect(path))

    @classmethod
    def in_memory(cls) -> "Store":
        """The 590 offline tests' backend. Needs no service and no credential."""
        return SqliteStore(sqlite3.connect(":memory:"))

    @classmethod
    def from_url(cls, url: str | None = None) -> "Store":
        """Selection happens by URL, in one place, exactly like Caliber's env.py.

        `postgresql://...` (or `postgres://`, or SQLAlchemy's
        `postgresql+psycopg://`) → PostgresStore. Anything else is SQLite: a
        `sqlite:///path` URL, or a bare path.
        """
        url = url or POC_DATABASE_URL
        head = url.split("://", 1)[0].split("+", 1)[0].lower()
        if head in ("postgresql", "postgres"):
            return PostgresStore.connect(url)
        if url.startswith("sqlite:"):
            tail = url[len("sqlite:"):]
            # sqlite:///C:\path (Windows) · sqlite:////abs/path (POSIX) ·
            # sqlite:// and sqlite:///:memory: both mean in-memory.
            for prefix in ("///", "//"):
                if tail.startswith(prefix):
                    tail = tail[len(prefix):]
                    break
            if tail in ("", ":memory:"):
                return cls.in_memory()
            return cls.open(tail)
        return cls.open(url)

    def close(self) -> None:
        self.db.close()

    # -- runs --------------------------------------------------------------
    def create_run(self, run_id: str | None = None) -> RunRecord:
        run_id = run_id or uuid.uuid4().hex
        now = _now()
        self._insert("runs", {
            "run_id": run_id, "created_at": now, "updated_at": now, "status": RUNNING,
        })
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> RunRecord:
        row = self._execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(f"no such run: {run_id}")
        return self._to_run_record(row)

    def list_runs(self) -> list[RunRecord]:
        rows = self._execute("SELECT * FROM runs ORDER BY created_at DESC").fetchall()
        return [self._to_run_record(r) for r in rows]

    def set_status(
        self,
        run_id: str,
        status: str,
        *,
        current_step: int | None = None,
        waiting_for: str | None = None,
        failed_reason: str | None = None,
    ) -> None:
        _check(status, RUN_STATUSES, "run status")
        self._update("runs", {
            "status": status, "updated_at": _now(), "current_step": current_step,
            "waiting_for": waiting_for, "failed_reason": failed_reason,
        }, "run_id = ?", (run_id,))

    # -- attempts ----------------------------------------------------------
    def next_attempt(self, run_id: str, step: int) -> int:
        row = self._execute(
            "SELECT MAX(attempt) AS n FROM step_runs WHERE run_id = ? AND step = ?",
            (run_id, step),
        ).fetchone()
        return (row["n"] or 0) + 1

    def start_attempt(
        self,
        *,
        run_id: str,
        step: int,
        step_key: str,
        attempt: int,
        started_at: str,
        meta: CallMeta | None = None,
        served_from: str | None = None,
    ) -> int:
        """Write the `running` row BEFORE the agent call. Returns its row id.

        RULEBOOK §4 rule 9, and Caliber wrote that rule after a rolled-back
        request took the trace row with it: a step that dies mid-call is
        recorded, never lost. The pre-call facts (agent, prompt version and
        hash, model requested, cw, input hash) are all known already; the
        outcome facts arrive in `finish_attempt`.
        """
        if served_from is not None:
            _check(served_from, SERVED_FROM_VALUES, "served_from")
        m = asdict(meta) if meta else {}
        return self._insert_id("step_runs", {
            "run_id": run_id, "step": step, "step_key": step_key, "attempt": attempt,
            "status": RUNNING, "started_at": started_at, "finished_at": None,
            "served_from": served_from,
            **_pre_call_columns(m),
        })

    def finish_attempt(
        self,
        attempt_id: int,
        *,
        status: str,
        meta: CallMeta | None = None,
        output: Any = None,
        error_kind: str | None = None,
        problems: list[str] | None = None,
        served_from: str | None = None,
        finished_at: str | None = None,
    ) -> StepRecord:
        """Close the row `start_attempt()` opened, in its OWN transaction.

        Two transactions, not one: the point of rule 9 is that the record of a
        call does not depend on the caller's transaction surviving.
        """
        _check(status, ATTEMPT_STATUSES, "attempt status")
        if served_from is not None:
            _check(served_from, SERVED_FROM_VALUES, "served_from")
        m = asdict(meta) if meta else {}
        values: dict[str, Any] = {
            "status": status,
            "finished_at": finished_at or _now(),
            "error_kind": error_kind,
            "problems": problems or None,
            "output": output,
            "output_sha256": None if output is None else sha256_of(strip_nuls(output)),
            "meta": m or None,
        }
        if served_from is not None:
            values["served_from"] = served_from
        if m:
            values.update(_pre_call_columns(m))
            values.update({
                "model_served": (m.get("models_served") or [None])[0],
                "subtype": m.get("subtype"),
                "salvaged_from": m.get("salvaged_from"),
                "session_id": m.get("session_id"),
                "latency_ms": m.get("latency_ms"),
                "input_tokens": m.get("input_tokens"),
                "output_tokens": m.get("output_tokens"),
                "total_cost_usd": m.get("total_cost_usd"),
            })
        self._update("step_runs", values, "id = ?", (attempt_id,))
        row = self._execute("SELECT * FROM step_runs WHERE id = ?", (attempt_id,)).fetchone()
        if row is None:
            raise KeyError(f"no such attempt: {attempt_id}")
        return self._to_step_record(row)

    def record_attempt(
        self,
        *,
        run_id: str,
        step: int,
        step_key: str,
        attempt: int,
        status: str,
        started_at: str,
        meta: CallMeta | None = None,
        output: Any = None,
        error_kind: str | None = None,
        problems: list[str] | None = None,
        served_from: str | None = None,
    ) -> StepRecord:
        """Write one finished attempt. Called for failures too — that is the point.

        A thin wrapper over `start_attempt()` + `finish_attempt()`, so the two
        paths cannot drift. The runner still calls this; it may move to the
        split pair whenever it wants the `running` row to be visible during the
        call rather than after it.
        """
        attempt_id = self.start_attempt(
            run_id=run_id, step=step, step_key=step_key, attempt=attempt,
            started_at=started_at, meta=meta,
        )
        return self.finish_attempt(
            attempt_id, status=status, meta=meta, output=output,
            error_kind=error_kind, problems=problems, served_from=served_from,
        )

    def attempts(self, run_id: str, step: int | None = None) -> list[StepRecord]:
        sql = "SELECT * FROM step_runs WHERE run_id = ?"
        args: list[Any] = [run_id]
        if step is not None:
            sql += " AND step = ?"
            args.append(step)
        sql += " ORDER BY step, attempt"
        return [self._to_step_record(r) for r in self._execute(sql, args).fetchall()]

    def completed(self, run_id: str) -> dict[int, StepRecord]:
        """The latest successful attempt per step — what a resume starts from."""
        done: dict[int, StepRecord] = {}
        for record in self.attempts(run_id):
            if record.succeeded:
                done[record.step] = record
        return done

    def cost(self, run_id: str) -> float:
        """Everything this run has spent, failed attempts included."""
        row = self._execute(
            "SELECT COALESCE(SUM(total_cost_usd), 0) AS total FROM step_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        return float(row["total"])

    # -- run inputs (FR-I8: "re-run on its own from saved inputs") ----------
    def save_input(self, run_id: str, key: str, payload: Any = None) -> InputRecord:
        """Save one of the run's OWN inputs (`resume_text`, `answers`, `jd_text`).

        Append-only: a second save under the same key is a new row, so the
        answers a re-run was given do not erase the ones before them. `inputs()`
        reads the latest per key.
        """
        saved_at = _now()
        self._insert("run_inputs", {
            "run_id": run_id, "key": key, "payload": payload,
            "payload_sha256": None if payload is None else sha256_of(strip_nuls(payload)),
            "saved_at": saved_at,
        })
        return self.input(run_id, key)

    def inputs(self, run_id: str) -> dict[str, InputRecord]:
        """The latest saved value of every input key for this run."""
        rows = self._execute(
            "SELECT * FROM run_inputs WHERE run_id = ? ORDER BY id", (run_id,)
        ).fetchall()
        latest: dict[str, InputRecord] = {}
        for row in rows:
            record = self._to_input_record(row)
            latest[record.key] = record
        return latest

    def input(self, run_id: str, key: str) -> InputRecord:
        record = self.inputs(run_id).get(key)
        if record is None:
            raise KeyError(f"no such input: {key}")
        return record

    # -- checkpoints (FR-I11) ---------------------------------------------
    def decide(self, run_id: str, key: str, payload: Any = None) -> None:
        """Record the candidate's answer at a checkpoint."""
        sql = self._upsert_checkpoint_sql()
        params = [
            self._bind("run_id", run_id), self._bind("key", key),
            self._bind("decided_at", _now()), self._bind("payload", payload),
        ]
        self._execute(sql, params)
        self.db.commit()

    def decided(self, run_id: str, key: str) -> bool:
        row = self._execute(
            "SELECT 1 AS hit FROM checkpoints WHERE run_id = ? AND key = ?", (run_id, key)
        ).fetchone()
        return row is not None

    def decision(self, run_id: str, key: str) -> Any:
        row = self._execute(
            "SELECT payload FROM checkpoints WHERE run_id = ? AND key = ?", (run_id, key)
        ).fetchone()
        if row is None:
            raise KeyError(f"checkpoint not decided: {key}")
        return self._json_out(row["payload"])

    def clear_decision(self, run_id: str, key: str) -> None:
        """Re-arm a checkpoint, so a repeating step pauses again next time round."""
        self._execute("DELETE FROM checkpoints WHERE run_id = ? AND key = ?", (run_id, key))
        self.db.commit()

    # -- row -> dataclass --------------------------------------------------
    def _to_run_record(self, row: Any) -> RunRecord:
        return RunRecord(
            run_id=row["run_id"],
            created_at=self._ts_out(row["created_at"]),
            updated_at=self._ts_out(row["updated_at"]),
            status=row["status"],
            current_step=row["current_step"],
            waiting_for=row["waiting_for"],
            failed_reason=row["failed_reason"],
        )

    def _to_step_record(self, row: Any) -> StepRecord:
        return StepRecord(
            run_id=row["run_id"],
            step=row["step"],
            step_key=row["step_key"],
            attempt=row["attempt"],
            status=row["status"],
            started_at=self._ts_out(row["started_at"]),
            finished_at=self._ts_out(row["finished_at"]),
            agent=row["agent"],
            model_requested=row["model_requested"],
            model_served=row["model_served"],
            served_from=row["served_from"],
            subtype=row["subtype"],
            salvaged_from=row["salvaged_from"],
            total_cost_usd=self._num_out(row["total_cost_usd"]),
            error_kind=row["error_kind"],
            input_sha256=row["input_sha256"],
            output_sha256=row["output_sha256"],
            problems=self._json_out(row["problems"]) or [],
            output=self._json_out(row["output"]),
        )

    def _to_input_record(self, row: Any) -> InputRecord:
        return InputRecord(
            run_id=row["run_id"],
            key=row["key"],
            payload=self._json_out(row["payload"]),
            payload_sha256=row["payload_sha256"],
            saved_at=self._ts_out(row["saved_at"]),
        )


def _check(value: str, allowed: frozenset[str], what: str) -> None:
    """Vocabulary validation lives here, because the column has no constraint."""
    if value not in allowed:
        raise ValueError(f"unknown {what}: {value!r} (expected one of {sorted(allowed)})")


def _pre_call_columns(m: dict[str, Any]) -> dict[str, Any]:
    """The audit facts that are known before the model is called."""
    return {
        "agent": m.get("agent"),
        "prompt_version": m.get("prompt_version"),
        "prompt_sha256": m.get("prompt_sha256"),
        "model_requested": m.get("model_requested"),
        "cw": m.get("cw"),
        "input_sha256": m.get("input_sha256"),
    }


# ---------------------------------------------------------------------------
# SQLite — the offline backend
# ---------------------------------------------------------------------------
class SqliteStore(Store):
    """Tests and offline demos. JSON is TEXT, timestamps are ISO strings.

    Kept because the 590-test suite must run on a machine with no service:
    Caliber, which SHIPS PostgreSQL, runs its whole ~790-test suite this way.
    """

    placeholder = "?"
    schema = SQLITE_SCHEMA

    def _prepare(self) -> None:
        self.db.row_factory = sqlite3.Row
        # SQLite ignores foreign keys unless asked, per connection. Postgres
        # always enforces them, so without this an orphan step_run could be
        # written in a test and pass, then fail against the system of record —
        # and the conformance suite would not be a conformance suite.
        self.db.execute("PRAGMA foreign_keys = ON")

    def _create_schema(self) -> None:
        self.db.executescript(self.schema)
        self.db.commit()

    def _json_in(self, value: Any) -> Any:
        return None if value is None else _dumps(value)

    def _json_out(self, value: Any) -> Any:
        return json.loads(value) if value else None

    def _ts_in(self, value: Any) -> Any:
        return value.isoformat(timespec="seconds") if isinstance(value, datetime) else value

    def _ts_out(self, value: Any) -> Any:
        return value

    def _insert_returning_id(self, sql: str, params: Sequence[Any]) -> int:
        return int(self.db.execute(sql, list(params)).lastrowid)

    def _upsert_checkpoint_sql(self) -> str:
        return ("INSERT OR REPLACE INTO checkpoints (run_id, key, decided_at, payload) "
                "VALUES (?,?,?,?)")


# ---------------------------------------------------------------------------
# PostgreSQL — the system of record
# ---------------------------------------------------------------------------
class PostgresStore(Store):
    """psycopg 3, plain SQL, one connection, no ORM and no migration tool.

    NOT VERIFIED AGAINST A LIVE SERVER: written offline, against psycopg 3.3
    and the PostgreSQL 18 documentation. The conformance suite
    (`pytest -m postgres`, needs `POC_TEST_DATABASE_URL`) is what proves it.
    """

    placeholder = "%s"
    schema = POSTGRES_SCHEMA

    @classmethod
    def connect(cls, url: str) -> "PostgresStore":
        if psycopg is None:  # pragma: no cover
            raise RuntimeError(
                "psycopg is not installed; `pip install 'psycopg[binary]>=3.2'` "
                "or point POC_DATABASE_URL at a sqlite:// URL"
            )
        # A SQLAlchemy-style `postgresql+psycopg://` URL is accepted for the
        # convenience of anyone copying a DSN out of the Caliber repo; libpq
        # does not understand the `+driver` part, so it is dropped.
        if "+" in url.split("://", 1)[0]:
            scheme, rest = url.split("://", 1)
            url = f"{scheme.split('+', 1)[0]}://{rest}"
        # Never log this URL: it carries the password. If a connection fails,
        # report dbname@host:port from psycopg.conninfo.conninfo_to_dict().
        return cls(psycopg.connect(url, row_factory=_dict_row))

    def _create_schema(self) -> None:
        # `CREATE TABLE IF NOT EXISTS` at construction, as on SQLite. No
        # Alembic: four tables, one developer, and a database that is
        # reproducible from this constant and disposable.
        #
        # One statement per execute(): psycopg's extended protocol takes a
        # single statement, and relying on the simple-protocol fallback for a
        # multi-statement string is a detail of the driver, not of the schema.
        for statement in (s.strip() for s in self.schema.split(";")):
            if statement:
                self.db.execute(statement)
        self.db.commit()

    def _json_in(self, value: Any) -> Any:
        # Jsonb(None) would write a JSON `null`; we want SQL NULL.
        return None if value is None else _Jsonb(value, dumps=_dumps)

    def _json_out(self, value: Any) -> Any:
        # jsonb comes back already decoded.
        return value

    def _ts_in(self, value: Any) -> Any:
        """timestamptz wants a datetime. The store's callers speak ISO strings.

        Converted here rather than relying on the server to cast an `unknown`
        parameter, so the behaviour does not depend on how psycopg happens to
        type a bare `str` this release.
        """
        if value is None or isinstance(value, datetime):
            return value
        try:
            parsed = datetime.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"timestamp columns need an ISO-8601 string or a datetime, got {value!r}"
            ) from exc
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    def _ts_out(self, value: Any) -> Any:
        """Back to the same ISO-8601 UTC string SQLite returns.

        `.astimezone(utc)` first: psycopg renders a timestamptz in the session's
        timezone, and this box's server defaults to the machine locale until
        someone runs PG_DATABASE_SETTINGS. Converting here means the store reads
        back the same string either way.
        """
        if not isinstance(value, datetime):
            return value
        return value.astimezone(timezone.utc).isoformat(timespec="seconds")

    def _insert_returning_id(self, sql: str, params: Sequence[Any]) -> int:
        row = self.db.execute(sql + " RETURNING id", list(params)).fetchone()
        return int(row["id"])

    def _upsert_checkpoint_sql(self) -> str:
        # `INSERT OR REPLACE` does not exist in PostgreSQL. Same behaviour:
        # the latest answer wins, the row keeps its place.
        return ("INSERT INTO checkpoints (run_id, key, decided_at, payload) "
                "VALUES (%s,%s,%s,%s) "
                "ON CONFLICT (run_id, key) DO UPDATE "
                "SET decided_at = EXCLUDED.decided_at, payload = EXCLUDED.payload")


@contextmanager
def open_store(target: str | Path = DEFAULT_DB) -> Iterator[Store]:
    """Open whichever backend `target` names, and close it afterwards."""
    store = Store.from_url(target) if isinstance(target, str) and "://" in target else Store.open(target)
    try:
        yield store
    finally:
        store.close()
