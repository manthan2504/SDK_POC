"""CW-2 elicitation: the code decides WHICH gaps, the model only phrases them.

The eval gate Caliber names is the invented-demand rate. `_verify()` is where it
is held at zero, so most of these tests are about what the model is *not*
allowed to change.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date

import pytest

from app.agents.base import LLMCallsDisabled, build_options
from app.agents.elicitor import (
    ELICITOR,
    MAX_GAPS_PER_CALL,
    build_user_prompt,
    gaps_to_ask,
    run_elicitor,
)
from app.candidate_profile import MissingField, build_profile
from app.config import DATA_DIR, HAIKU, LLM_GATE_ENV
from app.schemas import Elicitation, ProfileDraft, check_schema_rules
from tests.fakes import FakeQuery, make_result

FIXTURES = DATA_DIR / "fixtures"
TODAY = date(2026, 9, 21)


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def allow_llm(monkeypatch):
    monkeypatch.setenv(LLM_GATE_ENV, "1")


@pytest.fixture
def profile():
    resume = (FIXTURES / "ravi_resume.txt").read_text(encoding="utf-8")
    draft = ProfileDraft.model_validate_json(
        (FIXTURES / "ravi_draft_example.json").read_text(encoding="utf-8")
    )
    return build_profile(draft, [resume], today=TODAY)


def reply(questions: list[dict], opening: str | None = "Three quick questions."):
    return make_result(structured_output={
        "analysis": "gaps phrased", "opening": opening, "questions": questions,
    })


def phrased(key, question="How big was it?", analysis="because"):
    return {"analysis": analysis, "key": key, "question": question}


def gap(key, question="template wording?", required=True, reason="missing"):
    return MissingField(key=key, question=question, required=required, reason=reason)


# --- the code owns which gaps --------------------------------------------
def test_required_gaps_are_asked_before_nudges(profile):
    gaps = gaps_to_ask(profile, limit=MAX_GAPS_PER_CALL)
    required = [g for g in gaps if g.required]
    assert gaps[:len(required)] == required


def test_the_round_is_capped(profile):
    assert len(gaps_to_ask(profile, limit=3)) == 3


def test_a_profile_with_no_gaps_cannot_be_asked_about(profile):
    complete = profile.model_copy(update={"missing_fields": []})
    with pytest.raises(ValueError, match="no gaps"):
        build_user_prompt(gaps_to_ask(complete), complete)


def test_too_many_gaps_for_one_round_is_refused(profile):
    many = [gap(f"project:p{i}:impact") for i in range(MAX_GAPS_PER_CALL + 1)]
    with pytest.raises(ValueError, match="limit for one round"):
        build_user_prompt(many, profile)


# --- the model owns only the wording -------------------------------------
def test_the_models_wording_is_used(allow_llm, profile):
    """Wording that genuinely asks the field is kept as the model wrote it.

    The template text is valid by construction, so the fake returns it with a
    marker: what is under test is whose wording survives, not the words.
    """
    gaps = gaps_to_ask(profile, limit=2)
    fake = FakeQuery([reply([phrased(g.key, f"{g.question} (reworded)") for g in gaps])])
    out = run(run_elicitor(profile, limit=2, query_fn=fake))

    assert all(q.question.endswith("(reworded)") for q in out.questions)
    assert all(q.source == "model" for q in out.questions)
    assert out.fell_back == []


def test_a_question_for_a_gap_we_never_found_is_dropped(allow_llm, profile):
    """Invented demand: the model asking for something the code did not ask for."""
    gaps = gaps_to_ask(profile, limit=1)
    fake = FakeQuery([reply([
        phrased(gaps[0].key),
        phrased("project:p99:salary", "What is your current salary?"),
    ])])
    out = run(run_elicitor(profile, limit=1, query_fn=fake))

    assert [q.key for q in out.questions] == [gaps[0].key]
    assert out.invented == ["project:p99:salary"]
    assert "salary" not in json.dumps([q.question for q in out.questions])


def test_a_gap_the_model_skipped_keeps_its_template_wording(allow_llm, profile):
    """The candidate is still asked — a skipped gap must not vanish."""
    gaps = gaps_to_ask(profile, limit=2)
    fake = FakeQuery([reply([phrased(gaps[0].key, f"{gaps[0].question} (reworded)")])])
    out = run(run_elicitor(profile, limit=2, query_fn=fake))

    assert len(out.questions) == 2
    assert out.questions[1].question == gaps[1].question  # the template
    assert out.questions[1].phrased is False
    assert out.fell_back == [gaps[1].key]


def test_an_empty_question_falls_back_to_the_template(allow_llm, profile):
    gaps = gaps_to_ask(profile, limit=1)
    fake = FakeQuery([reply([phrased(gaps[0].key, "   ")])])
    out = run(run_elicitor(profile, limit=1, query_fn=fake))
    assert out.questions[0].question == gaps[0].question
    assert out.questions[0].source == "template"


def test_a_null_key_cannot_replace_a_gap(allow_llm, profile):
    gaps = gaps_to_ask(profile, limit=1)
    fake = FakeQuery([reply([{"analysis": "x", "key": None, "question": "anything?"}])])
    out = run(run_elicitor(profile, limit=1, query_fn=fake))
    assert out.questions[0].question == gaps[0].question


def test_required_and_reason_come_from_the_code_not_the_model(allow_llm, profile):
    gaps = gaps_to_ask(profile, limit=3)
    fake = FakeQuery([reply([phrased(g.key) for g in gaps])])
    out = run(run_elicitor(profile, limit=3, query_fn=fake))
    assert [q.required for q in out.questions] == [g.required for g in gaps]
    assert [q.reason for q in out.questions] == [g.reason for g in gaps]


def test_the_opening_line_is_carried_through(allow_llm, profile):
    gaps = gaps_to_ask(profile, limit=1)
    fake = FakeQuery([reply([phrased(gaps[0].key)], opening="Two quick questions.")])
    assert run(run_elicitor(profile, limit=1, query_fn=fake)).opening == "Two quick questions."


# --- the request ---------------------------------------------------------
def test_the_prompt_fences_the_gaps(profile):
    prompt = build_user_prompt(gaps_to_ask(profile, limit=2), profile)
    assert prompt.startswith('<gaps source="candidate" trust="untrusted">')


def test_each_gap_carries_the_candidates_own_words(profile):
    """Without context the model writes "your second project"."""
    project_gap = next(g for g in profile.missing_fields if g.key.startswith("project:"))
    prompt = build_user_prompt([project_gap], profile)
    body = json.loads(prompt[prompt.index(">") + 1: prompt.rindex("</gaps>")]
                      .replace("\\u003c", "<").replace("\\u003e", ">"))
    sent = body["gaps"][0]
    assert sent["key"] == project_gap.key
    assert sent["reason"] == project_gap.reason
    assert sent["context"].get("project")


def test_a_thin_answer_is_sent_with_what_the_candidate_wrote(profile):
    """`thin` means they answered too briefly; asking again from scratch is rude."""
    project = profile.projects[0]
    thin = gap(f"project:{project.project_id}:summary", reason="thin")
    prompt = build_user_prompt([thin], profile)
    if project.summary:
        assert "wrote" in prompt


def test_the_prompt_never_carries_the_whole_profile(profile):
    """Only what each gap needs — the resume itself is not re-sent."""
    prompt = build_user_prompt(gaps_to_ask(profile, limit=2), profile)
    assert "policy_version" not in prompt
    assert "grounding" not in prompt


# --- the spec ------------------------------------------------------------
def test_the_spec_matches_the_capability_mapping():
    assert ELICITOR.model == HAIKU  # CW-2: Haiku 4.5, no effort
    assert ELICITOR.effort is None
    assert ELICITOR.cw == "cw-2"
    assert ELICITOR.prompt.label == "elicitation.v2"
    assert ELICITOR.tool_names == ()


def test_the_options_are_lean_and_isolated():
    options = build_options(ELICITOR)
    assert options.tools == [] and options.setting_sources == [] and options.allowed_tools == []


def test_the_output_schema_obeys_the_rules():
    assert check_schema_rules(Elicitation) == []


def test_it_refuses_to_run_without_the_gate(profile):
    with pytest.raises(LLMCallsDisabled):
        run(run_elicitor(profile, query_fn=FakeQuery([reply([])])))


# --- v2: the question must still ask for what the field needs -------------
# Every case below is taken from the live run of 2026-09-21 (RULEBOOK §16.4),
# where the key was right and the question asked for something else.


@pytest.mark.parametrize(
    "key, expected",
    [
        ("role:r1:context", "context"),
        ("project:p1:impact", "impact"),
        ("project:p1:impact:quantify", "impact:quantify"),
        ("project:p1:hardest_problem:decision", "hardest_problem:decision"),
        ("project:p1:vague:cloud technologies", "vague"),
        ("project:p2:processes", "processes"),
        ("role:r1:employer", "employer"),
    ],
)
def test_the_field_is_read_from_the_key(key, expected):
    from app.agents.elicitor import field_of

    assert field_of(key) == expected


@pytest.mark.parametrize(
    "field, question",
    [
        # the three that drifted in the live run
        ("context", "What was your focus area — backend, frontend, full stack, or data?"),
        ("processes", "What key processes did the invoice system change or automate?"),
        ("hardest_problem", "What was the hardest problem you faced, and how did you solve it?"),
        # and the shapes they could drift into
        ("impact", "Tell me more about the rewards project."),
        ("scale", "What technologies did you use on it?"),
    ],
)
def test_a_question_that_asks_for_something_else_is_rejected(field, question):
    from app.agents.elicitor import asks_for

    assert not asks_for(question, field)


@pytest.mark.parametrize(
    "field, question",
    [
        ("context", "Was the role full-time, part-time or contract, how big was the team, and did you lead anyone?"),
        ("processes", "How did you work on it — design review, code review, on-call, agile?"),
        ("hardest_problem", "What was the hardest call you had to make, and which way did you go?"),
        ("impact", "What changed measurably — a time, a rate, or a cost?"),
        ("scale", "How many users did it serve, and what data volume?"),
        ("employer", "Which company was that role with?"),
    ],
)
def test_a_question_that_asks_for_the_field_is_kept(field, question):
    from app.agents.elicitor import asks_for

    assert asks_for(question, field)


def test_a_field_with_no_listed_terms_is_not_second_guessed():
    from app.agents.elicitor import asks_for

    assert asks_for("anything at all", "a_field_we_have_no_rule_for")


def test_a_drifted_question_falls_back_to_the_template(allow_llm, profile):
    """The live failure, end to end: right key, wrong question, template shown."""
    context_gap = next(g for g in profile.missing_fields if g.key.endswith(":context"))
    fake = FakeQuery([reply([phrased(context_gap.key, "What was your focus area?")])])
    out = run(run_elicitor(profile, limit=1, query_fn=FakeQuery([reply(
        [phrased(g.key, "What was your focus area?") for g in gaps_to_ask(profile, limit=1)]
    )])))

    asked = out.questions[0]
    if asked.key.endswith(":context"):
        assert asked.source == "template"
        assert "does not ask for context" in asked.refused


def test_the_gap_purpose_is_sent_to_the_model(profile):
    """`answer_must_give` is the whole fix: the model was never told what a
    usable answer contains, so it invented a reasonable question for the wrong thing."""
    context_gap = next(g for g in profile.missing_fields if g.key.endswith(":context"))
    prompt = build_user_prompt([context_gap], profile)
    body = json.loads(prompt[prompt.index(">") + 1: prompt.rindex("</gaps>")]
                      .replace("\u003c", "<").replace("\u003e", ">"))
    must_give = body["gaps"][0]["answer_must_give"]
    assert "full-time" in must_give and "team" in must_give and "led anyone" in must_give


def test_every_purpose_has_an_acceptance_check():
    """The two halves must agree — one describes the answer, the other tests for it."""
    from app.policy import FIELD_ASK_TERMS, FIELD_PURPOSE

    assert sorted(FIELD_PURPOSE) == sorted(FIELD_ASK_TERMS)

