"""[1] Profiler · CW-2 elicitation — wording the asks.

Model half : phrase each gap as a question a busy person will answer.
Code half  : `CandidateProfile.missing_fields` decided WHICH gaps exist, and
             `_verify()` refuses any question for a gap that was not on the list.

The split is the design (AGENT_CAPABILITIES_AND_MODELS §4.1 CW-2):

    "missing fields are **computed**; model only phrases"

Completeness is arithmetic — a field is null or it is not — so letting a model
decide what is missing would let it invent a demand or excuse a real gap. The
eval gate Caliber names is *invented-demand rate*, and `_verify()` is where that
rate is held at zero: a key we never asked about is dropped, not shown.

The templates in `candidate_profile.py` stay as the fallback. They are correct
but rigid, and twenty-six of them in a row reads like a form — which is how a
candidate abandons the capture step. This agent is the difference between a form
and being asked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.base import AgentSpec, CallMeta, QueryFn, fence, load_prompt, run_agent
from app.candidate_profile import CandidateProfile, MissingField
from app.config import HAIKU
from app.policy import FIELD_ASK_TERMS, FIELD_PURPOSE
from app.schemas import Elicitation
from app.textmatch import normalise_for_match

ELICITOR = AgentSpec(
    name="elicitor",
    prompt=load_prompt("elicitation", 2),
    output_model=Elicitation,
    model=HAIKU,  # RULEBOOK §10 / CW-2: Haiku 4.5, no effort
    # Caliber budgets $0.02–0.05. A ceiling, not a target.
    max_budget_usd=0.15,
    cw="cw-2",
)

# Asking for more than this at once abandons the candidate rather than the form.
# The code decides which to send; the rest wait for the next round.
MAX_GAPS_PER_CALL = 12


def field_of(key: str) -> str:
    """The profile field a gap key is about.

    Keys are `role:r1:context`, `project:p1:impact`, `project:p1:impact:quantify`
    (a refinement) and `project:p1:vague:<term>`. The field is the third segment,
    plus the fourth when the fourth names a refinement rather than a term.
    """
    parts = key.split(":")
    if len(parts) < 3:
        return parts[-1]
    field = parts[2]
    if field == "vague":
        return "vague"
    if len(parts) > 3 and f"{field}:{parts[3]}" in FIELD_PURPOSE:
        return f"{field}:{parts[3]}"
    return field


def asks_for(question: str, field: str) -> bool:
    """Does this wording still ask for what the field needs?

    The measured failure (RULEBOOK §16.4) was a question with the right key that
    asked a different thing — "What was your focus area?" for a gap needing
    employment type, team size and whether they led anyone. The key check could
    not see it, because the key was correct.

    Deliberately permissive: a field with no listed terms passes, and one whole
    word is enough. This rejects a question about another subject, not a
    question worded unusually — and a false reject only costs template wording.
    """
    terms = FIELD_ASK_TERMS.get(field)
    if not terms:
        return True
    haystack = f" {normalise_for_match(question)} "
    return any(
        (f" {term} " in haystack) if " " not in term and not term.endswith("-")
        else (term in haystack)
        for term in (normalise_for_match(t) for t in terms)
    )


@dataclass(frozen=True)
class AskedQuestion:
    """One gap, with the wording that will actually be shown."""

    key: str
    question: str
    required: bool
    reason: str
    phrased: bool  # False = the model's wording was refused, template text shown
    refused: str | None = None  # why it was refused, when it was

    @property
    def source(self) -> str:
        return "model" if self.phrased else "template"


@dataclass
class ElicitationRun:
    questions: list[AskedQuestion]
    opening: str | None
    meta: CallMeta
    # Keys the model answered that we never asked about. Caliber's eval gate for
    # CW-2 is the invented-demand rate, so this is the number that gate reads.
    invented: list[str] = field(default_factory=list)

    @property
    def fell_back(self) -> list[str]:
        """Gaps the model skipped, now showing their template wording."""
        return [q.key for q in self.questions if not q.phrased]


def gaps_to_ask(profile: CandidateProfile, limit: int = MAX_GAPS_PER_CALL) -> list[MissingField]:
    """Required gaps first, then nudges — the code's decision, not the model's."""
    required = [m for m in profile.missing_fields if m.required]
    optional = [m for m in profile.missing_fields if not m.required]
    return [*required, *optional][:limit]


def _context(gap: MissingField, profile: CandidateProfile) -> dict[str, Any]:
    """The candidate's own words for whatever this gap is about.

    Without it the model writes "your second project"; with it, the project's
    real name. Only what the gap needs — never the whole profile.
    """
    parts = gap.key.split(":")
    kind, ident = (parts + ["", ""])[:2]
    context: dict[str, Any] = {}

    if kind == "role":
        role = next((r for r in profile.roles if r.role_id == ident), None)
        if role:
            context = {"employer": role.employer, "title": role.title}
    elif kind == "project":
        project = next((p for p in profile.projects if p.project_id == ident), None)
        if project:
            context = {"project": project.name}
            role = next((r for r in profile.roles if r.role_id == project.role_id), None)
            if role:
                context["employer"] = role.employer
            field = parts[2] if len(parts) > 2 else ""
            wrote = getattr(project, field, None)
            if isinstance(wrote, str) and wrote and gap.reason in ("thin", "refine"):
                context["wrote"] = wrote
            if field == "vague" and len(parts) > 3:
                context["term"] = parts[3]

    return {k: v for k, v in context.items() if v}


def build_user_prompt(gaps: list[MissingField], profile: CandidateProfile) -> str:
    if not gaps:
        raise ValueError("no gaps to phrase")
    if len(gaps) > MAX_GAPS_PER_CALL:
        raise ValueError(f"{len(gaps)} gaps; the limit for one round is {MAX_GAPS_PER_CALL}")

    payload = {
        "gaps": [
            {
                "key": gap.key,
                "field": field_of(gap.key),
                # What a usable answer contains. Without it the model invents a
                # reasonable-sounding question for the wrong thing (§16.4).
                "answer_must_give": FIELD_PURPOSE.get(field_of(gap.key), ""),
                "reason": gap.reason,
                "context": _context(gap, profile),
            }
            for gap in gaps
        ]
    }
    return "\n\n".join([
        fence("gaps", payload, source="candidate"),
        "Write one question for each gap, in the order given.",
    ])


def _verify(draft: Elicitation, gaps: list[MissingField]) -> tuple[list[AskedQuestion], list[str]]:
    """Every gap gets a question; nothing else does.

    A gap the model skipped keeps its template wording, so the candidate is
    still asked. A key the model invented is counted and dropped.
    """
    asked_for = {gap.key: gap for gap in gaps}
    phrased = {
        q.key: q.question
        for q in draft.questions
        if q.key is not None and q.question and q.question.strip()
    }

    questions: list[AskedQuestion] = []
    for gap in gaps:
        wording = phrased.get(gap.key)
        refused: str | None = None
        if wording is None:
            refused = "no question returned"
        elif not asks_for(wording, field_of(gap.key)):
            # Right key, wrong question. The template is correct by construction,
            # so the candidate gets asked properly rather than asked something else.
            refused = f"does not ask for {field_of(gap.key)}"
        questions.append(AskedQuestion(
            key=gap.key,
            question=gap.question if refused else wording,
            required=gap.required,
            reason=gap.reason,
            phrased=refused is None,
            refused=refused,
        ))

    invented = sorted(key for key in phrased if key not in asked_for)
    return questions, invented


async def run_elicitor(
    profile: CandidateProfile,
    *,
    limit: int = MAX_GAPS_PER_CALL,
    query_fn: QueryFn | None = None,
) -> ElicitationRun:
    """Phrase this profile's gaps. The gap list is the code's; only wording is the model's."""
    gaps = gaps_to_ask(profile, limit)
    prompt = build_user_prompt(gaps, profile)
    result = await run_agent(ELICITOR, prompt, query_fn=query_fn)
    questions, invented = _verify(result.output, gaps)

    return ElicitationRun(
        questions=questions,
        opening=result.output.opening,
        meta=result.meta,
        invented=invented,
    )
