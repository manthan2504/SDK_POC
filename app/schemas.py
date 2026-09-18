"""Output contracts for agents (RULEBOOK §8).

Every agent returns exactly one object whose class derives from `AgentSchema`.
`check_schema_rules()` enforces the §8 rules on the JSON Schema that is sent to
the model, so a rule break fails a test instead of reaching a live call.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# JSON-Schema keywords the model contract may not use (bounds live in Pydantic
# validators after parsing, never in the schema sent to the model).
BANNED_KEYWORDS = frozenset(
    {
        "pattern",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "maxItems",
        "uniqueItems",
        "allOf",
        "oneOf",
        "not",
        "const",  # single-value Literal: stripped by some transforms, so meaningless to send
        "default",  # defaults change what the model is told; fields are required-and-nullable
    }
)

# A node is "typed" if it carries one of these; anything else is an untyped `Any`.
_TYPED_KEYS = ("type", "anyOf", "$ref", "enum")


class AgentSchema(BaseModel):
    """Base for every agent output: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


def check_schema_rules(model: type[BaseModel]) -> list[str]:
    """Return every §8 violation in `model`'s JSON Schema (empty list = compliant)."""
    schema = model.model_json_schema()
    defs: dict[str, Any] = schema.get("$defs", {})
    problems: list[str] = []

    if not issubclass(model, AgentSchema):
        problems.append(f"{model.__name__}: must derive from AgentSchema")

    def refs_in(node: Any) -> set[str]:
        found: set[str] = set()
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                found.add(ref.rsplit("/", 1)[-1])
            for value in node.values():
                found |= refs_in(value)
        elif isinstance(node, list):
            for item in node:
                found |= refs_in(item)
        return found

    def walk(node: Any, where: str) -> None:
        if isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{where}[{i}]")
            return
        if not isinstance(node, dict):
            return
        for key in node.keys() & BANNED_KEYWORDS:
            problems.append(f"{where}: banned keyword '{key}'")
        if node.get("minItems", 0) > 1:
            problems.append(f"{where}: minItems > 1")
        for key, value in node.items():
            if key == "properties":
                for prop, sub in value.items():
                    if isinstance(sub, dict) and not any(k in sub for k in _TYPED_KEYS):
                        problems.append(f"{where}.{prop}: untyped (Any) field")
                    walk(sub, f"{where}.{prop}")
            elif key != "$defs":
                walk(value, f"{where}.{key}")

    def check_object(obj: dict[str, Any], name: str) -> None:
        props = list(obj.get("properties", {}))
        if not props or props[0] != "analysis":
            problems.append(f"{name}: first field must be 'analysis' (reasoning first)")
        if obj.get("additionalProperties") is not False:
            problems.append(f"{name}: additionalProperties must be false (extra='forbid')")
        missing = set(props) - set(obj.get("required", []))
        if missing:
            problems.append(f"{name}: fields must be required (no defaults): {sorted(missing)}")

    check_object(schema, model.__name__)
    walk(schema, model.__name__)
    for def_name, def_schema in defs.items():
        if def_schema.get("type") != "object":
            continue  # enums etc.
        check_object(def_schema, def_name)
        walk(def_schema, def_name)
        # One level of nesting max: a nested object may not reference another object.
        nested = [r for r in refs_in(def_schema) if defs.get(r, {}).get("type") == "object"]
        if nested:
            problems.append(f"{def_name}: nests further objects {nested} (max one level)")

    return problems


# ---------------------------------------------------------------------------
# [1] Profiler contract (CW-1 + CW-4 style). Flat on purpose: roles, projects and
# skill claims are three lists linked by ids, so nesting stays one level deep.
# Docstrings below are sent to the model as schema descriptions.
# ---------------------------------------------------------------------------
Verdict = Literal["none", "mentioned", "demonstrated", "led"]


class RoleEntry(AgentSchema):
    """One job at one employer, with names and dates copied exactly as written."""

    analysis: str
    role_id: str | None  # "r1", "r2", ... in order of appearance
    employer_raw: str | None
    title_raw: str | None
    start_raw: str | None
    end_raw: str | None  # null when ongoing or not stated
    is_current: bool | None


class ProjectEntry(AgentSchema):
    """One distinct piece of work described under a role. Quotes are copied exactly."""

    analysis: str
    project_id: str | None  # "p1", "p2", ...
    role_id: str | None  # the role it appears under
    name: str | None  # a short label taken from the text
    summary_quote: str | None
    impact_quote: str | None
    hardest_problem_quote: str | None
    stack: list[str] | None  # technologies the text names for this project


class SkillClaim(AgentSchema):
    """What the text shows the candidate did with one technology in one project."""

    analysis: str
    project_id: str | None
    skill: str | None  # as written in the text
    quote: str | None  # the exact phrase that decides the verdict
    verdict: Verdict | None
    confidence: Literal["high", "low"] | None


class ProfileDraft(AgentSchema):
    """The career history one resume states, for the candidate to review."""

    analysis: str
    stated_years_raw: str | None  # the candidate's own statement, e.g. "6 years"
    roles: list[RoleEntry]
    projects: list[ProjectEntry]
    skills: list[SkillClaim]


# ---------------------------------------------------------------------------
# Example contract used by the Step 1 probe agent (not a Caliber agent).
# ---------------------------------------------------------------------------
class ProbeQuestion(AgentSchema):
    """One interview question about a topic — proves the run_agent() plumbing."""

    analysis: str  # one or two sentences: what the topic is and what to ask about
    topic: str | None  # the topic as understood; null if the input is not a topic
    question: str | None  # one open-ended question; null if no sensible question exists
    difficulty: Literal["easy", "medium", "hard"] | None
