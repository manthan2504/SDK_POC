"""POC-wide settings: paths, model ids, and the live-call gate.

Models are config values (RULEBOOK §10) — agents name a constant from here,
never a raw model string.
"""

import os
from pathlib import Path

from app.envfile import load_poc_env

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
DATA_DIR = PROJECT_ROOT / "data"
RUNS_DIR = PROJECT_ROOT / "runs"
# Neutral working directory handed to every agent, so no agent runs "inside" the repo.
AGENT_CWD = RUNS_DIR / "agent_cwd"

# --- Models (RULEBOOK §10) -------------------------------------------------
OPUS = "claude-opus-5"
SONNET = "claude-sonnet-5"
HAIKU = "claude-haiku-4-5"

# Haiku 4.5 rejects the `effort` parameter; only these models may receive it.
EFFORT_CAPABLE_MODELS = frozenset({OPUS, SONNET})

# --- Database (RULEBOOK §16.3) -------------------------------------------
# Postgres is the system of record; SQLite backs the offline tests. The URL
# decides which backend `Store.from_url()` builds, so nothing else branches.
#
# Secrets live in `.env` (git-ignored), never here and never in `.env.example`.
# `.env` is read here, once, at import — but ONLY `POC_*` keys, and never over an
# environment variable that is already set (app/envfile.py). `CALIBER_ALLOW_LLM`
# is deliberately not loadable from a file: the live-call gate is set by hand.
load_poc_env(PROJECT_ROOT / ".env")
POC_DATABASE_URL = os.environ.get("POC_DATABASE_URL", f"sqlite:///{RUNS_DIR / 'caliber.db'}")

# Set ONLY when a throwaway Postgres test database exists. Unset (the default)
# means the @pytest.mark.postgres tests skip and the suite needs no server —
# the same arrangement Caliber uses for its own ~790 tests.
POC_TEST_DATABASE_URL = os.environ.get("POC_TEST_DATABASE_URL")


# --- Live-call gate --------------------------------------------------------
# No agent may call an LLM unless this env var is exactly "1".
# Set it only for a run the user has explicitly approved.
LLM_GATE_ENV = "CALIBER_ALLOW_LLM"


# --- Per-call ceilings (defaults; an agent spec may tighten them) ----------
DEFAULT_MAX_TURNS = 3  # structured output is delivered via a tool call, so allow a short round trip
DEFAULT_MAX_BUDGET_USD = 0.25
