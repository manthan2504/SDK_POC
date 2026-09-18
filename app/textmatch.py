"""Grounded-or-dropped: is a quote really in the candidate's text? (RULEBOOK §5, §13)

Both sides are normalised the same way so harmless differences (smart quotes,
dash styles, line breaks, case) don't reject a genuine quote — but anything the
text does not contain is rejected. Never fuzzy-accept.
"""

import re
import unicodedata

_QUOTE_MAP = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "‚": "'",
        "′": "'",
        "´": "'",
        "“": '"',
        "”": '"',
        "„": '"',
        "″": '"',
    }
)
_DASHES = re.compile("[‐‑‒–—―−]")
_HYPHEN_BREAK = re.compile(r"(\w)-[ \t]*\r?\n[ \t]*(\w)")
_SPACE = re.compile(r"\s+")


def normalise_for_match(text: str) -> str:
    t = unicodedata.normalize("NFKC", text)
    # fence() escapes angle brackets; a model may copy the escaped form back.
    t = t.replace("\\u003c", "<").replace("\\u003e", ">")
    t = t.translate(_QUOTE_MAP)
    t = _DASHES.sub("-", t)
    t = _HYPHEN_BREAK.sub(r"\1\2", t)  # re-join words split across a line break
    t = _SPACE.sub(" ", t).strip()
    return t.casefold()


class GroundingText:
    """The candidate's material, normalised once, for repeated verbatim checks."""

    def __init__(self, *sources: str) -> None:
        self._norm = normalise_for_match("\n".join(s for s in sources if s))

    def contains(self, needle: str | None) -> bool:
        """True only for a non-empty needle found verbatim. None/empty never counts."""
        if not needle:
            return False
        n = normalise_for_match(needle)
        return bool(n) and n in self._norm


def mentions(text: str | None, term: str | None) -> bool:
    """Does `text` contain `term` (same normalisation)?"""
    if not text or not term:
        return False
    t = normalise_for_match(term)
    return bool(t) and t in normalise_for_match(text)
