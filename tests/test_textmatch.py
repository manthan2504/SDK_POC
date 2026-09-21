from app.textmatch import GroundingText, mentions, normalise_for_match


def test_normalise_unifies_quotes_dashes_space_and_case():
    assert normalise_for_match("Clinicians’  Policy\n— Q&A") == "clinicians' policy - q&a"


def test_normalise_rejoins_words_broken_across_lines():
    assert normalise_for_match("recom-\nmendation engine") == "recommendation engine"


def test_normalise_keeps_spaced_hyphens():
    assert normalise_for_match("2019 -\n2021") == "2019 - 2021"


def test_normalise_accepts_fence_escaped_angle_brackets():
    assert normalise_for_match("\\u003c5 years") == "<5 years"


def test_grounding_accepts_harmless_differences():
    text = GroundingText("Built a RAG assistant that answers clinicians' policy questions")
    assert text.contains("built a RAG assistant that answers clinicians’ policy")


def test_grounding_rejects_anything_not_in_the_text():
    text = GroundingText("Built a RAG assistant")
    assert not text.contains("Built a RAG agent")
    assert not text.contains("Led the RAG assistant")


def test_none_or_empty_is_never_grounded():
    text = GroundingText("anything")
    assert not text.contains(None)
    assert not text.contains("")
    assert not text.contains("   ")


def test_grounding_spans_all_sources():
    text = GroundingText("resume text here", "an answer: cut latency by 60%")
    assert text.contains("cut latency by 60%")


def test_mentions():
    assert mentions("caching embeddings (Redis)", "redis")
    assert not mentions("caching embeddings", "Redis")
    assert not mentions(None, "Redis")


# --- v1.2: word-boundary terms ----------------------------------------------

import pytest  # noqa: E402

from app import policy  # noqa: E402
from app.textmatch import SOURCE_SEPARATOR  # noqa: E402


@pytest.mark.parametrize(
    "text, term",
    [
        ("Ten years of PostgreSQL tuning", "SQL"),
        ("I joined three years ago", "Go"),
        ("Built a RAG assistant for clinicians", "R"),
        ("Lead engineer at Northwind Health", "Health Care"),
        ("Wrote Javascript widgets", "Java"),
    ],
)
def test_contains_term_rejects_matches_inside_words(text, term):
    assert not GroundingText(text).contains_term(term)


@pytest.mark.parametrize(
    "text, term",
    [
        ("Wrote SQL and PostgreSQL daily", "SQL"),
        ("Services in Go and Python", "go"),
        ("Stats in R, plotting in ggplot", "R"),
        ("Engines in C++ for trading", "C++"),
        ("Migrated the API to .NET 8", ".NET"),
        ("Backend in Node.js with Express", "Node.js"),
        ("Models with scikit-learn pipelines", "scikit-learn"),
        ("Worked at Northwind Health", "Northwind Health"),
    ],
)
def test_contains_term_accepts_whole_terms(text, term):
    assert GroundingText(text).contains_term(term)


def test_contains_term_none_or_empty_is_false():
    text = GroundingText("anything")
    assert not text.contains_term(None)
    assert not text.contains_term("")
    assert not text.contains_term("  ")


def test_short_needles_need_word_boundaries():
    assert policy.SHORT_NEEDLE_CHARS == 3
    text = GroundingText("I left three years ago to build Kafka pipelines")
    assert not text.contains("Go")
    assert not text.contains("ild")  # 3 chars, inside "build"
    assert text.contains("to")
    assert text.contains("ago")


def test_longer_needles_stay_substrings():
    text = GroundingText("Tuned PostgreSQL indexes")
    assert text.contains("tgreSQL")  # 7 chars: plain substring


def test_mentions_uses_whole_terms():
    assert not mentions("Ten years of PostgreSQL", "SQL")
    assert not mentions("years ago", "Go")
    assert mentions("SQL and PostgreSQL", "sql")
    assert mentions("engines in C++", "C++")


# --- v1.2: sources never join -----------------------------------------------


def test_needle_cannot_span_two_sources():
    text = GroundingText("resume ends with Python", "I cut costs by 40%")
    assert not text.contains("Python I cut costs")
    assert not text.contains("python\ni cut")
    assert text.contains("resume ends with Python")
    assert text.contains("I cut costs by 40%")


def test_separator_survives_normalisation_and_is_refused_in_needles():
    assert normalise_for_match("a" + SOURCE_SEPARATOR + "b") == "a" + SOURCE_SEPARATOR + "b"
    text = GroundingText("alpha", "beta")
    assert not text.contains("alpha" + SOURCE_SEPARATOR + "beta")
    assert not text.contains(SOURCE_SEPARATOR.strip())
    assert not text.contains_term(SOURCE_SEPARATOR.strip())


def test_empty_sources_are_skipped():
    text = GroundingText("", "only answer", None)  # type: ignore[arg-type]
    assert text.contains("only answer")
