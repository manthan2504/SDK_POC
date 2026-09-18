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
