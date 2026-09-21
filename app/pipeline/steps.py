"""The fixed step list (PRD v1.7 §10.1). Order is data, not behaviour.

Only [1] Profiler exists today; [2]–[8] append to `PIPELINE` as they are built,
and nothing in `runner.py` changes when they do. That is the whole point of
D11 — the sequence is a list you can read, not an agent's decision.

Each step owns the small amount of glue between the store's JSON and its agent:
what to feed in, what to hand on, and which pause follows it.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.agents.profiler import CandidateAnswer, run_profiler
from app.candidate_profile import CandidateProfile
from app.pipeline.runner import Step, StepResult

# Checkpoint keys (FR-I11). The app pauses at these; the agents know nothing
# about them.
ANSWERS_NEEDED = "answers_needed"  # the completeness loop: the profile has gaps
CONFIRM_PROFILE = "confirm_profile"  # PRD §7.1: the candidate confirms before [2]


async def _profiler(state: dict[str, Any], feedback: list[str]) -> StepResult:
    """[1] Profiler — resume and/or answers in, grounded CandidateProfile out.

    Re-running after the candidate answers is a *loop*, not a retry: the same
    resume plus the new answers, which is why the answers live in the state and
    not in the feedback.
    """
    answers = [CandidateAnswer(**a) if isinstance(a, dict) else a for a in state.get("answers", [])]
    run = await run_profiler(
        state.get("resume_text"),
        answers,
        today=state.get("today") or date.today(),
        feedback=feedback,
        query_fn=state.get("query_fn"),
    )
    # The draft is the model's proposal; the profile is what the app keeps.
    state["draft"] = run.draft
    return StepResult(output=run.profile, meta=run.meta, salvaged=run.salvaged)


def _after_profiler(profile: CandidateProfile) -> str | None:
    """Gaps first, then confirmation — the candidate never confirms a profile
    the code already knows is incomplete."""
    if profile.required_missing:
        return ANSWERS_NEEDED
    return CONFIRM_PROFILE


PROFILER_STEP = Step(
    number=1,
    key="profile",
    title="[1] Profiler — understand the candidate's experience",
    execute=_profiler,
    checkpoint_for=_after_profiler,
    repeat_after=frozenset({ANSWERS_NEEDED}),
    revive=CandidateProfile.model_validate,
)

PIPELINE: list[Step] = [PROFILER_STEP]


def questions_for(profile: CandidateProfile) -> list[dict[str, str]]:
    """What to ask at an ANSWERS_NEEDED pause — required first, nudges after."""
    return [
        {"key": m.key, "question": m.question, "required": str(m.required)}
        for m in profile.missing_fields
    ]
