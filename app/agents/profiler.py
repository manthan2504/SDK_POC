"""[1] Profiler — "understand the candidate's experience" (PRD v1.7 §10.1).

Model half : read the resume and/or the candidate's answers into a ProfileDraft.
             Path A = resume (+ follow-up answers); Path B (PRD FR-A2) = guided
             manual onboarding, answers only, no resume.
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
from app.config import HAIKU
from app.policy import MAX_ANSWERS_CHARS, MAX_RESUME_CHARS
from app.schemas import ProfileDraft

PROFILER = AgentSpec(
    name="profiler",
    prompt=load_prompt("profiler", 2),
    output_model=ProfileDraft,
    model=HAIKU,  # RULEBOOK §10: Haiku, never `effort`
    # Raised from 0.10 after the 2026-09-21 live run (RULEBOOK §16.2): one real
    # 2-page resume cost $0.1107 — ProfileDraft v2 asks for a quote per field, so
    # a complete draft runs ~18k output tokens. This ceiling is a runaway guard,
    # not a cost control; it stops nothing on a single-turn call. Why the draft is
    # that large is a schema question for the evals (step 11), not a cap to tune.
    max_budget_usd=0.25,
    cw="cw-1",
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

    @property
    def salvaged(self) -> bool:
        """True when the draft was kept from a run the SDK stopped at a ceiling.

        The run is still usable — the draft validated — but it was cut short,
        so the caller should surface it (and read `meta.subtype` /
        `meta.total_cost_usd` for why) rather than treat it as a clean pass.
        """
        return self.meta.salvaged_from is not None


def check_resume(resume_text: str) -> str:
    text = resume_text.strip()
    if not text:
        raise ValueError("resume text is empty")
    if len(text) > MAX_RESUME_CHARS:
        raise ValueError(f"resume text is {len(text):,} characters; the limit is {MAX_RESUME_CHARS:,}")
    return text


def build_user_prompt(
    resume_text: str | None,
    answers: list[CandidateAnswer] | None = None,
    feedback: list[str] | None = None,
) -> str:
    """Fence the candidate's material. Path A: resume (+ answers). Path B: answers only.

    `feedback` is the validation problems from a rejected previous reply, added by
    the pipeline's repair retry (RULEBOOK §4 rule 5). It is our own text, not the
    candidate's, so it is not fenced — but it is the only thing here that isn't.
    """
    has_resume = bool(resume_text and resume_text.strip())
    if not has_resume and not answers:
        raise ValueError("nothing to profile: need a resume or at least one answer")
    parts: list[str] = []
    if has_resume:
        parts.append(fence("resume", check_resume(resume_text or ""), source="candidate"))
    if answers:
        total = sum(len(a.answer) for a in answers)
        if total > MAX_ANSWERS_CHARS:
            raise ValueError(f"answers total {total:,} characters; the limit is {MAX_ANSWERS_CHARS:,}")
        payload = {"answers": [a.model_dump() for a in answers]}
        parts.append(fence("answers", payload, source="candidate"))
    if has_resume and answers:
        task = "Record the career history this resume states, using the answers to fill what the resume leaves out."
    elif has_resume:
        task = "Record the career history this resume states."
    else:
        task = "Record the career history these answers state."
    if feedback:
        problems = "\n".join(f"- {p}" for p in feedback)
        task += (
            "\n\nYour previous reply was rejected for these reasons. Fix exactly these "
            f"and change nothing else:\n{problems}"
        )
    return "\n\n".join([*parts, task])


def grounding_sources(resume_text: str | None, answers: list[CandidateAnswer] | None) -> list[str]:
    """Quotes may come from the resume (when there is one) or the candidate's own answers."""
    resume = [resume_text] if resume_text and resume_text.strip() else []
    return [*resume, *(a.answer for a in answers or [])]


async def run_profiler(
    resume_text: str | None,
    answers: list[CandidateAnswer] | None = None,
    *,
    today: date | None = None,
    feedback: list[str] | None = None,
    query_fn: QueryFn | None = None,
) -> ProfilerRun:
    prompt = build_user_prompt(resume_text, answers, feedback)
    result = await run_agent(PROFILER, prompt, query_fn=query_fn)
    profile = build_profile(
        result.output,
        grounding_sources(resume_text, answers),
        today=today,
        typed_sources=[a.answer for a in answers or []],
    )
    return ProfilerRun(draft=result.output, profile=profile, meta=result.meta)
