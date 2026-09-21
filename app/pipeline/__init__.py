"""The pipeline: plain Python owning the sequence (D11 / ADR-0008)."""

from app.pipeline.runner import (
    MAX_ATTEMPTS,
    PipelineOutcome,
    Step,
    StepResult,
    Verdict,
    classify,
    run_pipeline,
    run_step,
)
from app.pipeline.steps import ANSWERS_NEEDED, CONFIRM_PROFILE, PIPELINE, questions_for
from app.pipeline.store import (
    SERVED_CACHE,
    SERVED_FAKE,
    SERVED_PROVIDER,
    InputRecord,
    PostgresStore,
    SqliteStore,
    Store,
    StepRecord,
    open_store,
)

__all__ = [
    "MAX_ATTEMPTS", "PipelineOutcome", "Step", "StepResult", "Verdict",
    "classify", "run_pipeline", "run_step",
    "ANSWERS_NEEDED", "CONFIRM_PROFILE", "PIPELINE", "questions_for",
    "Store", "SqliteStore", "PostgresStore", "open_store",
    "StepRecord", "InputRecord",
    "SERVED_PROVIDER", "SERVED_FAKE", "SERVED_CACHE",
]
