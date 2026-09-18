"""POC-wide settings: paths, model ids, and the live-call gate.

Models are config values (RULEBOOK §10) — agents name a constant from here,
never a raw model string.
"""

from pathlib import Path

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

# --- Live-call gate --------------------------------------------------------
# No agent may call an LLM unless this env var is exactly "1".
# Set it only for a run the user has explicitly approved.
LLM_GATE_ENV = "CALIBER_ALLOW_LLM"

# --- Profiler (POC choices, not in Caliber's config yet) -------------------
MAX_RESUME_CHARS = 60_000  # Caliber's cap on resume text sent to the model
YEARS_TOLERANCE = 1.0  # stated vs dated years may differ by this much before we flag it

# --- Per-call ceilings (defaults; an agent spec may tighten them) ----------
DEFAULT_MAX_TURNS = 3  # structured output is delivered via a tool call, so allow a short round trip
DEFAULT_MAX_BUDGET_USD = 0.25
