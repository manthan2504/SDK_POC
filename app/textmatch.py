"""Grounded-or-dropped: is a quote really in the candidate's text? (RULEBOOK §5, §13)

Both sides are normalised the same way so harmless differences (smart quotes,
dash styles, line breaks, case) don't reject a genuine quote — but anything the
text does not contain is rejected. Never fuzzy-accept.
"""

import re
import unicodedata

from app.policy import SHORT_NEEDLE_CHARS

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


# Joins sources so no needle can span two of them. U+241E (SYMBOL FOR RECORD
# SEPARATOR) is a visible symbol: NFKC and casefold leave it unchanged, it is not
# whitespace (so the space-collapse keeps it), and any needle that contains it
# is refused outright, so a match can never cross from one source into the next.
SOURCE_SEPARATOR = " ␞ "
_SEP_CHAR = SOURCE_SEPARATOR.strip()


def _term_pattern(norm_term: str) -> re.Pattern[str]:
    """Whole-term pattern: no word character directly before or after."""
    return re.compile(r"(?<!\w)" + re.escape(norm_term) + r"(?!\w)")


def _find_term(norm_text: str, norm_term: str) -> bool:
    return bool(norm_term) and _SEP_CHAR not in norm_term and _term_pattern(norm_term).search(norm_text) is not None


class GroundingText:
    """The candidate's material, normalised once, for repeated verbatim checks."""

    def __init__(self, *sources: str) -> None:
        self._norm = SOURCE_SEPARATOR.join(n for n in (normalise_for_match(s) for s in sources if s) if n)

    def contains(self, needle: str | None) -> bool:
        """True only for a non-empty needle found verbatim. None/empty never counts.
        Needles of SHORT_NEEDLE_CHARS or fewer must stand as a whole term ("Go" is
        not in "ago"); longer needles are plain substrings. Never spans two sources."""
        if not needle:
            return False
        n = normalise_for_match(needle)
        if not n or _SEP_CHAR in n:
            return False
        if len(n) <= SHORT_NEEDLE_CHARS:
            return _find_term(self._norm, n)
        return n in self._norm

    def contains_term(self, term: str | None) -> bool:
        """True only if `term` occurs as a whole term (word boundaries both sides):
        "SQL" is not in "PostgreSQL", but "C++" / ".NET" / "Node.js" match where
        written. None/empty never counts."""
        if not term:
            return False
        return _find_term(self._norm, normalise_for_match(term))


def mentions(text: str | None, term: str | None) -> bool:
    """Does `text` contain `term` as a whole term (same normalisation)?"""
    if not text or not term:
        return False
    return _find_term(normalise_for_match(text), normalise_for_match(term))
