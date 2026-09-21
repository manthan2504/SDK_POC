"""Text-quality ladder: how much does a free-text answer actually say? (RULEBOOK §9)

Caliber's ladder (reference/plan/ARITHMETIC_RULES.md §2), simplified for the POC —
no bigram language model. Every answer lands on one tier:

    empty < noise < thin < substantive < specific

The completeness gate needs >= substantive; "specific" is the non-gating refinement
(impact names a number, hardest problem names a decision). Every threshold and word
list comes from `app.policy`; nothing role-specific lives here (FR-I5).
"""

import re
from dataclasses import dataclass
from typing import Literal

from app import policy

Tier = Literal["empty", "noise", "thin", "substantive", "specific"]

_TOKEN = re.compile(r"[A-Za-z0-9']+")
_SPACE = re.compile(r"\s+")
_VOWELS = set("aeiouy")
# A run of WORDLIKE_MAX_CONSONANT_RUN+ letters that are not aeiouy.
_CONSONANT_RUN = re.compile(r"[b-df-hj-np-tv-xz]{%d,}" % policy.WORDLIKE_MAX_CONSONANT_RUN)
# A letter repeated REPEAT_RUN_LIMIT+ times in a row ("aaaa", "zzzzz"). Letters only:
# digit runs ("1000000") and ellipses ("....") are legitimate in real answers.
_REPEAT_RUN = re.compile(r"([A-Za-z])\1{%d,}" % (policy.REPEAT_RUN_LIMIT - 1), re.IGNORECASE)

# Order in which project fields are compared for near-duplicates (scale excluded).
_DUP_ORDER = ("summary", "responsibilities", "impact", "hardest_problem")
_PROJECT_FIELDS = (*_DUP_ORDER, "scale")


@dataclass(frozen=True)
class TextRead:
    """One read of one answer: its tier, a candidate-facing reason, and flags."""

    tier: Tier
    reason: str
    flags: frozenset[str]
    words: int


def tier_rank(tier: Tier) -> int:
    """Position on the ladder (empty 0 … specific 4)."""
    return policy.TIERS.index(tier)


def at_least(tier: Tier, floor: Tier) -> bool:
    """Is `tier` at or above `floor`?"""
    return tier_rank(tier) >= tier_rank(floor)


def tokens(text: str | None) -> list[str]:
    """Word tokens (`[A-Za-z0-9']+`), original case."""
    return _TOKEN.findall(text or "")


def is_wordlike(token: str) -> bool:
    """Does a token look like a real word, number or acronym?"""
    if any(c.isdigit() for c in token):
        return True
    if token.isupper() and len(token) <= policy.ACRONYM_MAX_CHARS:
        return True  # acronym: AWS, ECS, REST, API
    # Everything else, Title-case included, must look pronounceable.
    low = token.lower()
    return any(c in _VOWELS for c in low) and not _CONSONANT_RUN.search(low)


def wordlike_ratio(toks: list[str]) -> float:
    """Share of tokens that look word-like (0.0 for no tokens)."""
    if not toks:
        return 0.0
    return sum(1 for t in toks if is_wordlike(t)) / len(toks)


def _mostly_caps(toks: list[str]) -> bool:
    """All-caps alphabetic tokens (2+ letters) exceed ACRONYM_MAX_SHARE and no token
    has a lowercase letter: a shouted string of "acronyms" is not an answer."""
    caps = sum(1 for t in toks if len(t) >= 2 and t.isalpha() and t.isupper())
    has_lower = any(any(c.islower() for c in t) for t in toks)
    return not has_lower and caps / len(toks) > policy.ACRONYM_MAX_SHARE


def _flat(text: str) -> str:
    """Lowercase, whitespace collapsed — for word/phrase lookups."""
    return _SPACE.sub(" ", text.lower()).strip()


def _has_term(flat: str, term: str) -> bool:
    """Whole-word match of a word or phrase (handles hyphenated terms like 'trade-off')."""
    pattern = r"(?<![a-z0-9'])" + re.escape(term.lower()) + r"(?![a-z0-9'])"
    return re.search(pattern, flat) is not None


def _has_any(flat: str, terms) -> bool:
    return any(_has_term(flat, t) for t in terms)


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def read_text(text: str | None, field: str | None = None) -> TextRead:
    """Place one answer on the ladder. `field` (a key of FIELD_SPECS) enables the
    field's length floor, echo check and specificity rule; unknown or None = generic."""
    if text is None or not text.strip():
        return TextRead("empty", "nothing captured yet", frozenset(), 0)

    toks = tokens(text)
    n = len(toks)
    ratio = wordlike_ratio(toks)
    if n == 0 or _REPEAT_RUN.search(text) or ratio < policy.WORDLIKE_NOISE_RATIO:
        return TextRead("noise", "that doesn't read as a real answer", frozenset(), n)
    if n < policy.MIN_WORDS_ANY:
        return TextRead("noise", f"{_plural(n, 'word')} — too thin to assess", frozenset(), n)
    if _mostly_caps(toks):
        return TextRead("noise", "that doesn't read as a real answer", frozenset(), n)

    spec = policy.FIELD_SPECS.get(field) if field else None
    if spec is not None:
        min_words, min_chars, _, echo = spec
        if n < min_words:
            return TextRead("thin", f"say a bit more ({min_words}+ words)", frozenset(), n)
        if len(text.strip()) < min_chars:
            return TextRead("thin", f"say a bit more ({min_chars}+ characters)", frozenset(), n)
        distinct = {t.lower() for t in toks}
        fresh = distinct - echo
        if len(fresh) * 2 < len(distinct):
            return TextRead("thin", "mostly restates the question", frozenset({"echo"}), n)

    if ratio < policy.WORDLIKE_THIN_RATIO:
        return TextRead("thin", "much of this doesn't read as real words", frozenset({"gibberish"}), n)

    flat = _flat(text)
    if field == "impact":
        quantified = (
            any(c.isdigit() for c in text)
            or any(c in policy.QUANT_SYMBOLS for c in text)
            or _has_any(flat, policy.QUANT_WORDS)
        )
        if quantified:
            return TextRead("specific", "names a measurable result", frozenset({"quantified"}), n)
        return TextRead("substantive", "no number yet", frozenset(), n)

    if field == "hardest_problem":
        causal = _has_any(flat, policy.CAUSAL_WORDS) or _has_any(flat, policy.CAUSAL_PHRASES)
        flags = {"causal"} if causal else set()
        if _has_any(flat, policy.DECISION_WORDS) or _has_any(flat, policy.DECISION_PHRASES):
            return TextRead("specific", "names the decision you made", frozenset(flags | {"decision"}), n)
        return TextRead("substantive", "no decision named yet", frozenset(flags), n)

    return TextRead("substantive", "reads as a real answer", frozenset(), n)


def near_duplicate(a: str | None, b: str | None) -> bool:
    """Jaccard similarity of lowercase token sets >= NEAR_DUP_JACCARD. Empty never matches."""
    sa = {t.lower() for t in tokens(a)}
    sb = {t.lower() for t in tokens(b)}
    if not sa or not sb:
        return False
    return len(sa & sb) / len(sa | sb) >= policy.NEAR_DUP_JACCARD


def read_project_fields(
    fields: dict[str, str | None],
    dedupe_fields: set[str] | frozenset[str] | None = None,
) -> dict[str, TextRead]:
    """Read every project text field present; demote a later field (>= substantive)
    that near-duplicates an earlier one to thin (`duplicate`). Scale is never compared.
    `dedupe_fields` limits demotion to later fields named in it (e.g. only the ones the
    candidate typed); every field still counts as an "earlier" one. None = all fields."""
    reads = {f: read_text(fields[f], f) for f in _PROJECT_FIELDS if f in fields}
    seen: list[str] = []
    for f in _DUP_ORDER:
        if f not in fields:
            continue
        r = reads[f]
        if at_least(r.tier, "substantive") and (dedupe_fields is None or f in dedupe_fields):
            for earlier in seen:
                if near_duplicate(fields[f], fields[earlier]):
                    reads[f] = TextRead(
                        "thin",
                        f"repeats the {earlier.replace('_', ' ')} answer almost word for word",
                        frozenset({"duplicate"}),
                        r.words,
                    )
                    break
        seen.append(f)
    return reads
