"""CW-3 skill normalise, code half: the canon, and retrieval into it.

    "Postgres" ─▶ retrieve candidates (THIS FILE, deterministic)
               ─▶ constrained-select one of them (the model, CW-3 agent)
               ─▶ validator: the chosen key MUST be one we offered

Caliber's design for CW-3 is *retrieve → constrained-select*, and the checker is
"canon ∈ candidates (hallucinated canon = 0)". So the model never sees an open
field: it picks from a list this file produced, or says none of them fit. A key
it invents cannot survive, because `SkillCanon.knows()` refuses it.

The canon is seeded from the role bar's sub-skill keys and aliases (D9/FR-I5:
role content lives in YAML, never in code), which is exactly what
AGENT_CAPABILITIES_AND_MODELS §4.1 names as the CW-3 resource.

Why this matters downstream: step [3] Gap Analyst compares the candidate's
skills against the bar's sub-skills. Without normalisation, "Postgres" and
"PostgreSQL" are two different skills and the gap engine reports a gap the
candidate does not have. RULEBOOK O16 recorded that as a known deviation; this
module is what closes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

from app.config import DATA_DIR
from app.vague import normalise_term

ROLEBARS_DIR = DATA_DIR / "rolebars"

# How many canon entries the model is offered for one skill. Caliber's escalation
# for a failed select is "widened candidates", so this is a floor to widen from,
# not a limit on what exists.
MAX_CANDIDATES = 8

# A tool hit can never outrank a skill-name hit, however exact it is: listing
# pgvector is not the same claim as judging embedding trade-offs.
TOOL_MATCH_CEILING = 75

# A single-token alias this short matches too much ("bge", "rag" are real, but
# two-letter fragments are noise), so short aliases must match as whole tokens.
SHORT_ALIAS_CHARS = 3


@dataclass(frozen=True)
class CanonSkill:
    """One sub-skill of the bar: the join key everything downstream uses."""

    key: str  # e.g. "retrieval.embeddings" — stable, the thing we join on
    name: str  # human label, for the question text
    area: str  # the parent capability area, e.g. "retrieval"
    aliases: tuple[str, ...]  # OTHER WORDS for this same skill
    # Products and libraries you would USE while doing it. Kept apart from
    # aliases because they are not the same claim: pgvector is not another word
    # for "embedding selection & trade-offs", it is something you may have used
    # without ever making a trade-off. A tool-only hit therefore scores below an
    # alias hit, and carries a label so the model can weigh it.
    tools: tuple[str, ...] = ()

    @property
    def spellings(self) -> tuple[str, ...]:
        """Words that NAME this skill: its label, its key, its aliases."""
        return _unique_terms([self.name, self.key.rsplit(".", 1)[-1].replace("_", " "), *self.aliases])

    @property
    def tool_spellings(self) -> tuple[str, ...]:
        """Words that merely SUGGEST this skill."""
        return _unique_terms(self.tools)

    @property
    def all_spellings(self) -> tuple[str, ...]:
        return self.spellings + self.tool_spellings


@dataclass(frozen=True)
class Candidate:
    """One canon entry offered to the model, with why it was offered."""

    key: str
    name: str
    area: str
    matched_on: str  # the spelling that pulled it in — shown to the model as evidence
    exact: bool  # a spelling matched the whole term, not just part of it
    via: str = "alias"  # "alias" = a word for the skill; "tool" = a thing used for it

    @property
    def names_the_skill(self) -> bool:
        return self.via == "alias"


@dataclass(frozen=True)
class SkillCanon:
    """The bar's sub-skills, indexed for retrieval."""

    role_key: str
    version: str
    skills: tuple[CanonSkill, ...] = field(default_factory=tuple)
    # What a depth / weight number in this bar MEANS, loaded from the file so
    # the rubric travels with the values (ARITHMETIC_RULES 6).
    depth_scale: dict[int, str] = field(default_factory=dict)
    weight_scale: dict[int, str] = field(default_factory=dict)

    def depth_word(self, level: int) -> str:
        """A bare 3 is not a requirement; "can design with it" is."""
        return self.depth_scale.get(level, f"depth {level}")

    def knows(self, key: str | None) -> bool:
        """The validator behind 'hallucinated canon = 0'."""
        return any(s.key == key for s in self.skills)

    def get(self, key: str) -> CanonSkill:
        for skill in self.skills:
            if skill.key == key:
                return skill
        raise KeyError(f"not in the canon: {key}")

    def candidates(self, term: str | None, limit: int = MAX_CANDIDATES) -> list[Candidate]:
        """Canon entries a human might plausibly mean by `term`, best first.

        Deterministic and explainable: exact spelling, then whole-token overlap.
        No embeddings — EMB-1 is out of POC scope, and a wrong *candidate list* is
        recoverable (the model declines) where a wrong *canon* is not.
        """
        needle = normalise_term(term)
        if not needle:
            return []
        needle_tokens = set(needle.split())

        scored: list[tuple[int, int, Candidate]] = []
        for skill in self.skills:
            best: tuple[int, str, str] | None = None  # (score, spelling, via)
            for spelling in skill.spellings:
                score = _score(needle, needle_tokens, spelling)
                if score and (best is None or score > best[0]):
                    best = (score, spelling, "alias")
            for spelling in skill.tool_spellings:
                # Capped, so naming the skill always beats naming a tool.
                score = min(_score(needle, needle_tokens, spelling), TOOL_MATCH_CEILING)
                if score and (best is None or score > best[0]):
                    best = (score, spelling, "tool")
            if best is not None:
                score, spelling, via = best
                scored.append((
                    score,
                    -len(spelling),  # a tighter match wins ties
                    Candidate(skill.key, skill.name, skill.area, spelling,
                              exact=score >= 100, via=via),
                ))

        scored.sort(key=lambda row: (-row[0], -row[1]))
        return [candidate for _, _, candidate in scored[:limit]]


def _unique_terms(raw: Iterable[str]) -> tuple[str, ...]:
    seen: list[str] = []
    for term in (normalise_term(r) for r in raw):
        if term and term not in seen:
            seen.append(term)
    return tuple(seen)


def collisions(canon: SkillCanon) -> dict[str, list[str]]:
    """Spellings claimed by more than one skill.

    ARITHMETIC_RULES 7 validates unique *keys* and says nothing about unique
    spellings — and a duplicate is silent: retrieval just offers both, so the
    model is asked to choose between two entries a human meant as one. The
    placeholder bar had one ("long context"), which is why this exists.
    """
    owners: dict[str, list[str]] = {}
    for skill in canon.skills:
        for spelling in skill.all_spellings:
            owners.setdefault(spelling, []).append(skill.key)
    return {term: keys for term, keys in owners.items() if len(keys) > 1}


def _score(needle: str, needle_tokens: set[str], spelling: str) -> int:
    """0 = no match. Higher is a better reason to offer this candidate."""
    if needle == spelling:
        return 100
    spelling_tokens = set(spelling.split())
    if needle_tokens == spelling_tokens:
        return 90
    shared = needle_tokens & spelling_tokens
    if not shared:
        return 0
    # A short token has to match whole; that is already true here, since we
    # compare tokens rather than substrings. "sql" will not pull in "postgresql".
    if len(spelling) <= SHORT_ALIAS_CHARS and spelling not in needle_tokens:
        return 0
    covered = len(shared) / max(len(needle_tokens), len(spelling_tokens))
    return int(40 + covered * 40)


# The bar groups sub-skills under `competencies`, and keeps a separate
# `landscape` list for tools that are not competencies in their own right. Both
# are legitimate join targets for a candidate's skill, so both are indexed.
_SKILL_SECTIONS = ("competencies", "landscape")


def _sub_skills(bar: dict[str, Any]) -> Iterable[CanonSkill]:
    for area in bar.get("competencies", []) or []:
        area_key = area.get("key", "")
        for sub in area.get("sub_skills", []) or []:
            key = sub.get("key")
            if not key:
                continue
            yield CanonSkill(
                key=key,
                name=str(sub.get("name") or key.rsplit(".", 1)[-1].replace("_", " ")),
                area=str(area_key),
                aliases=tuple(str(a) for a in (sub.get("aliases") or [])),
                tools=tuple(str(t) for t in (sub.get("tools") or [])),
            )

    # Landscape entries are flat: a tool, not a competency with children.
    for tool in bar.get("landscape", []) or []:
        key = tool.get("key")
        if not key:
            continue
        yield CanonSkill(
            key=key,
            name=str(tool.get("name") or key.replace("_", " ")),
            area="landscape",
            aliases=tuple(str(a) for a in (tool.get("aliases") or [])),
            tools=tuple(str(t) for t in (tool.get("tools") or [])),
        )


def load_canon(role_key: str, version: str | None = None) -> SkillCanon:
    """Read a bar from `data/rolebars/<role>/<version>/bar.yaml`.

    `version=None` takes the only version present, and refuses if there are
    several — picking one silently is how a run ends up citing a bar nobody
    chose.
    """
    role_dir = ROLEBARS_DIR / role_key
    if not role_dir.is_dir():
        raise FileNotFoundError(f"no role bar for {role_key!r} in {ROLEBARS_DIR}")

    if version is None:
        versions = sorted(p.name for p in role_dir.iterdir() if (p / "bar.yaml").is_file())
        if not versions:
            raise FileNotFoundError(f"no bar.yaml under {role_dir}")
        if len(versions) > 1:
            raise ValueError(f"{role_key} has several versions {versions}; name the one you mean")
        version = versions[0]

    path = role_dir / version / "bar.yaml"
    bar = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if bar.get("role_key") != role_key:
        # The directory is how a bar is located; the field is what citations
        # resolve against. Drift between them makes source_refs unresolvable.
        raise ValueError(f"{path}: role_key {bar.get('role_key')!r} != directory {role_key!r}")

    return SkillCanon(
        role_key=role_key,
        version=str(bar.get("version") or version),
        skills=tuple(_sub_skills(bar)),
        depth_scale={int(k): str(v) for k, v in (bar.get("depth_scale") or {}).items()},
        weight_scale={int(k): str(v) for k, v in (bar.get("weight_scale") or {}).items()},
    )
