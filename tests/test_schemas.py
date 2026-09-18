from typing import Any, Literal

import pytest
from pydantic import BaseModel, Field, ValidationError

from app.schemas import AgentSchema, ProbeQuestion, check_schema_rules


def test_probe_question_follows_the_rules():
    assert check_schema_rules(ProbeQuestion) == []


def test_probe_question_accepts_nulls_and_rejects_extras():
    ok = ProbeQuestion.model_validate(
        {"analysis": "Not a topic.", "topic": None, "question": None, "difficulty": None}
    )
    assert ok.question is None
    with pytest.raises(ValidationError):
        ProbeQuestion.model_validate(
            {"analysis": "x", "topic": None, "question": None, "difficulty": None, "extra": 1}
        )


def test_probe_question_requires_every_key():
    with pytest.raises(ValidationError):
        ProbeQuestion.model_validate({"analysis": "x", "topic": None})


def test_probe_question_rejects_unknown_difficulty():
    with pytest.raises(ValidationError):
        ProbeQuestion.model_validate(
            {"analysis": "x", "topic": "t", "question": "q", "difficulty": "impossible"}
        )


# --- each rule is caught -----------------------------------------------------
def _problems(model: type[BaseModel]) -> str:
    return " | ".join(check_schema_rules(model))


def test_must_derive_from_agent_schema():
    class Plain(BaseModel):
        analysis: str

    assert "must derive from AgentSchema" in _problems(Plain)


def test_analysis_must_come_first():
    class Late(AgentSchema):
        verdict: str
        analysis: str

    assert "first field must be 'analysis'" in _problems(Late)


def test_defaults_are_rejected():
    class WithDefault(AgentSchema):
        analysis: str
        note: str | None = None

    problems = _problems(WithDefault)
    assert "banned keyword 'default'" in problems
    assert "must be required" in problems


def test_length_bounds_are_rejected():
    class Bounded(AgentSchema):
        analysis: str
        quote: str = Field(max_length=300)

    assert "banned keyword 'maxLength'" in _problems(Bounded)


def test_untyped_any_is_rejected():
    class Loose(AgentSchema):
        analysis: str
        blob: Any

    assert "untyped (Any)" in _problems(Loose)


def test_single_value_literal_is_rejected():
    class Const(AgentSchema):
        analysis: str
        kind: Literal["only"]

    assert "banned keyword 'const'" in _problems(Const)


def test_min_items_above_one_is_rejected():
    class Many(AgentSchema):
        analysis: str
        items: list[str] = Field(min_length=2)

    assert "minItems > 1" in _problems(Many)


def test_nested_object_needs_analysis_and_forbid():
    class Inner(BaseModel):
        name: str

    class Outer(AgentSchema):
        analysis: str
        inner: Inner

    problems = _problems(Outer)
    assert "Inner: first field must be 'analysis'" in problems
    assert "Inner: additionalProperties must be false" in problems


def test_one_level_of_nesting_only():
    class Leaf(AgentSchema):
        analysis: str

    class Middle(AgentSchema):
        analysis: str
        leaf: Leaf

    class Root(AgentSchema):
        analysis: str
        middle: Middle

    assert "max one level" in _problems(Root)


def test_one_level_of_nesting_is_fine():
    class Item(AgentSchema):
        analysis: str
        name: str | None

    class Root(AgentSchema):
        analysis: str
        items: list[Item]

    assert check_schema_rules(Root) == []
