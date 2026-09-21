"""[1] Profiler · CW-4 claim–evidence verdict — is this quote *about* this skill?

Model half : given a skill, one verbatim quote from the candidate's own text and
             the project it came from, say what that quote proves on the existing
             four-level ladder — none / mentioned / demonstrated / led.
Code half  : `demote_only()` below. CW-4 may lower the verdict CW-1 already
             settled; it may never raise one. Every refused raise is recorded.

**Why this workload exists.** Our grounding check proves a quote is *real* — a
verbatim substring of the candidate's material. It cannot prove the quote is
*about* the skill it was filed under. The reference calls that the known defect
class D10: Terraform rated "demonstrated" on "I ran the schema migrations". The
quote is genuine, the project really did use Terraform, and the rating is still
wrong. Judging aboutness is the one part of the ladder no substring test can
reach, so it is the one part a model is asked to do.

**One pass, not two.** Caliber runs Opus for the verdict plus a Sonnet citations
pass, because citations and structured output cannot be requested together
(HTTP 400). We do not need the second pass: `app.candidate_profile` has already
checked every quote verbatim before CW-4 sees it, so a citations pass would
re-solve a solved problem and pay Sonnet to do it.

**Optional, never a replacement.** CW-1 still produces an inline verdict for
every skill (weaker-wins against the code cap). CW-4 is a second opinion over
those settled verdicts; nothing in `run_profiler()` or `build_profile()` changes,
and a profile built without ever calling CW-4 is still a complete profile.
RULEBOOK §16.5: the PRD asks for an evidence strength on the SkillProfile and
never mandates a separately-routed adjudication pass — ours is a quality option.

**The proposed verdict is deliberately not sent to the model.** It would only
invite agreement, and demote-only is enforced here in code either way.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.base import AgentSpec, CallMeta, QueryFn, fence, load_prompt, run_agent
from app.candidate_profile import EVIDENCE_ORDER, evidence_rank
from app.config import OPUS
from app.schemas import ClaimVerdictSet, Verdict

CLAIM_VERDICT = AgentSpec(
    name="claim_verdict",
    prompt=load_prompt("claim_verdict", 1),
    output_model=ClaimVerdictSet,
    # The one agent in this POC that is not Haiku. The reference's reason, taken
    # on trust until the evals run: "hardest Profiler task; a false
    # 'demonstrated' is unrecoverable." Effort is the only depth control Opus
    # has, and `max` is warned against for structured output (AgentSpec forbids
    # it outright).
    model=OPUS,
    effort="high",
    # Caliber budgets $0.05–0.15 per candidate here and calls it the dominant
    # Profiler cost. This ceiling is a runaway guard, not a target: on a
    # single-turn call it stops nothing, it only decides whether the run reports
    # `success` or `error`. It sits well above that range because our
    # analysis-first schemas ran ~10x Caliber's estimate on the 2026-09-21 live
    # CW-1 call (RULEBOOK §16.4) — and well below "unbounded", because Opus
    # output is 5x Haiku's price, so a runaway here costs real money.
    max_budget_usd=0.50,
    cw="cw-4",
)

# One call covers this many claims. Beyond it the list is split. A long batch is
# where a model starts carrying one claim's reasoning into the next — and unlike
# CW-3, where a borrowed canon key cannot survive that term's candidate list, a
# verdict borrowed from a neighbouring claim is perfectly well-formed.
MAX_CLAIMS_PER_CALL = 20


@dataclass(frozen=True)
class Claim:
    """One thing to adjudicate: a skill, the quote filed under it, and where it came from."""

    claim_id: str
    skill: str
    quote: str  # already checked verbatim against the candidate's text
    proposed: Verdict  # what CW-1 settled; never sent to the model
    project: str | None = None  # the project the quote came from, in the candidate's words


@dataclass(frozen=True)
class AdjudicatedClaim:
    """One claim after the gate: what was proposed, what was answered, what we keep."""

    claim_id: str
    skill: str
    proposed: Verdict  # CW-1's verdict
    model_verdict: Verdict | None  # CW-4's answer; None = it did not answer
    verdict: Verdict  # what the profile should carry
    confidence: str | None
    note: str | None = None  # why `verdict` is not `model_verdict`, when it is not

    @property
    def demoted(self) -> bool:
        return evidence_rank(self.verdict) < evidence_rank(self.proposed)

    @property
    def promotion_refused(self) -> bool:
        """The model rated this claim higher than CW-1 did, and was overruled."""
        return (
            self.model_verdict is not None
            and evidence_rank(self.model_verdict) > evidence_rank(self.proposed)
        )

    @property
    def skipped(self) -> bool:
        return self.model_verdict is None


@dataclass
class VerdictRun:
    claims: list[AdjudicatedClaim]
    meta: CallMeta

    @property
    def demoted(self) -> list[AdjudicatedClaim]:
        return [c for c in self.claims if c.demoted]

    @property
    def promotions_refused(self) -> list[AdjudicatedClaim]:
        """The demote-only counter — how often the model reached above its remit."""
        return [c for c in self.claims if c.promotion_refused]

    @property
    def skipped(self) -> list[AdjudicatedClaim]:
        return [c for c in self.claims if c.skipped]


def demote_only(proposed: Verdict, model_verdict: Verdict | None) -> Verdict:
    """The gate: the weaker of the two verdicts, compared by rank, never by string.

    CW-4 is a second opinion on a verdict the code half already settled, so it
    may subtract evidence and never add any — it sees one quote, where CW-1 saw
    the whole document. No answer at all leaves the proposal untouched.

    This is deliberately *not* `final_evidence()`, which floors its result at
    "mentioned" because the code half only knows the skill appears somewhere in
    the candidate's text. CW-4's entire finding is that a quote may not be about
    the skill at all, so that floor would erase the one thing this call buys.
    """
    if model_verdict is None:
        return proposed
    return EVIDENCE_ORDER[min(evidence_rank(proposed), evidence_rank(model_verdict))]


def build_user_prompt(claims: list[Claim]) -> str:
    """Fence the claims. The quotes and project text are the candidate's own words.

    `proposed` is not in the payload: the model is asked what the quote proves,
    not whether it agrees with us.
    """
    if not claims:
        raise ValueError("no claims to adjudicate")
    if len(claims) > MAX_CLAIMS_PER_CALL:
        raise ValueError(f"{len(claims)} claims; split into calls of {MAX_CLAIMS_PER_CALL}")
    ids = [c.claim_id for c in claims]
    if len(set(ids)) != len(ids):
        raise ValueError("claim ids must be unique within one call")

    payload = {
        "claims": [
            {
                "claim_id": c.claim_id,
                "skill": c.skill,
                "quote": c.quote,
                "project": c.project,
            }
            for c in claims
        ]
    }
    return "\n\n".join([
        fence("claims", payload, source="candidate"),
        "For each claim, say what its quote proves about its skill.",
    ])


def _verify(draft: ClaimVerdictSet, claims: list[Claim]) -> list[AdjudicatedClaim]:
    """Apply the gate to every claim we sent, and only to those.

    Three silent corrections happen here:
      * a verdict for a claim we never sent is dropped — there is no proposal to
        gate it against, so there is nothing it could mean;
      * a claim the model skipped, or answered with null, keeps its proposal and
        is recorded as unanswered;
      * a verdict above the proposal is refused, the proposal stands, and the
        attempt is written into `note` so the audit shows it was made.
    """
    answered: dict[str, Verdict | None] = {}
    confidences: dict[str, str | None] = {}
    for row in draft.verdicts:
        if row.claim_id is None or row.claim_id in answered:
            continue  # the first answer for an id wins; a repeat is not a second opinion
        answered[row.claim_id] = row.verdict
        confidences[row.claim_id] = row.confidence

    results: list[AdjudicatedClaim] = []
    for claim in claims:
        if claim.claim_id not in answered:
            results.append(AdjudicatedClaim(
                claim.claim_id, claim.skill, claim.proposed, None,
                claim.proposed, None, "no verdict returned",
            ))
            continue

        said = answered[claim.claim_id]
        confidence = confidences[claim.claim_id]
        if said is None:
            results.append(AdjudicatedClaim(
                claim.claim_id, claim.skill, claim.proposed, None,
                claim.proposed, confidence, "no verdict returned",
            ))
            continue

        kept = demote_only(claim.proposed, said)
        if evidence_rank(said) > evidence_rank(claim.proposed):
            note = f"{said!r} refused: CW-4 may only demote, so {claim.proposed!r} stands"
        elif kept != claim.proposed:
            note = f"demoted from {claim.proposed!r}"
        else:
            note = None
        results.append(AdjudicatedClaim(
            claim.claim_id, claim.skill, claim.proposed, said, kept, confidence, note,
        ))

    return results


async def run_claim_verdict(
    claims: list[Claim],
    *,
    query_fn: QueryFn | None = None,
) -> VerdictRun:
    """Adjudicate `claims` in one call. The model proposes; the code decides."""
    if not claims:
        raise ValueError("no claims to adjudicate")
    prompt = build_user_prompt(claims)
    result = await run_agent(CLAIM_VERDICT, prompt, query_fn=query_fn)
    return VerdictRun(claims=_verify(result.output, claims), meta=result.meta)
