"""Vague skill terms: "cloud technologies" is not a skill (ARITHMETIC_RULES §3).

A vague term is never recorded as a skill; the app asks the candidate which specific
tools they mean instead. Word lists live in `app.policy`; a few real tools that look
vague ("etcd", "Sketch") are exempted by KNOWN_TOOLS.
"""

import re
import string

from app import policy

_SPACE = re.compile(r"\s+")
_TOKEN = re.compile(r"[a-z0-9']+")
_EDGE = string.punctuation + string.whitespace


def normalise_term(term: str | None) -> str:
    """Lowercase, whitespace collapsed, surrounding punctuation stripped."""
    if not term:
        return ""
    return _SPACE.sub(" ", term.lower()).strip(_EDGE)


def is_vague_skill(term: str | None) -> bool:
    """True when the term is too general to count as a skill."""
    t = normalise_term(term)
    if not t:
        return False
    if t in policy.KNOWN_TOOLS:
        return False
    if t in policy.VAGUE_WHOLE:
        return True
    if any(tok in policy.VAGUE_TOKENS for tok in _TOKEN.findall(t)):
        return True
    return any(
        re.search(r"(?<![a-z0-9'])" + re.escape(p) + r"(?![a-z0-9'])", t) for p in policy.VAGUE_PHRASES
    )


def vague_reason(term: str | None) -> str:
    """Candidate-facing sentence asking for the specific tools ("" when not vague)."""
    if not is_vague_skill(term):
        return ""
    shown = _SPACE.sub(" ", term or "").strip(_EDGE)
    return f"'{shown}' is too general to assess — which specific tools or services?"
