"""[1] Profiler — "understand the candidate's experience" (PRD v1.7 §10.1).

Model half : read the resume (+ any follow-up answers) into a ProfileDraft.
Code half  : app.candidate_profile.build_profile() grounds, dates, rates and
             computes missing fields. The model never decides completeness.

The completeness loop (PRD §7.1) is app-owned: if profile.missing_fields is not
empty, the app asks the candidate those questions and calls run_profiler() again
with the same resume plus the answers. Nothing here loops by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel

from app.agents.base import AgentSpec, CallMeta, QueryFn, fence, load_prompt, run_agent
from app.candidate_profile import CandidateProfile, build_profile
from app.config import HAIKU, MAX_RESUME_CHARS
from app.schemas import ProfileDraft

PROFILER = AgentSpec(
    name="profiler",
    prompt=load_prompt("profiler", 1),
    output_model=ProfileDraft,
    model=HAIKU,  # RULEBOOK §10: Haiku, never `effort`
    max_budget_usd=0.10,
)


class CandidateAnswer(BaseModel):
    """The candidate's reply to one missing-field question."""

    key: str
    question: str
    answer: str


@dataclass
class ProfilerRun:
    draft: ProfileDraft  # what the model returned (validated)
    profile: CandidateProfile  # what the app keeps (grounded + computed)
    meta: CallMeta  # audit facts for the StepRun record


def check_resume(resume_text: str) -> str:
    text = resume_text.strip()
    if not text:
        raise ValueError("resume text is empty")
    if len(text) > MAX_RESUME_CHARS:
        raise ValueError(f"resume text is {len(text):,} characters; the limit is {MAX_RESUME_CHARS:,}")
    return text


def build_user_prompt(resume_text: str, answers: list[CandidateAnswer] | None = None) -> str:
    parts = [fence("resume", check_resume(resume_text), source="candidate")]
    if answers:
        payload = {"answers": [a.model_dump() for a in answers]}
        parts.append(fence("answers", payload, source="candidate"))
        task = "Record the career history this resume states, using the answers to fill what the resume leaves out."
    else:
        task = "Record the career history this resume states."
    return "\n\n".join([*parts, task])


def grounding_sources(resume_text: str, answers: list[CandidateAnswer] | None) -> list[str]:
    """Quotes may come from the resume or from the candidate's own answers."""
    return [resume_text, *(a.answer for a in answers or [])]


async def run_profiler(
    resume_text: str,
    answers: list[CandidateAnswer] | None = None,
    *,
    today: date | None = None,
    query_fn: QueryFn | None = None,
) -> ProfilerRun:
    prompt = build_user_prompt(resume_text, answers)
    result = await run_agent(PROFILER, prompt, query_fn=query_fn)
    profile = build_profile(result.output, grounding_sources(resume_text, answers), today=today)
    return ProfilerRun(draft=result.output, profile=profile, meta=result.meta)
