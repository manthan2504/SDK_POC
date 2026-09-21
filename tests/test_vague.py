"""Offline tests for vague skill terms (app/vague.py)."""

import pytest

from app import policy
from app.vague import is_vague_skill, normalise_term, vague_reason


@pytest.mark.parametrize("term", sorted(policy.VAGUE_WHOLE))
def test_every_whole_term_is_vague(term):
    assert is_vague_skill(term)


@pytest.mark.parametrize(
    "term",
    ["Figma tools", "Python, etc", "misc scripts", "various AWS services", "big data technologies"],
)
def test_vague_token_anywhere(term):
    assert is_vague_skill(term)


@pytest.mark.parametrize("term", ["Docker and more", "Kafka and others", "AWS (EC2, S3 and more)"])
def test_vague_phrase(term):
    assert is_vague_skill(term)


@pytest.mark.parametrize("term", ["etcd", "Sketch", "  SKETCH  ", "Fetch API", "prefetch", "etcd."])
def test_known_tools_are_exempt(term):
    assert not is_vague_skill(term)


@pytest.mark.parametrize(
    "term",
    ["PostgreSQL", "AWS ECS", "Kafka", "React", "Kubernetes", "LangChain", "commandmore", "sketchbook"],
)
def test_real_tools_are_not_vague(term):
    assert not is_vague_skill(term)


@pytest.mark.parametrize(
    "term",
    ["Cloud Technologies", "  cloud   technologies  ", "cloud\ttechnologies.", "(DevOps)", '"Analytics"', "ETC."],
)
def test_normalisation(term):
    assert is_vague_skill(term)


@pytest.mark.parametrize("term", [None, "", "   ", "..."])
def test_empty_is_not_vague(term):
    assert not is_vague_skill(term)


def test_normalise_term():
    assert normalise_term("  Cloud   Technologies. ") == "cloud technologies"
    assert normalise_term(None) == ""


def test_vague_reason():
    assert vague_reason("  cloud technologies ") == (
        "'cloud technologies' is too general to assess — which specific tools or services?"
    )


def test_vague_reason_keeps_candidate_casing():
    assert vague_reason("Various Tools.").startswith("'Various Tools' is too general")


@pytest.mark.parametrize("term", ["Kafka", "etcd", None, ""])
def test_vague_reason_empty_when_not_vague(term):
    assert vague_reason(term) == ""
