# PostgreSQL patterns in Caliber — and which ones this POC should copy

> **What this is.** A read of the real product repo's database layer (`D:\Caliber`, read-only),
> written so the POC can move `app/pipeline/store.py` from SQLite to PostgreSQL 18 while copying
> the patterns that pay and skipping the ones that don't.
>
> **Written:** 2026-09-21. **Evidence:** file paths and quoted snippets throughout.
> **No database was connected to, no migration run, no LLM called** while writing this.
> Credentials are referred to by variable name only.
>
> **Organised as:** Part 1 what Caliber does → Part 2 what to copy → Part 3 what to skip →
> Part 4 the two decisions you actually asked for → Part 5 Windows credentials → Part 6 the
> table-by-table conversion.

---

## 0. The two numbers that decide everything below

| | |
|---|---|
| POC tests that construct a `Store` | **42** — `tests/test_pipeline_store.py` (16) + `tests/test_pipeline_runner.py` (26) |
| POC tests that never touch persistence | **548** of 590 |
| Caliber tests that connect to PostgreSQL | **0**. Grep for `pytest.mark.integration` across `api/tests/` matches only the conftest **docstring**. The marker infrastructure exists; not one test uses it. |

Caliber **ships** PostgreSQL and runs its entire ~790-test suite on in-memory SQLite and
attribute-bag fakes. That precedent is the single most useful thing in this document: the
product you are mirroring does not test against its own database either.

---

# Part 1 — What Caliber does

## 1.1 Stack and exact versions

`D:\Caliber\api\pyproject.toml`:

```toml
requires-python = ">=3.12,<3.13"
    # database
    "sqlalchemy>=2.0.36",
    "alembic>=1.14",
    "psycopg[binary]>=3.2",
    "pgvector>=0.3.6",
    # cache / jobs
    "redis>=5.2",
    "arq>=0.26",
    # auth
    "fastapi-users[sqlalchemy]>=14.0",
```

- **SQLAlchemy 2.0, ORM, `DeclarativeBase` + `Mapped[...]` / `mapped_column(...)`** — the modern
  typed style throughout, not the 1.x `Column()` style.
- **psycopg 3** (binary wheel — matters on Windows: no libpq or MSVC build needed). URL scheme is
  `postgresql+psycopg://` (see `api/tests/conftest.py`).
- **Alembic** for migrations.
- **Sync, not async — deliberately.** `api/src/caliber/db.py` opens with the reason:

  > *"Sync SQLAlchemy 2.0 deliberately: the slow paths (grading, resume parse) go to an ARQ worker
  > process rather than being awaited in the request, so async buys little here and costs
  > greenlet/driver complexity on native Windows. Revisit if a genuine in-request fan-out appears."*

- **Tooling:** `uv` (there is an `api/uv.lock`), `ruff`, `mypy --strict` with the pydantic plugin,
  `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`).

### Server versions — and the gap with this box

| | Caliber | This POC's box |
|---|---|---|
| Server | PostgreSQL **17.11**, service `postgresql-x64-17` (`docs/RUNBOOK-db.md`; `ops/db.ps1` hardcodes `C:\Program Files\PostgreSQL\17\bin`) | PostgreSQL **18**, service `postgresql-x64-18` |
| pgvector | **0.8.6**, built from source with MSVC | not installed, **not needed** |

**Does the version gap matter? No.** Every Postgres feature this POC needs — `jsonb`,
`timestamptz`, `numeric`, `ON CONFLICT ... DO UPDATE`, `GENERATED ALWAYS AS IDENTITY`,
`gen_random_uuid()` — has been core since PostgreSQL 13. Nothing in the POC's schema is
17-vs-18 sensitive. The only practical consequences: the bin path is
`C:\Program Files\PostgreSQL\18\bin`, and any script copied from `ops/db.ps1` must have its
`$pgbin` / `$svcName` changed or it will silently look for a 17 that isn't there.

*(PostgreSQL 18 also adds a native `uuidv7()`. Don't rely on it without checking `SELECT uuidv7()`
first — `gen_random_uuid()` is the safe choice and is what Caliber uses.)*

## 1.2 Engine and session — where they live

All of it in one 40-line file, `api/src/caliber/db.py`:

```python
class Base(DeclarativeBase):
    pass

_settings = get_settings()

engine = create_engine(
    str(_settings.database_url),
    pool_pre_ping=True,  # a 10-day Memurai restart or a PG bounce must not wedge the pool
    future=True,
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

Three things worth naming:

1. **The engine is built at module scope**, so importing anything under `caliber` runs
   `get_settings()`, which is fail-fast and raises if there is no `.env`. That one decision
   shapes the whole test arrangement (§1.6).
2. **`create_engine` is lazy** — it opens no connection. That is what makes the offline test
   suite possible at all.
3. **`expire_on_commit=False`** so ORM objects stay readable after the request's commit.

Settings are `pydantic-settings`, `api/src/caliber/core/config.py`, with typed DSNs:

```python
database_url: PostgresDsn
test_database_url: PostgresDsn | None = None
```

and the canonical `.env` is the **repo root** one — *"There is no second .env inside api/."*

## 1.3 Models — naming, keys, cascades, nullability, defaults

Two model modules: `api/src/caliber/models.py` (S0 infrastructure: `agent_call`, `job_run`) and
`api/src/caliber/domain.py` (S1 domain, 11 tables).

**Table names:** `snake_case`, **singular**, no prefix:
`agent_call`, `job_run`, `app_user`, `candidate_profile`, `work_experience`, `project`,
`education`, `skill_claim`, `skill_evidence`, `resume_artifact`, `gap_relevance_rating`,
`user_entitlement`, `upgrade_interest`.
`app_user` rather than `user` because `user` is a reserved word in Postgres.

**Primary keys:** UUID everywhere, no exceptions, no bigserial, no natural keys.

```python
id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

…with the migration *also* carrying a server default:

```python
sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
          server_default=sa.text("gen_random_uuid()")),
```

Both halves on purpose: the Python default means an object has an id before flush; the
`server_default` means a hand-written `INSERT` in psql still gets one.

**Foreign keys:** always three things together — DB-level cascade, an index on the FK column,
and an ORM-level cascade on the relationship.

```python
profile_id: Mapped[uuid.UUID] = mapped_column(
    ForeignKey("candidate_profile.id", ondelete="CASCADE"), nullable=False, index=True
)
...
experiences: Mapped[list[WorkExperience]] = relationship(
    back_populates="profile", cascade="all, delete-orphan",
    order_by="WorkExperience.sort_order"
)
```

Every FK in the repo is `ondelete="CASCADE"`. There is no `SET NULL`, no `RESTRICT`.

**Constraint names are hand-written**, not generated — there is **no**
`MetaData(naming_convention=...)` anywhere in the repo. The convention is by hand:

- unique constraints: `uq_<what>_per_<scope>` — `uq_skill_per_profile`,
  `uq_evidence_per_skill_project`, `uq_relevance_per_user_surface`, `uq_entitlement_per_user_feature`
- indexes: `ix_<table>_<column>` — `ix_agent_call_created_at`, `ix_job_run_status`
- a named partial index: `ix_gap_relevance_real_bar`

```python
__table_args__ = (UniqueConstraint("profile_id", "skill", name="uq_skill_per_profile"),)
```

**Nullability discipline:** NOT NULL on everything derived or required; nullable columns carry a
comment saying *what null means*. This is the house style and it is unusually consistent:

- `end_date: Mapped[date | None] = mapped_column(Date)  # null => current`
- `expires_at` — *"NULL means indefinite."*
- `cw` / `prompt_version` / `prompt_hash` — *"Nullable: rows from before b7e2c4d1a9f3 have neither,
  and null says so honestly."*
- `pending_email` is deliberately **not** unique and **not** indexed, with four lines explaining
  why a unique constraint there would let one abandoned request block another person permanently.

**`server_default` vs Python default — the rule that bites.** Any Python default must be
mirrored by a `server_default` or the drift check never goes clean. Stated twice, in the code:

```python
# `server_default=text("0")` mirrors the migration exactly. Without it
# `db.ps1 drift` reports the column as an un-migrated model change forever.
session_version: Mapped[int] = mapped_column(
    Integer, nullable=False, default=0, server_default=text("0")
)
```

and again on the partial index:

```python
# Mirrors the migration exactly, or `db.ps1 drift` reports the index as
# an un-migrated model change on every run.
Index("ix_gap_relevance_real_bar", "surface", "rating",
      postgresql_where=text("bar_is_placeholder = false")),
```

## 1.4 Types

| Concern | Caliber's choice | Evidence |
|---|---|---|
| **JSON** | **JSONB, always.** `from sqlalchemy.dialects.postgresql import JSONB`, typed `Mapped[dict \| None]` or `Mapped[list \| None]`. Never `JSON`, never json-in-TEXT. | `context`, `payload`, `result`, `confirmed_snapshot`, `dismissed_duplicate_pairs`, `processes`, `stack` |
| **Enums** | **No native PG enum. No CHECK constraint.** A Python `StrEnum` in one module (`api/src/caliber/enums.py`, 9 enums) + a narrow `String(n)` column, validated in the application. | see quote below |
| **Timestamps** | **`DateTime(timezone=True)` = `timestamptz`, always.** `server_default=func.now()`, and `onupdate=func.now()` for `updated_at`. Calendar dates use `Date`. | every model |
| **Money / cost** | **`Float`** → `double precision`. There is **no `Numeric`, no `Decimal` anywhere in the repo.** | `cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)` |
| **Text** | `Text` for unbounded prose (`prompt`, `response`, `error`, `summary`, `impact`, `resume_text`); `String(n)` for bounded labels, width chosen per field: 16 status/outcome/effort/cw, 32 provider/feature, 64 agent/model/sha256, 120 skill, 200/300/400 names, 320 email, 500 storage key, 1000 note, 2000 URL. | throughout |

The enum decision is argued explicitly on `UserEntitlement.feature`:

> *"Stored as text, not a DB enum: the set is expected to grow with the product, and an ALTER TYPE
> per addition buys nothing when the application validates the value on the way in anyway."*

### Two type lessons Caliber paid for

**(a) Narrow varchars + provider-supplied strings = a lost transaction.**
`api/src/caliber/tracing.py` has a `_clip()` helper whose docstring is the whole story:

> *"this write usually runs on the CALLER's session with flush(), so a StringDataRightTruncation
> would deactivate their transaction. […] then the request's own commit would fail with
> PendingRollbackError — turning "the trace could not be written" into "the resume upload 500'd and
> rolled back after telling the candidate their text was saved". A trace row is diagnostic; it may
> lose precision, never a user's work."*

Every externally-sourced string is clipped to its column width before the insert
(`_clip(rec.model, 64)`). SQLite never raised this because SQLite ignores `VARCHAR(n)` lengths.

**(b) PostgreSQL text columns cannot store `\x00`.**
`api/tests/test_nul_byte_guard.py`:

> *"PostgreSQL text columns cannot store `\x00`; psycopg raises `DataError` and the transaction is
> lost. That surfaced as a 500 with a `text/plain` body […] It reaches us the ordinary way: text
> copied out of a PDF. So it is stripped, not refused."*

There is a `strip_nuls` validator on every Pydantic input model, covering strings *and* list
entries. SQLite stores NUL bytes happily, so this is a bug the POC cannot currently have and will
acquire on the day it switches.

## 1.5 Migrations

**Layout:** `api/alembic.ini` (stock, `script_location = %(here)s/alembic`, `prepend_sys_path = .`)
→ `api/alembic/env.py` → `api/alembic/versions/` (11 revisions). File naming after the baseline is
`<hash>_<stage>_<slug>.py`, e.g. `b7e2c4d1a9f3_s1_agent_call_cw_prompt_provenance.py` — the `s1_`
/ `s2_` prefix ties the migration to the delivery stage.

**`env.py` picks the URL from the app's own Settings, not from `alembic.ini`:**

> *"The DB URL comes from the app's own Settings object, not from alembic.ini, so there is exactly
> one place a connection string is defined.
> Target selection: `-x db=dev` (default) or `-x db=test`. Without this the test database can only
> be migrated by hand, which is how schemas silently drift apart — caliber_test must run the same
> migrations as caliber, not a copy."*

```python
_target = (context.get_x_argument(as_dictionary=True).get("db") or "dev").lower()
if _target in ("dev", "caliber"):      _url = str(_settings.database_url)
elif _target in ("test", "caliber_test"):
    if _settings.test_database_url is None:
        raise RuntimeError("TEST_DATABASE_URL is not set in .env; cannot migrate -x db=test")
    _url = str(_settings.test_database_url)
config.set_main_option("sqlalchemy.url", _url)
```

Other `env.py` details worth keeping: `compare_type=True` on both offline and online configure;
`poolclass=pool.NullPool`; models imported for their side effect (`import caliber.models  # noqa: F401`).

**The best gotcha in the whole repo** is in `run_migrations_online`:

```python
# The app role carries statement_timeout / lock_timeout (ops/db-roles.sql).
# A long index build is a legitimate migration and must not inherit a
# request-shaped timeout, so they are cleared for migration connections.
#
# These go through libpq's `options` at CONNECT time, deliberately. Issuing
# them as `connection.execute("SET ...")` instead silently breaks migrations:
# the execute autobegins a transaction, alembic's context.begin_transaction()
# then becomes a no-op, and every migration is rolled back at close while
# alembic still logs "Running upgrade/downgrade" and exits 0.
connect_args={"options": "-c statement_timeout=0 -c lock_timeout=30s"},
```

**Every migration has a real `downgrade()`.** The one exception is documented:

```python
def downgrade() -> None:
    op.drop_table("job_run")
    op.drop_table("agent_call")
    # the vector extension is deliberately NOT dropped: other databases/objects
    # may depend on it and dropping it is not reversible in a useful way.
```

**Extensions are created by the provisioning script, never by a migration** — because
`CREATE EXTENSION` needs superuser and the app role deliberately isn't one.

### How they actually run migrations: `ops\db.ps1`

One 396-line PowerShell entry point, ten subcommands. No make, no just, no nox.

```
verify (default) · provision · harden · migrate · drift · roundtrip
reset-test · backup · restore · psql
```

> *"Exit code is 0 only if every check passed - safe to gate CI on."*

- **`migrate`** — `alembic -x db=dev upgrade head` **and** `-x db=test upgrade head`, then reports
  each database's `alembic_version`.
- **`drift`** — `alembic -x db=<t> check` on **both**. Fails with the fix in the message:
  *"models and migrations disagree - run: uv run alembic -x db=$t revision --autogenerate"*.

- **`roundtrip`** — this is what `AGENT_WORK_DESIGN.md`'s *"migrate/drift/roundtrip clean"* means.
  Not an exit-code check. The comment says why:

  > *"The S0 gate asserts 'alembic upgrade head then downgrade base runs clean'. Exit codes are not
  > enough: the rebuilt schema must equal the one we already run on."*

  The algorithm:
  1. `pg_dump --schema-only --no-owner --no-privileges` of the **dev** database → `$before`
  2. `alembic -x db=test downgrade base`; assert **zero** tables survive besides `alembic_version`
     — *"migrations are not reversible"* if any do
  3. `alembic -x db=test upgrade head`
  4. dump the **test** database → `$after`
  5. `Compare-Object $before $after` must be `$null`

  The dumps are normalised first, and the normalisation itself encodes two real findings:

  ```powershell
  # Structural dump with pg_dump's random \restrict nonce stripped, so two dumps
  # of the same schema compare equal.
  ...
  # Also drop COMMENT ON SCHEMA: it is Postgres's own default comment, not
  # application schema, and `reset-test` (drop schema public cascade) discards
  # it — which made the round-trip fail on a line no migration controls.
  ```

**None of this runs in CI** — CI has no Postgres. `db.ps1` is a developer-box gate.

## 1.6 Testing against a database — and how CI needs nothing

`TEST_DATABASE_URL` exists (`Settings.test_database_url`), but it is used by **exactly two things**:
`alembic -x db=test`, and `db.ps1`'s `roundtrip` / `reset-test`. **No test ever reads it.**

`.github/workflows/ci.yml` opens with the claim you asked about:

> *"The whole point of this gate is that it needs NOTHING: no Postgres, no Redis, no network calls
> and no LLM credential. Everything it runs is either a text scan or a pure function exercised
> against the fakes in api/tests/conftest.py."*

Here is the whole mechanism, in five parts:

**1. A marker that is excluded by default.** `api/pyproject.toml`:

```toml
addopts = "-m 'not integration'"
markers = [
    "integration: needs a live Postgres/Redis; excluded from the default run",
]
```

**2. Settings satisfied by environment before any import.** `api/tests/conftest.py`:

```python
# `caliber.db` calls `get_settings()` at module scope and builds the engine
# there, and every domain import pulls `caliber.db` in. […]
# `setdefault`, not assignment: a real environment (an integration run) wins.
# No connection is opened - `create_engine` is lazy - so this needs no server.
_OFFLINE_SETTINGS = {
    "DATABASE_URL": "postgresql+psycopg://caliber:caliber@127.0.0.1:5432/caliber_test",
    ...
}
for _k, _v in _OFFLINE_SETTINGS.items():
    os.environ.setdefault(_k, _v)
```

That DSN is a **placeholder that is never dialled**. `create_engine` builds no socket.

**3. CI hands the app a placeholder `.env`:**

```yaml
- name: Provide placeholder settings
  run: cp .env.example .env
```

with the comment: *"`.env.example` carries placeholders only - no secret, and nothing in this job
ever opens a connection, because `create_engine` is lazy."*

**4. Most tests use attribute bags, not ORM rows.** `FakeProfile`, `FakeExperience`,
`FakeProject`, `FakeEducation` — plain `@dataclass`es mirroring the columns:

> *"The functions under test only ever READ attributes off the ORM rows - they never call `db`,
> never touch a relationship loader […] so plain attribute bags are a faithful stand-in and a far
> sharper test subject: a fake cannot accidentally pass because a real row was populated by a
> fixture nobody read."*

**5. The paths that genuinely WRITE get in-memory SQLite, behind the same ORM.**

```python
@pytest.fixture
def sqlite_session():
    ...
    @compiles(JSONB, "sqlite")
    def _jsonb_as_json(type_, compiler, **kw):
        return "JSON"

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
```

with three lessons written into the comments:

- *"SQLite in memory keeps the file's constraint intact: still no server, no network, no credential.
  The one Postgres-only type the domain uses (JSONB) is shimmed to SQLite's JSON."*
- Import the model modules **before** `create_all`, or `Base.metadata` is empty and you get
  *"no such table: app_user"* — *"Order-dependent, and invisible until a new test module happened
  not to need the import."*
- `StaticPool` + `check_same_thread=False` because Starlette runs sync handlers on a worker thread
  and the default pool would give that thread *its own empty `:memory:` database*.

There is even a full HTTP fixture on top of it — `api_client` overrides FastAPI's `get_db`
dependency with the SQLite session and carries a genuinely signed session cookie.

**So: no schema-per-test, no transaction-rollback fixture, no truncation. There is no test
database at all.** SQLAlchemy's dialect layer is what makes one schema definition serve both
engines, and the `@compiles` shim is the entire cost of the difference.

## 1.7 The trace/audit tables — the analogue of `step_runs`

### `agent_call` — one row per LLM call
`api/src/caliber/models.py`, created in `alembic/versions/0001_baseline.py`, extended by
`b7e2c4d1a9f3`.

> *"agent_call - the local trace sink that stands in for Langfuse (deviation D1). Every LLM call
> writes exactly one row: prompt, context, model, tokens, cost, latency, outcome. This is what
> makes agent behaviour auditable without a hosted trace UI."*

| Column | Type | Null | Note |
|---|---|---|---|
| `id` | `uuid` PK | no | `default=uuid.uuid4` / `server_default gen_random_uuid()` |
| `created_at` | `timestamptz` | no | `server_default=func.now()` |
| `agent` | `varchar(64)` | no | indexed |
| `provider` | `varchar(32)` | no | |
| `model` | `varchar(64)` | no | model *served* |
| `effort` | `varchar(16)` | yes | |
| `served_from` | `varchar(16)` | no | `provider \| cache_exact \| fake` — *"distinguishes a real billed call from a replay"* |
| `outcome` | `varchar(16)` | no | `ok \| error` |
| `cw` | `varchar(16)` | yes | workload tag, **indexed** — *"the per-workload cost roll-up is the query that reads it"* |
| `prompt_version` | `varchar(64)` | yes | which prompt file |
| `prompt_hash` | `varchar(64)` | yes | *"the sha256 of exactly what the model saw"* |
| `request_hash` | `varchar(64)` | no | indexed; correlates the DB row with the JSONL file sink |
| `prompt` | `text` | no | the full prompt **is** stored |
| `context` | `jsonb` | yes | |
| `response` | `text` | yes | |
| `error` | `text` | yes | |
| `input_tokens` | `int` | no | default 0 |
| `output_tokens` | `int` | no | default 0 |
| `cost_usd` | `double precision` | no | default 0 |
| `latency_ms` | `int` | no | default 0 |

Indexes: `ix_agent_call_created_at`, `ix_agent_call_request_hash`, `ix_agent_call_agent`,
`ix_agent_call_cw`. No FK to a user or a run — the trace is standalone.

**Two sinks, one truth** (`api/src/caliber/tracing.py`): every call writes to `agent_call` **and**
to `logs/agent/agent-YYYY-MM-DD.jsonl`, both carrying `request_hash` — *"that reconciliation is
what replaces a hosted trace UI"*. The file write is wrapped so *"tracing must never break the
request"*, and the DB write swallows its exception too.

**Where the POC is already stricter than Caliber.** `write_trace(rec, db=None)` writes on the
**caller's** session when one is passed (`session.flush()`), and on its own session otherwise
(`session.commit()`). The call site (`llm/runtime.py:_record`) passes the caller's session, and it
writes **after** the call returns. So a caller that rolls back takes the trace with it — which is
exactly the lesson RULEBOOK §4 rule 9 ("record before you call, in its own transaction") was
written from. Keep the POC's rule; it is the improvement.

### `job_run` — durable job record
> *"jobs are recorded in POSTGRES, not Redis. Memurai Developer is non-production and
> self-terminates at 10 days, so Redis is transport only and must never be the system of record."*

`id` uuid PK · `created_at` / `updated_at` timestamptz · `job_type` varchar(64) ·
`status` varchar(16) NOT NULL default `'queued'` (`queued|running|succeeded|failed|cancelled`,
*"one vocabulary, used by the API and the web client alike"*) · `arq_job_id` varchar(128) ·
`payload` jsonb · `result` jsonb · `error` text · `attempts` int NOT NULL default 0.
Indexes on `status` and `created_at`.

`job_run` is the closest shape to the POC's `runs` table; `agent_call` to `step_runs`. Between
them they cover every column the POC already has except `salvaged_from`, `step`, `attempt` and
the resume-from-checkpoint fields — which are the POC's own additions and are good ones.

## 1.8 Deliberately avoided — the ADRs

`D:\Caliber\docs\decisions\`:

| ADR | Decision | The reason, in their words |
|---|---|---|
| **0005** Postgres-as-record / Redis-as-transport | `job_run` lives in Postgres; Redis/ARQ carries jobs *in flight* only; the semantic cache moved to pgvector | Memurai Developer *"self-terminates"* at ~10 days, `appendonly no`, no RediSearch. *"durability by configuration on a product that terminates itself is not durability."* Also: **the grading route is excluded from semantic caching in code** — *"two paraphrased answers are not the same answer; a cache hit would return someone else's score. This is a correctness rule, not a performance tuning choice."* |
| **0004** pgvector, no separate vector DB | Vectors in the same Postgres; local CPU embeddings | A dedicated vector DB is *"second store to operate, back up, and keep consistent, for retrieval volumes one Postgres handles."* Also: *"the swap-back to a hosted embedding model is a migration, not a config flip"* — a pgvector column's dimension is DDL-fixed. |
| **0013** `session_version` int, not a session table | One integer on `app_user`, embedded in the signed cookie | Revoking every cookie is one write instead of a table to keep and sweep |
| — | **No async engine** | *"async buys little here and costs greenlet/driver complexity on native Windows"* |
| — | **No native PG enums** | *"an ALTER TYPE per addition buys nothing when the application validates the value on the way in anyway"* |
| — | **No PITR** | *"real PITR needs WAL archiving to a separate device, and this box has one disk. A backup sitting beside the data it protects is a convenience, not disaster recovery."* |
| — | **No `CREATE EXTENSION` in migrations** | needs superuser; the app role deliberately isn't one |

One more finding: **pgvector is provisioned but unused.** `CREATE EXTENSION vector` runs in the
baseline migration and `db.ps1 verify` asserts an L2 distance works, but grepping the models turns
up **zero `Vector` columns**. The extension is infrastructure waiting for EMB-1. The POC should not
copy a dependency the product itself has not yet spent.

---

# Part 2 — What the POC should copy

Ranked. Each with the reason, and what it costs.

### C1. `timestamptz` for every timestamp, and set the database to UTC — **copy**
`DateTime(timezone=True)` in the models, `ALTER DATABASE ... SET timezone='UTC'` and
`datestyle='ISO, YMD'` in `ops/db-roles.sql`, with the reason:

> *"the server default came from the machine locale (Asia/Calcutta) and datestyle 'iso, dmy'. Every
> timestamp column in the app is timestamptz, and every trace correlates against logs, so the
> database speaks UTC and ISO."*

That is **this machine's locale**. The POC's `_now()` already produces
`datetime.now(timezone.utc).isoformat(timespec="seconds")` and stores it as `TEXT`. Moving to
`timestamptz` makes `ORDER BY created_at DESC` a real sort instead of a string sort, and makes
`SUM`/date arithmetic possible in the demo query.
**Cost:** two lines of `ALTER DATABASE`, and `RunRecord.created_at` becomes a `datetime` instead of
a `str` — so anything that prints it needs `.isoformat()`. Roughly a dozen touch points.

### C2. JSONB for `meta`, `output`, `problems`, `payload` — **copy**
Today the POC does `json.dumps(...)` on the way in and `json.loads(...)` on the way out, in four
places. With psycopg 3 and a `jsonb` column, both **disappear**: you pass
`psycopg.types.json.Jsonb(value)` and you get a Python object back. Plus the demo can run
`SELECT meta->>'model_requested', SUM(total_cost_usd) FROM step_runs GROUP BY 1`, which is a good
thing to show an audience.
**Cost:** near zero — it deletes code. The one gotcha: `Jsonb(None)` is SQL-null vs JSON `null`;
keep the existing `if x is not None` guards.

### C3. The offline-test arrangement, wholesale — **copy** (see Part 4B)
`addopts = "-m 'not <marker>'"` + `markers = [...]`, `os.environ.setdefault` before any app import,
a lazy connection, and fakes for everything that only reads. The POC's `tests/conftest.py` already
does the env-gate trick for `CALIBER_ALLOW_LLM`; this is the same move for `POC_DATABASE_URL`.
**Cost:** ~10 lines in `pytest.ini` and `conftest.py`.

### C4. Mirror every Python default with a `server_default` — **copy the discipline**
Even with plain SQL and no Alembic, this matters the moment you compare a live schema against the
committed `schema.sql` (C7 below). If `_now()` fills `created_at` in Python and the DDL says
`DEFAULT now()`, the two must agree or a hand-written `INSERT` in psql produces a row the app
cannot read back consistently.
**Cost:** one `DEFAULT` clause per defaulted column.

### C5. FK + `ON DELETE CASCADE` + an index on the FK column, all three — **copy**
Today `step_runs.run_id TEXT NOT NULL REFERENCES runs(run_id)` has no `ON DELETE` clause. The
composite `step_runs_by_run (run_id, step, attempt)` index already covers the FK lookup, so keep
that and add nothing. Add `ON DELETE CASCADE` so `DELETE FROM runs WHERE run_id = ...` cleans up a
demo run in one statement instead of three.
**Cost:** one clause. **Note:** SQLite does not enforce FKs unless `PRAGMA foreign_keys=ON`, which
the POC never sets — so this constraint starts being real on the day you switch. Expect one test to
discover an orphan it was silently allowed to create.

### C6. Narrow, named `varchar` widths — and clip before inserting — **copy the lesson, invert the choice**
`agent`, `model_requested`, `error_kind`, `subtype`, `cw`, `session_id` are all
provider-or-SDK-supplied strings in the POC too. Caliber's `_clip()` exists because a
`StringDataRightTruncation` **deactivates the caller's transaction** — in the POC that means a
`record_attempt()` for a failed step raises, and the step's audit row, the one thing RULEBOOK §4
rule 6 exists to guarantee, is lost.
**Two ways to avoid it:** use `text` (no length at all — Postgres `text` and `varchar(n)` have
identical performance) or use `varchar(n)` with a clip helper. **Recommend `text` for the POC**,
because a 590-test suite has no budget for a truncation bug and the widths buy nothing here.
Caliber chose widths because it has a web form and wanted the DB to be the last guard; the POC has
no such surface.
**Cost:** zero. This is the one place I'd deviate from Caliber outright.

### C7. `roundtrip`'s *idea*, in a test — **copy the idea, skip the tooling**
The valuable insight is *exit codes are not enough — compare the schema*. For the POC, the same
check is 15 lines and no Alembic: apply `SCHEMA` to a scratch database, `pg_dump --schema-only`,
compare against a committed `reference/schema.sql`. Mark it with the Postgres-only marker so it
skips when no server is present. Remember the two normalisations Caliber had to discover: strip
`pg_dump`'s random `\restrict` nonce and `COMMENT ON SCHEMA`.
**Cost:** ~20 lines + one committed file. Skip it if you would not maintain the committed dump —
a stale golden file is worse than no check.

### C8. `strip_nuls` on anything that came from a PDF — **copy, and you need it on day one**
`app/extraction.py` already strips C0 controls including NUL in `_clean()` (RULEBOOK O19), so the
extraction path is covered. The uncovered path is model output and error text going into
`step_runs.problems` / `meta` / `output`. A `\x00` there raises `psycopg.DataError`, and by
§1.7 that kills the audit row.
**Cost:** one helper applied in `record_attempt`.

---

# Part 3 — What the POC should skip, and why

| Skip | Why |
|---|---|
| **pgvector** | Caliber ships the extension and has **zero vector columns**. The POC has no retrieval step at all. Adding it means building an extension on Windows (`ops/build-pgvector.bat`, MSVC) for nothing. |
| **Redis / ARQ / `job_run`'s transport split** | ADR-0005 exists because Memurai self-terminates at 10 days. The POC's runner is synchronous plain Python by design (D11, RULEBOOK §4 rule 1) — there is no queue, so there is nothing to make durable. |
| **Async engine / asyncpg** | Caliber explicitly rejected async on native Windows. The POC's runner is `async` for the SDK's sake, but its store calls are microseconds of local I/O; making them async buys nothing and means every `store.*` call in `runner.py` grows an `await`. |
| **`fastapi-users`, `app_user`, entitlements, `session_version`** | The POC has one user and no auth (RULEBOOK §17 Out: auth, payments). A `user_id` FK on `runs` would be a column that is always the same value. |
| **A second `caliber_poc_test` database** | Caliber needs it only for `alembic -x db=test` and `roundtrip`. With no Alembic there is nothing to migrate into it, and no test reads it (§1.6). |
| **`ops/db.ps1` in full (396 lines)** | `provision` + `verify` are worth ~60 lines. `harden` (restarts the service), `backup`/`restore` (7-day rotation, `pg_dumpall --globals-only`), `psql`, `reset-test` are operations for a system with users and data worth losing. The POC's database is reproducible from `SCHEMA` and disposable. **Also: it hardcodes PostgreSQL 17** — copying it unchanged on this box gets you a script that looks for `C:\Program Files\PostgreSQL\17\bin` and service `postgresql-x64-17`. |
| **Multi-tenant / row-level concerns** | Not in scope; no second tenant exists. |
| **`Float` for money** | See Part 6. This is Caliber's weakest type choice and the POC should not copy it. |

---

# Part 4 — The two decisions

## 4A. SQLAlchemy + Alembic, or plain SQL with psycopg?

**Recommendation: keep plain SQL, use psycopg 3, and hand-roll a 40-line migration step.
Do not adopt SQLAlchemy. Do not adopt Alembic.**

Argued from this POC's situation, not from best practice:

**1. Three tables today, ~8 later, one developer, one machine.**
Alembic's value is *coordinating schema change across people and environments, over time,
reversibly*. Every one of those words is absent here. The POC's entire migration story can honestly
be "drop the database and re-apply `SCHEMA`", because the only data in it is demo runs that cost
pennies to regenerate. Alembic's price is not the library — it is `alembic.ini`, `env.py`, a
`versions/` directory, `--autogenerate` reviews, `compare_type`, `down_revision` chains, and the
`server_default`-mirroring discipline of §1.3 whose *only* purpose is making `alembic check` go
quiet. That is a lot of apparatus to keep quiet about 8 tables.

**2. The store is already the right shape, and an ORM does not improve it.**
`app/pipeline/store.py` is one class with a ~15-method vocabulary (`create_run`, `record_attempt`,
`completed`, `cost`, `decide`…). No SQL leaks to callers. `runner.py` never sees a query. That
encapsulation — not the ORM — is what makes a backend swap possible. SQLAlchemy would replace 330
readable lines with ~200 lines of model declarations *plus* a session lifecycle, and the callers
would look identical.

**3. RULEBOOK §2 rule 1: one concept per step.** The concept being learned this step is
*PostgreSQL* — jsonb, timestamptz, `ON CONFLICT`, identity columns, transactions. SQLAlchemy is a
second, larger concept that would sit between the user and the thing they are trying to learn. The
user writes this code (§2 rule 2); `INSERT INTO step_runs (...) VALUES (%s, ...)` is code they can
write and defend. `mapped_column(JSONB)` teaches SQLAlchemy.

**4. The demo audience.** This POC exists to show the org what was learned. A reader can open
`store.py`, see `CREATE TABLE step_runs (...)` and know the schema. With SQLAlchemy they see
declarations and have to trust that Alembic rendered them faithfully.

**What you give up, honestly, and it is one thing:** SQLAlchemy's dialect layer, which is exactly
what lets Caliber run its whole suite on SQLite (§1.6, the `@compiles(JSONB, "sqlite")` shim). With
hand-written SQL you cannot point the same statements at two engines: `?` vs `%s`, `AUTOINCREMENT`
vs `GENERATED ALWAYS AS IDENTITY`, `INSERT OR REPLACE` vs `ON CONFLICT ... DO UPDATE`, `REAL` vs
`numeric`, `TEXT` timestamps vs `timestamptz`. Five genuine divergences across ten statements. §4B
is the answer to that, and it does not need an ORM.

**If you decide otherwise** — if the demo's point is *"this is how Caliber builds it"* rather than
*"this is the pipeline"* — then take SQLAlchemy **Core** (`Table`/`MetaData`, not the ORM) and skip
Alembic anyway. Core gives you the dialect layer and the `@compiles` shim, in ~80 lines of table
definitions, without relationships, lazy loading, identity maps or session semantics. That is the
honest middle. The full ORM is not worth it at this size.

## 4B. How the 590 offline tests keep working — **the important question**

**Facts first.** Of 590 collected tests, **42 construct a `Store`**: all 16 in
`tests/test_pipeline_store.py` and all 26 in `tests/test_pipeline_runner.py` (which uses
`Store.in_memory()` in its fixture at line 33). The other **548 never touch persistence** and are
unaffected by anything below.

**The blunt answer to "can I just dump SQLite?": you can, and it costs you 42 tests' ability to run
without a database service.** Not the whole suite — collection does not connect — but
`python -m pytest -q` on a machine where `postgresql-x64-18` is stopped would go from 590 passed to
548 passed, 42 errored. That includes `test_a_failed_attempt_is_kept_not_overwritten` and the
runner's resume / checkpoint / repair-retry tests, which are the tests that prove RULEBOOK §4 rules
4, 5, 6 and 11. Those are the *most* valuable tests in the repo to keep cheap to run. **Know that
before you delete `Store.in_memory()`.**

### The four options, priced

| Option | What it is | Cost |
|---|---|---|
| **A. Test-only Postgres + `TRUNCATE` or schema-per-test** | `caliber_poc_test`, recreated per session | The service becomes a hard dependency of the suite. Slowest option. This is what Caliber explicitly refused. |
| **B. Transaction-rollback fixtures** | Open a transaction per test, roll back at teardown | Same hard dependency, just faster. Also *changes what you are testing*: the POC's store calls `self.db.commit()` after every statement, so a rollback fixture requires a nested-savepoint dance or a store that stops committing. Real refactor. |
| **C. Same SQL against both engines** | One statement set, lowest common denominator | The worst option. You lose `jsonb`, `timestamptz`, `ON CONFLICT` and identity columns — i.e. most of the reason to move — *and* a test can pass on SQLite and fail on Postgres, because the dialects differ exactly where it matters. |
| **D. Two backends behind one interface, plus a conformance suite** | **Recommended** | ~150 lines of new SQL + a parametrised test file |

### Recommended: option D

1. **Split the backend, keep the vocabulary.** Extract today's SQLite statements into
   `SqliteStore` and write `PostgresStore` beside it. Both expose the identical ~15 methods and
   return the same `RunRecord` / `StepRecord` dataclasses. `runner.py` and the demos import
   `Store` from `app/pipeline/__init__.py` and do not change at all.
2. **Choose the backend from the environment, once, in `app/config.py`.**
   `POC_DATABASE_URL` set → Postgres; unset → SQLite. One place, like Caliber's *"exactly one place
   a connection string is defined"*.
3. **Make `tests/test_pipeline_store.py` a conformance suite.** Parametrise its fixture over both
   backends; mark the Postgres parameter `@pytest.mark.postgres` and **skip** (not fail) it when
   `POC_TEST_DATABASE_URL` is unset. Copy Caliber's `pytest.ini` shape exactly:

   ```ini
   addopts = -m "not postgres"
   markers =
       postgres: needs a live PostgreSQL; excluded from the default run
   ```

   This is the same pattern the Agent SDK itself uses for store backends
   (`claude_agent_sdk.testing.session_store_conformance`, already noted in RULEBOOK §3.6) — a
   pleasing symmetry for the demo.
4. **Leave `test_pipeline_runner.py` on SQLite in memory.** Those 26 tests are about *sequence,
   retries, resume and pauses*, not about SQL. They should stay the fastest tests in the suite.

**Result:** `python -m pytest -q` still collects and passes **590 tests with no service running**.
On the developer's box with Postgres up, `python -m pytest -m postgres` runs the same 16 store
tests again against the real engine — so the backends cannot drift without a red test.

**Cost, stated plainly:**
- ~150 lines of Postgres SQL, most of it a mechanical `?`→`%s`, plus four real rewrites (Part 6).
- The risk that a store bug exists only in the Postgres path and nobody runs `-m postgres` that
  day. Mitigated by making the conformance suite the same file, so it is obvious it exists.
- A second `SCHEMA` constant. Real duplication; ~50 lines. This is the price of not using an ORM,
  and it is the honest trade against §4A.

**The alternative I would accept:** if the 42 tests genuinely do not matter to you, delete
`SqliteStore` and mark all 42 `postgres`. The suite then reports "590 collected, 42 deselected" on
a bare machine, which is at least honest and loud. What you must not do is leave them failing.

**One more honest note.** Caliber — which *ships* PostgreSQL — runs its whole ~790-test suite on
in-memory SQLite and fakes. Dumping SQLite from the POC would make the POC's test story strictly
weaker than the real product's. If someone in the demo audience asks "why do your tests need a
database when Caliber's don't?", there is no good answer.

---

# Part 5 — Connection and credentials on Windows

**The repo rule first, and there is a bug in it today.**
`.gitignore` line 11 is `.env.*`, which **also ignores `.env.example`**. The task's premise
(".env is git-ignored; .env.example is not") is not currently true in this repo — and there is no
`.env.example` yet. Fix before writing any credential handling:

```gitignore
.env
.env.*
!.env.example
```

Caliber's `.gitignore` gets the same job done with `.env`, `.env.local`, `.env.*.local`, `.env.bak*`
— and a comment recording that a real `.env.bak-before-local` was once found sitting untracked.

**What `.env.example` should carry** — placeholders only, every key the app reads, with the shape
documented. Caliber's is the model (its own header: *"Regenerate from .env.example"*):

```
# PostgreSQL 18 (native Windows service: postgresql-x64-18)
POC_DATABASE_URL=postgresql://caliber_poc:CHANGEME@127.0.0.1:5432/caliber_poc
# Set only to run the Postgres conformance tests (pytest -m postgres)
POC_TEST_DATABASE_URL=
```

**Rules, each with a Caliber precedent:**

1. **One place defines the connection string.** `app/config.py` reads `POC_DATABASE_URL`; nothing
   else builds a DSN. Caliber's `env.py`: *"so there is exactly one place a connection string is
   defined."* The POC has an extra reason: `store.py` is the file the demo audience reads, and a
   password-shaped string in it is the wrong thing to show them.
2. **`127.0.0.1`, never `localhost`.** Caliber uses the literal everywhere (`db.ps1`, the offline
   DSN in conftest). On Windows `localhost` can resolve to `::1` first and miss a `pg_hba.conf`
   that only has an IPv4 line — a confusing "no pg_hba.conf entry for host" on a server that is
   plainly running.
3. **Generate an alphanumeric-only password.** Straight from `docs/RUNBOOK-db.md`:
   *"generated, alphanumeric-only so no DSN needs URL-encoding."* A `@`, `:` or `/` in a password
   silently breaks a URL-style DSN and the error does not say so.
4. **A dedicated non-superuser role owning one database.** `CREATE ROLE caliber_poc LOGIN ...;
   CREATE DATABASE caliber_poc OWNER caliber_poc;` — two statements, and it means a mistake in
   `store.py` cannot reach anything else on the instance. Caliber asserts this in `db.ps1 verify`:
   *"the app must not run as one."*
5. **Never set `PGPASSWORD` machine-wide.** If a provisioning script needs it, set it **in the
   script's own process only** (`$env:PGPASSWORD = ...` inside the script, as `db.ps1` does), or
   better, use libpq's own `%APPDATA%\postgresql\pgpass.conf`, which lives outside the repo
   entirely. This mirrors RULEBOOK O2's existing rule about `ANTHROPIC_API_KEY`.
6. **Never log the DSN.** If a connection fails, log `dbname@host:port` and the driver's error, not
   the conninfo. `psycopg.conninfo.conninfo_to_dict()` lets you pick fields without printing the
   password.
7. **Set the database to UTC at creation time**, not in Python — Part 2 C1.
8. **`runs/` is already git-ignored**, which covers `runs/caliber.db`. When Postgres becomes the
   default, make sure nothing writes a dump or `pg_dump` output into the repo.

**psycopg 3 specifics for this store:**

- `psycopg.connect(url, row_factory=psycopg.rows.dict_row)` replaces
  `sqlite3.connect(...)` + `row_factory = sqlite3.Row`. `dict_row` returns real dicts, so
  `RunRecord(**row)` keeps working and `_to_step_record` stops needing `dict(row)`.
- Placeholders are `%s`, not `?`. (A literal `%` inside a SQL string must then be `%%`.)
- Default is **not** autocommit; the existing `self.db.commit()` calls are correct as they stand.
- JSON: `from psycopg.types.json import Jsonb` on the way in; values come back already decoded.
- `psycopg[binary]` in `requirements.txt` — the binary wheel bundles libpq, which is what makes
  this a one-line install on Windows. Caliber pins exactly `psycopg[binary]>=3.2`.
- The POC's CLI can be long-lived across a checkpoint pause. Caliber's `pool_pre_ping=True` exists
  for exactly that (*"a PG bounce must not wedge the pool"*). Without SQLAlchemy the equivalent is
  a one-line reconnect guard: if `conn.closed`, reopen. Do not add `psycopg_pool` — one connection,
  one process.

---

# Part 6 — Table-by-table conversion of `app/pipeline/store.py`

What actually changes, with the recommendation for each.

| Today (SQLite) | Postgres | Why / cost |
|---|---|---|
| `run_id TEXT PRIMARY KEY` | **`run_id text PRIMARY KEY`** — *keep text, do not use `uuid`* | The POC generates `uuid.uuid4().hex` (32 chars, no dashes) and the tests pass literal handles: `store.create_run("older")`, `store.create_run("newer")`, `store.get_run("nope")`. A `uuid` column rejects all three and breaks `test_runs_are_listed_newest_first` and `test_an_unknown_run_is_a_key_error` outright. Caliber uses `uuid` because its ids are never human-supplied. **Zero cost to keep `text`; real cost to change.** |
| `created_at TEXT` / `updated_at TEXT` | `timestamptz NOT NULL DEFAULT now()` | Part 2 C1. `_now()` returns a `str`; either keep passing the ISO string (Postgres parses it) or pass the `datetime`. Recommend passing the `datetime` and letting the dataclass hold a `datetime`. |
| `status TEXT` | `text NOT NULL` + keep the module constants | Matches Caliber: no native enum, no CHECK, validated in Python. `RUNNING/WAITING/DONE/FAILED` already are that vocabulary. |
| `id INTEGER PRIMARY KEY AUTOINCREMENT` | `bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY` | The SQL-standard form, preferred over `bigserial`. Note `record_attempt` currently ends with `return self.attempts(run_id)[-1]` — a re-read of every row for that run. Replace with `INSERT ... RETURNING *`, which is both correct and cheaper. |
| `total_cost_usd REAL` | **`numeric(12,6)`** — *deviate from Caliber* | Caliber uses `Float`/`double precision` and has no `Numeric` anywhere. But RULEBOOK §16.2 is a story about a cost being compared against a ceiling ($0.1107 vs $0.10) — a number used in a comparison that decides success should be exact, not binary-float. **Cost:** psycopg returns `Decimal`; cast at the dataclass boundary (`float(row["total_cost_usd"])`) and `StepRecord.total_cost_usd: float \| None` and `Store.cost() -> float` stay exactly as they are. ~2 lines. |
| `problems TEXT` (json.dumps) | `jsonb` | Part 2 C2 — deletes the dumps/loads pair |
| `meta TEXT`, `output TEXT` (json.dumps) | `jsonb` | same; and enables `meta->>'cw'` roll-ups in the demo |
| `latency_ms / input_tokens / output_tokens INTEGER` | `integer` | unchanged |
| `agent`, `model_requested`, `error_kind`, `subtype`, `session_id`, `cw` … | **`text`, no width** | Part 2 C6 — deliberately unlike Caliber's `varchar(16/32/64)`, to make `StringDataRightTruncation` structurally impossible. A truncation here would lose the audit row for a *failed* step, which is the row RULEBOOK §4 rule 6 most wants kept. |
| `UNIQUE (run_id, step, attempt)` | unchanged | Already the right constraint. |
| `CREATE INDEX IF NOT EXISTS step_runs_by_run ON step_runs (run_id, step, attempt)` | keep; rename to `ix_step_runs_run_step_attempt` | Caliber's naming convention. Cosmetic. |
| `REFERENCES runs(run_id)` | `REFERENCES runs(run_id) ON DELETE CASCADE` | Part 2 C5 |
| `INSERT OR REPLACE INTO checkpoints` | `INSERT INTO checkpoints (...) VALUES (...) ON CONFLICT (run_id, key) DO UPDATE SET decided_at = EXCLUDED.decided_at, payload = EXCLUDED.payload` | **A real rewrite, not a translation.** `INSERT OR REPLACE` does not exist in Postgres. |
| `SELECT MAX(attempt) ...` then a separate `INSERT` | unchanged, but know it is a race | Two processes would collide; `UNIQUE (run_id, step, attempt)` catches it as a `UniqueViolation` rather than corrupting data. The POC is single-process, so this is a note, not a task. If it ever matters, the fix is `INSERT ... SELECT COALESCE(MAX(attempt),0)+1 ...` in one statement. |
| `Store.__init__` runs `executescript(SCHEMA)` on **every** construction | **Move DDL out of the constructor** | `CREATE TABLE IF NOT EXISTS` on every `Store()` is harmless against a private file and wrong against a shared server — it means every CLI invocation issues DDL, and DDL takes locks. Recommend an explicit `init_schema(conn)` called by `scripts/db_init.py` or `step3_demo.py --init`, plus a startup check that the tables exist with a clear error if not. **Cost:** one extra command to remember, one clear failure message instead of silent auto-creation. |
| *(new)* a `schema_version` table | `CREATE TABLE schema_version (version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())` + `migrations/001_*.sql`, `002_*.sql` applied in order | This is the whole hand-rolled migration story from §4A: ~40 lines that read the current version, apply each higher-numbered file in a transaction, and record it. It is Alembic's useful 5%, and for 8 tables it is enough. |

---

## Open questions for the user

1. **Is the CLI/FastAPI demo (Step 12) going to run more than one process?** If yes, revisit the
   `next_attempt` race and the single-connection assumption. If no (and I assume no), neither
   matters.
2. **Do you want a committed `reference/schema.sql` golden file** for the roundtrip-style check
   (Part 2 C7)? Only worth it if you will regenerate it; a stale one is worse than none.
3. **Should the SQLite backend survive past the demo,** or is it explicitly a test-only artifact?
   The answer changes whether `SqliteStore` gets a docstring saying "tests and offline demos only"
   or "supported backend".

## Sources

`D:\Caliber\api\pyproject.toml` · `api\src\caliber\db.py` · `api\src\caliber\core\config.py` ·
`api\src\caliber\models.py` · `api\src\caliber\domain.py` · `api\src\caliber\enums.py` ·
`api\src\caliber\tracing.py` · `api\src\caliber\llm\runtime.py` · `api\alembic\env.py` ·
`api\alembic.ini` · `api\alembic\versions\0001_baseline.py` ·
`api\alembic\versions\b7e2c4d1a9f3_s1_agent_call_cw_prompt_provenance.py` ·
`api\tests\conftest.py` · `api\tests\test_nul_byte_guard.py` · `.github\workflows\ci.yml` ·
`ops\db.ps1` · `ops\db-roles.sql` · `docs\RUNBOOK-db.md` ·
`docs\decisions\0004-pgvector-single-store-local-embeddings.md` ·
`docs\decisions\0005-postgres-record-redis-transport.md` ·
`docs\decisions\0013-session-version-not-session-table.md` ·
POC: `app\pipeline\store.py` · `app\pipeline\runner.py` · `tests\conftest.py` · `.gitignore` ·
`pytest.ini` · `reference\agents\AGENT_WORK_DESIGN.md`
