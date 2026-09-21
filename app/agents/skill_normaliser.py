"""[1] Profiler · CW-3 skill normalise — "Postgres" and "PostgreSQL" are one skill.

Model half : choose, for each term, which offered canon key it means (or none).
Code half  : `app.skillcanon` retrieves the candidates beforehand, and every
             answer is checked against the list that term was actually offered.

Caliber's shape for CW-3 is **retrieve → constrained-select**, with the checker
"canon ∈ candidates (hallucinated canon = 0)". The model never sees an open
field, and a key it invents cannot survive `_verify()` — which is the whole
reason this is cheap enough for Haiku with no effort setting.

Why it matters: step [3] Gap Analyst joins the candidate's skills to the bar's
sub-skills. Two spellings of one skill read as a gap the candidate does not
have. RULEBOOK O16 recorded that deviation; this closes it.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.base import AgentSpec, CallMeta, QueryFn, fence, load_prompt, run_agent
from app.config import HAIKU
from app.schemas import SkillNormalisation
from app.skillcanon import Candidate, SkillCanon

SKILL_NORMALISER = AgentSpec(
    name="skill_normaliser",
    prompt=load_prompt("skill_normalise", 1),
    output_model=SkillNormalisation,
    model=HAIKU,  # RULEBOOK §10 / CW-3: "frontier spend here buys nothing measurable"
    # Caliber budgets <$0.01 for this workload. The ceiling is a runaway guard.
    max_budget_usd=0.10,
    cw="cw-3",
)

# One call covers this many terms. Beyond it the list is split, because a long
# candidate list is where a model starts borrowing keys between terms.
MAX_TERMS_PER_CALL = 25


@dataclass(frozen=True)
class NormalisedSkill:
    """What the code kept, after checking the model's choice."""

    skill: str  # the term as the candidate wrote it
    canon_key: str | None  # a key from this term's own candidate list, or None
    canon_name: str | None
    confidence: str | None
    offered: tuple[str, ...]  # the keys this term was offered
    rejected: str | None = None  # why the model's answer was refused, if it was

    @property
    def matched(self) -> bool:
        return self.canon_key is not None


@dataclass
class NormalisationRun:
    skills: list[NormalisedSkill]
    meta: CallMeta

    @property
    def unmatched(self) -> list[str]:
        return [s.skill for s in self.skills if not s.matched]

    @property
    def refused(self) -> list[NormalisedSkill]:
        """Answers the code threw away — the hallucinated-canon counter."""
        return [s for s in self.skills if s.rejected]


def build_user_prompt(terms: dict[str, list[Candidate]]) -> str:
    """Fence the terms and the exact candidate list offered for each.

    The candidates are ours, not the candidate's, but the *terms* came out of a
    resume, so the whole payload is fenced as untrusted.
    """
    if not terms:
        raise ValueError("no terms to normalise")
    if len(terms) > MAX_TERMS_PER_CALL:
        raise ValueError(f"{len(terms)} terms; split into calls of {MAX_TERMS_PER_CALL}")

    payload = {
        "terms": [
            {
                "skill": term,
                "candidates": [
                    {
                        "key": c.key, "name": c.name, "area": c.area,
                        "matched_on": c.matched_on,
                        # "alias" = the bar calls this skill by that word;
                        # "tool" = that word is only something you'd USE for it,
                        # which is weaker evidence and the model should say so.
                        "matched_as": c.via,
                    }
                    for c in candidates
                ],
            }
            for term, candidates in terms.items()
        ]
    }
    return "\n\n".join([
        fence("terms", payload, source="candidate"),
        "Match each term to one of its own candidates, or to null.",
    ])


def _verify(
    draft: SkillNormalisation,
    terms: dict[str, list[Candidate]],
    canon: SkillCanon,
) -> list[NormalisedSkill]:
    """Keep only choices the model was entitled to make.

    Three ways an answer is refused, all of them silent corrections to null:
      * the term was never asked about (an invented row);
      * the key was not offered for THIS term (borrowed from another, or made up);
      * the key is not in the canon at all.
    """
    by_skill = {m.skill: m for m in draft.matches if m.skill is not None}
    results: list[NormalisedSkill] = []

    for term, candidates in terms.items():
        offered = tuple(c.key for c in candidates)
        match = by_skill.get(term)
        if match is None:
            results.append(NormalisedSkill(term, None, None, None, offered, "no answer returned"))
            continue

        key = match.canon_key
        if key is None:
            results.append(NormalisedSkill(term, None, None, None, offered))
        elif key not in offered:
            results.append(NormalisedSkill(
                term, None, None, None, offered,
                f"{key!r} was not offered for this term",
            ))
        elif not canon.knows(key):
            results.append(NormalisedSkill(
                term, None, None, None, offered, f"{key!r} is not in the canon",
            ))
        else:
            results.append(NormalisedSkill(
                term, key, canon.get(key).name, match.confidence, offered,
            ))

    return results


async def run_skill_normaliser(
    terms: list[str],
    canon: SkillCanon,
    *,
    query_fn: QueryFn | None = None,
) -> NormalisationRun:
    """Normalise `terms` against `canon`. One call; the code checks every answer."""
    offered = {term: canon.candidates(term) for term in dict.fromkeys(terms) if term}
    if not offered:
        raise ValueError("no terms to normalise")

    prompt = build_user_prompt(offered)
    result = await run_agent(SKILL_NORMALISER, prompt, query_fn=query_fn)
    return NormalisationRun(skills=_verify(result.output, offered, canon), meta=result.meta)
