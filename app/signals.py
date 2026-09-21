"""Profile signals — ownership, seniority and per-skill depth (PRD v1.7 §7.1).

Pure arithmetic over facts already extracted and graded elsewhere (text tiers,
flags, evidence strengths, recency). Nothing here calls a model or reads text
quality itself: callers pass computed tiers in. Rules mirror Caliber
(reference/plan/ARITHMETIC_RULES.md §3); every number and word list lives in
`app.policy`. Role-agnostic (FR-I5): no skill or role names appear here.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from app import policy
from app.textmatch import normalise_for_match

Tier = Literal["none", "some", "strong"]
Level = Literal["leader", "owner", "contributor"]
SIGNAL_KEYS = ("scope", "tradeoffs", "ambiguity", "cross_team")


# ---------------------------------------------------------------------------
# Input records
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RoleFacts:
    role_id: str
    led_team: bool | None
    team_size: int | None


@dataclass(frozen=True)
class ProjectFacts:
    project_id: str
    role_id: str | None
    your_role: str | None
    scale_tier: str
    hardest_tier: str
    hardest_flags: frozenset[str]
    hardest_words: int


# ---------------------------------------------------------------------------
# Output records
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OwnershipRead:
    level: Level
    basis: str


@dataclass(frozen=True)
class SignalRead:
    tier: Tier
    count: int
    total: int
    basis: str


# ---------------------------------------------------------------------------
# Team quote parsing
# ---------------------------------------------------------------------------
_NUMBER_WORD = re.compile(r"\b(" + "|".join(policy.NUMBER_WORDS) + r")\b")
_TEAM_OF = re.compile(r"\bteam of (?:about |around |roughly |over |~)?(\d+)\b")
_N_PERSON = re.compile(r"\b(\d+)[- ](?:person|people|member|strong|staff)\b")
_VERB_N = re.compile(r"\b([a-z]+) (?:a team of |about |around |roughly |over )?(\d+)(?: ([a-z]+))?")
_N_PLURAL = re.compile(r"\b(\d+) ([a-z]+)")


def _prepare(text: str) -> str:
    t = normalise_for_match(text)
    return _NUMBER_WORD.sub(lambda m: str(policy.NUMBER_WORDS[m.group(1)]), t)


def _is_headcount_noun(word: str | None) -> bool:
    return word is None or word not in policy.NOT_HEADCOUNT_NOUNS


def parse_team_size(team_quote: str | None) -> int | None:
    """First plausible headcount (1..MAX_TEAM_SIZE) in a team quote, else None.

    Recognises "team of 6", "a 12-person team", "led 4 people", "6 engineers"
    and spelled-out numbers one..twelve. A number followed by a time or volume
    word ("3 years", "500 users") is never a headcount.
    """
    if not team_quote:
        return None
    t = _prepare(team_quote)
    found: list[tuple[int, int]] = []  # (position, value)
    for m in _TEAM_OF.finditer(t):
        found.append((m.start(1), int(m.group(1))))
    for m in _N_PERSON.finditer(t):
        found.append((m.start(1), int(m.group(1))))
    for m in _VERB_N.finditer(t):
        if m.group(1) in policy.TEAM_SIZE_VERBS and _is_headcount_noun(m.group(3)):
            found.append((m.start(2), int(m.group(2))))
    for m in _N_PLURAL.finditer(t):
        noun = m.group(2)
        if len(noun) > 2 and noun.endswith("s") and _is_headcount_noun(noun):
            found.append((m.start(1), int(m.group(1))))
    return next((v for _, v in sorted(found) if 1 <= v <= policy.MAX_TEAM_SIZE), None)


_TOKEN = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
_CLAUSE_SPLIT = re.compile("[" + re.escape(policy.LEAD_CLAUSE_BREAKS) + "]")
_SUBJECT_SKIP = (
    policy.LEAD_SUBJECT_ADVERBS
    | policy.LEAD_SUBJECT_FILLERS
    | policy.PASSIVE_AUXILIARIES
    | policy.PEOPLE_LEAD_WORDS
    | policy.TEAM_SIZE_VERBS
    | policy.TEAM_OBJECT_VERBS
)


def _candidate_is_subject(tokens: list[str], i: int) -> bool:
    """Looking back from tokens[i], is the subject "I" or absent (resume style)?

    Adverbs, "and", auxiliaries, numbers and chained lead verbs are skipped; the
    first other word decides. A team word ("we", "our") or a third party
    ("manager", "cto", "priya", "who") means someone else led.
    """
    for w in reversed(tokens[:i]):
        if w in policy.LEAD_SELF_SUBJECTS:
            return True
        if w in _SUBJECT_SKIP or w.isdigit():
            continue
        return False
    return True  # clause starts with the marker: resume style


def _is_passive(tokens: list[str], i: int) -> bool | None:
    """True if tokens[i] is passive by someone else; None if "by me" (the candidate)."""
    nxt = tokens[i + 1] if i + 1 < len(tokens) else None
    if nxt == "by":
        after = tokens[i + 2] if i + 2 < len(tokens) else None
        return None if after in policy.PASSIVE_SELF_AGENTS else True
    if tokens[i].endswith("ing"):  # "was leading" is active
        return False
    for w in reversed(tokens[:i]):
        if w in policy.LEAD_SUBJECT_ADVERBS:
            continue
        return w in policy.PASSIVE_AUXILIARIES
    return False


def _clause_leads(clause: str) -> bool:
    if any(p in clause for p in policy.PEOPLE_LEAD_SELF_PHRASES):
        return True
    tokens = _TOKEN.findall(clause)
    for i, w in enumerate(tokens):
        if w not in policy.PEOPLE_LEAD_WORDS:
            continue
        passive = _is_passive(tokens, i)
        if passive is None:  # "led by me"
            return True
        if not passive and _candidate_is_subject(tokens, i):
            return True
    for p in policy.PEOPLE_LEAD_PHRASES:
        if p in policy.PEOPLE_LEAD_SELF_PHRASES:
            continue
        pos = clause.find(p)
        if pos >= 0 and _candidate_is_subject(tokens, len(_TOKEN.findall(clause[:pos]))):
            return True
    return False


def leads_people(team_quote: str | None) -> bool | None:
    """Does the team quote say the candidate led people? None if there is no quote.

    True needs a people-leading marker ("led", "managed", "direct reports", ...)
    that the candidate is the subject of: not passive ("was managed by", "led by
    our manager") and, looking back within its clause, the subject is "I" or
    absent (resume style "Led a team of 4") — not a team word ("we led") or a
    third party ("our manager led", "the CTO managed"). Member-only phrasing
    ("was part of", "member of") anywhere means False.
    """
    if team_quote is None or not team_quote.strip():
        return None
    t = normalise_for_match(team_quote)
    if any(p in t for p in policy.TEAM_MEMBER_PHRASES):
        return False
    t = _prepare(team_quote)
    return any(_clause_leads(c) for c in _CLAUSE_SPLIT.split(t))


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------
_OWNER_ROLES = frozenset({"owned", "built_solo"})


def ownership(roles: Sequence[RoleFacts], projects: Sequence[ProjectFacts]) -> OwnershipRead:
    """leader (led a team or a project) > owner (owned / built solo) > contributor."""
    led_roles = [r.role_id for r in roles if r.led_team is True]
    led_projects = [p.project_id for p in projects if p.your_role == "led"]
    if led_roles or led_projects:
        parts = []
        if led_roles:
            parts.append(f"led a team in {_plural(len(led_roles), 'role')}")
        if led_projects:
            parts.append(f"led {_plural(len(led_projects), 'project')}")
        return OwnershipRead("leader", "Leader: " + " and ".join(parts) + ".")
    owned = [p.project_id for p in projects if p.your_role in _OWNER_ROLES]
    if owned:
        return OwnershipRead("owner", f"Owner: owned or built alone {_plural(len(owned), 'project')}.")
    if not projects:
        return OwnershipRead("contributor", "Contributor: no project evidence captured yet.")
    return OwnershipRead("contributor", "Contributor: no project was led or owned.")


def ownership_level(roles: Sequence[RoleFacts], projects: Sequence[ProjectFacts]) -> Level:
    return ownership(roles, projects).level


# ---------------------------------------------------------------------------
# Seniority signals
# ---------------------------------------------------------------------------
def _rank(tier: str) -> int:
    return policy.TIERS.index(tier) if tier in policy.TIERS else 0


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def signal_tier(count: int, total: int) -> Tier:
    """none if 0; strong if count >= STRONG_MIN_COUNT and count/total >= STRONG_MIN_RATIO; else some."""
    if count <= 0 or total <= 0:
        return "none"
    if count >= policy.STRONG_MIN_COUNT and count / total >= policy.STRONG_MIN_RATIO:
        return "strong"
    return "some"


def _read(count: int, total: int, unit: str, what: str) -> SignalRead:
    basis = f"{count} of {_plural(total, unit)} {what}."
    return SignalRead(signal_tier(count, total), count, total, basis)


def _defended(p: ProjectFacts) -> bool:
    return p.hardest_tier == "specific" and "causal" in p.hardest_flags and p.hardest_words >= policy.DEFENDED_MIN_WORDS


def _cross_team(r: RoleFacts) -> bool:
    return r.led_team is True or (r.team_size is not None and r.team_size >= policy.SIZABLE_TEAM)


def seniority_signals(roles: Sequence[RoleFacts], projects: Sequence[ProjectFacts]) -> dict[str, SignalRead]:
    """scope, tradeoffs, ambiguity (a defended decision) and cross_team, each none/some/strong.

    cross_team is read from the roles, so it is computed even with no projects.
    """
    cross = sum(1 for r in roles if _cross_team(r))
    cross_read = _read(cross, len(roles), "role", f"led a team or had a team of {policy.SIZABLE_TEAM}+")
    if not projects:
        empty = SignalRead("none", 0, 0, "No project evidence captured yet")
        return {"scope": empty, "tradeoffs": empty, "ambiguity": empty, "cross_team": cross_read}
    n = len(projects)
    substantive = _rank("substantive")
    scope = sum(1 for p in projects if _rank(p.scale_tier) >= substantive)
    tradeoffs = sum(1 for p in projects if p.hardest_tier == "specific")
    ambiguity = sum(1 for p in projects if _defended(p))
    return {
        "scope": _read(scope, n, "project", "describe the scale of the work"),
        "tradeoffs": _read(tradeoffs, n, "project", "name a specific decision in the hardest problem"),
        "ambiguity": _read(
            ambiguity, n, "project",
            f"defend a decision with a reason in at least {policy.DEFENDED_MIN_WORDS} words",
        ),  # fmt: skip
        "cross_team": cross_read,
    }


# ---------------------------------------------------------------------------
# Depth score (display only — never used in gap size)
# ---------------------------------------------------------------------------
def _strength_rank(strength: str) -> int:
    order = list(policy.DEPTH_BASE)  # none < mentioned < demonstrated < led
    return order.index(strength) if strength in policy.DEPTH_BASE else 0


def depth_score(sources: Iterable[tuple[str, bool]], recency: str) -> tuple[int, str]:
    """Per-skill depth score 0-100 and the arithmetic behind it, in plain words.

    `sources` = one (evidence_strength, quantified) per contributing project.
    base[strongest] + corroboration (extra deep sources) + mention bonus
    + quantified bonus + recency adjustment, clamped to 0..100.
    """
    items = list(sources)
    strongest = max((s for s, _ in items), key=_strength_rank, default="none")
    base = policy.DEPTH_BASE.get(strongest, 0)
    deep = [(s, q) for s, q in items if s in policy.DEPTH_DEEP_STRENGTHS]
    mentions = len(items) - len(deep)
    corro = min(policy.DEPTH_CORROBORATION_CAP, policy.DEPTH_CORROBORATION_STEP * max(0, len(deep) - 1))
    extra_mentions = mentions if deep else max(0, mentions - 1)
    corro_m = min(policy.DEPTH_MENTION_CAP, policy.DEPTH_MENTION_STEP * extra_mentions)
    quant = policy.DEPTH_QUANTIFIED_BONUS if any(q for _, q in deep) else 0
    adj = policy.DEPTH_RECENCY_ADJ.get(recency, policy.DEPTH_RECENCY_ADJ["unknown"])
    raw = base + corro + corro_m + quant + adj
    score = max(0, min(100, raw))

    parts = [f"{strongest} {base}"]
    if corro:
        parts.append(f"+ corroboration {corro}")
    if corro_m:
        parts.append(f"+ mentions {corro_m}")
    if quant:
        parts.append(f"+ quantified {quant}")
    parts.append(f"+ recency {recency} {adj:+d}" if adj else f"+ recency {recency} 0")
    basis = " ".join(parts) + f" = {score}"
    if score != raw:
        basis += f" (clamped from {raw})"
    return score, basis


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------
def education_weight(years: float | None) -> int:
    """1 below EDUCATION_FULL_WEIGHT_YEARS of experience, else 0 (unknown years -> 0)."""
    return 1 if years is not None and years < policy.EDUCATION_FULL_WEIGHT_YEARS else 0
