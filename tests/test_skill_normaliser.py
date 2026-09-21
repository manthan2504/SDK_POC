"""CW-3 skill normalise: the canon, retrieval, and the constrained-select gate.

The rule the whole workload rests on: a canon key the model was not offered for
that term never survives. Caliber states the checker as "canon ∈ candidates
(hallucinated canon = 0)".
"""

from __future__ import annotations

import asyncio
import json

import pytest

from app.agents.base import build_options
from app.agents.skill_normaliser import (
    MAX_TERMS_PER_CALL,
    SKILL_NORMALISER,
    build_user_prompt,
    run_skill_normaliser,
)
from app.config import HAIKU, LLM_GATE_ENV
from app.schemas import SkillNormalisation, check_schema_rules
from app.skillcanon import CanonSkill, SkillCanon, load_canon
from tests.fakes import FakeQuery, make_result

ROLE = "senior_ai_engineer"


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def allow_llm(monkeypatch):
    monkeypatch.setenv(LLM_GATE_ENV, "1")


@pytest.fixture
def canon() -> SkillCanon:
    return load_canon(ROLE)


def tiny_canon() -> SkillCanon:
    return SkillCanon(
        role_key="test",
        version="v1",
        skills=(
            CanonSkill("data.sql", "SQL and relational modelling", "data",
                       ("postgresql", "postgres", "mysql")),
            CanonSkill("retrieval.rag_design", "RAG design", "retrieval",
                       ("rag", "retrieval augmented generation")),
        ),
    )


def reply(matches: list[dict], analysis: str = "ok"):
    return make_result(structured_output={"analysis": analysis, "matches": matches})


def match(skill, key, analysis="because", confidence="high"):
    return {"analysis": analysis, "skill": skill, "canon_key": key, "confidence": confidence}


# --- the canon -----------------------------------------------------------
def test_the_canon_loads_from_the_role_bar(canon):
    """D9/FR-I5: role content lives in YAML, never in code."""
    assert canon.role_key == ROLE
    assert canon.version == "v0.1-placeholder"
    assert len(canon.skills) > 10
    assert canon.knows("retrieval.embeddings")


def test_an_unknown_role_is_refused():
    with pytest.raises(FileNotFoundError):
        load_canon("no_such_role")


def test_a_key_outside_the_canon_is_not_known(canon):
    assert not canon.knows("retrieval.invented")
    assert not canon.knows(None)


# --- retrieval -----------------------------------------------------------
def test_an_alias_retrieves_its_skill(canon):
    assert canon.candidates("pgvector")[0].key == "retrieval.embeddings"
    assert canon.candidates("prompt injection")[0].key == "safety.injection"


def test_an_abbreviation_retrieves_its_skill(canon):
    assert canon.candidates("RAG")[0].key == "retrieval.rag_design"


def test_retrieval_is_case_and_space_insensitive(canon):
    assert canon.candidates("  EMBEDDINGS ")[0].key == "retrieval.embeddings"


def test_a_term_the_bar_does_not_cover_retrieves_nothing(canon):
    """This bar is for AI engineering; a Spring backend skill is simply absent."""
    assert canon.candidates("Spring Boot") == []
    assert canon.candidates("Kubernetes") == []


def test_an_empty_term_retrieves_nothing(canon):
    assert canon.candidates("") == []
    assert canon.candidates(None) == []


def test_candidates_are_capped(canon):
    assert len(canon.candidates("design", limit=2)) <= 2


def test_a_term_is_matched_as_a_whole_token_not_a_substring():
    """v1.2's rule, applied to the canon: "SQL" must not be pulled in merely
    because "PostgreSQL" contains those letters."""
    canon = SkillCanon(
        role_key="test", version="v1",
        skills=(CanonSkill("data.relational", "Relational databases", "data", ("postgresql",)),),
    )
    assert canon.candidates("SQL") == []
    assert canon.candidates("PostgreSQL")[0].key == "data.relational"


def test_a_key_segment_counts_as_a_spelling():
    """`data.sql` is named SQL even if no alias says so."""
    assert tiny_canon().candidates("SQL")[0].key == "data.sql"


# --- the constrained-select gate -----------------------------------------
def test_a_key_that_was_offered_is_kept(allow_llm):
    fake = FakeQuery([reply([match("Postgres", "data.sql")])])
    out = run(run_skill_normaliser(["Postgres"], tiny_canon(), query_fn=fake))
    assert out.skills[0].canon_key == "data.sql"
    assert out.skills[0].canon_name == "SQL and relational modelling"
    assert out.refused == []


def test_a_key_from_another_terms_list_is_refused(allow_llm):
    """Borrowing between terms is the failure mode a shared prompt invites."""
    fake = FakeQuery([reply([
        match("Postgres", "data.sql"),
        match("RAG", "data.sql"),  # real key, wrong term
    ])])
    out = run(run_skill_normaliser(["Postgres", "RAG"], tiny_canon(), query_fn=fake))
    rag = next(s for s in out.skills if s.skill == "RAG")
    assert rag.canon_key is None
    assert "was not offered" in rag.rejected


def test_an_invented_key_is_refused(allow_llm):
    fake = FakeQuery([reply([match("Postgres", "data.postgres_expert")])])
    out = run(run_skill_normaliser(["Postgres"], tiny_canon(), query_fn=fake))
    assert out.skills[0].canon_key is None
    assert out.refused


def test_null_is_an_accepted_answer(allow_llm):
    fake = FakeQuery([reply([match("Kubernetes", None, confidence=None)])])
    out = run(run_skill_normaliser(["Kubernetes"], tiny_canon(), query_fn=fake))
    assert out.skills[0].canon_key is None
    assert out.skills[0].rejected is None  # refusing to match is not an error
    assert out.unmatched == ["Kubernetes"]


def test_a_term_the_model_skipped_is_still_reported(allow_llm):
    fake = FakeQuery([reply([match("Postgres", "data.sql")])])
    out = run(run_skill_normaliser(["Postgres", "RAG"], tiny_canon(), query_fn=fake))
    rag = next(s for s in out.skills if s.skill == "RAG")
    assert rag.canon_key is None
    assert rag.rejected == "no answer returned"


def test_a_row_for_a_term_we_never_sent_is_ignored(allow_llm):
    fake = FakeQuery([reply([match("Postgres", "data.sql"), match("Rust", "data.sql")])])
    out = run(run_skill_normaliser(["Postgres"], tiny_canon(), query_fn=fake))
    assert [s.skill for s in out.skills] == ["Postgres"]


def test_every_result_records_what_was_offered(allow_llm):
    fake = FakeQuery([reply([match("Postgres", "data.sql")])])
    out = run(run_skill_normaliser(["Postgres"], tiny_canon(), query_fn=fake))
    assert out.skills[0].offered == ("data.sql",)


# --- the request ---------------------------------------------------------
def test_the_prompt_fences_the_terms():
    canon = tiny_canon()
    prompt = build_user_prompt({"Postgres": canon.candidates("Postgres")})
    assert prompt.startswith('<terms source="candidate" trust="untrusted">')
    assert "data.sql" in prompt


def test_each_term_is_sent_with_its_own_candidates():
    canon = tiny_canon()
    prompt = build_user_prompt({t: canon.candidates(t) for t in ("Postgres", "RAG")})
    body = json.loads(prompt[prompt.index(">") + 1: prompt.rindex("</terms>")]
                      .replace("\\u003c", "<").replace("\\u003e", ">"))
    offered = {t["skill"]: [c["key"] for c in t["candidates"]] for t in body["terms"]}
    assert offered == {"Postgres": ["data.sql"], "RAG": ["retrieval.rag_design"]}


def test_duplicate_terms_are_asked_about_once(allow_llm):
    fake = FakeQuery([reply([match("Postgres", "data.sql")])])
    out = run(run_skill_normaliser(["Postgres", "Postgres"], tiny_canon(), query_fn=fake))
    assert len(out.skills) == 1


def test_an_empty_term_list_is_refused(allow_llm):
    with pytest.raises(ValueError):
        run(run_skill_normaliser([], tiny_canon()))


def test_too_many_terms_for_one_call_is_refused():
    canon = tiny_canon()
    with pytest.raises(ValueError, match="split into calls"):
        build_user_prompt({f"skill{i}": canon.candidates("x") for i in range(MAX_TERMS_PER_CALL + 1)})


# --- the spec ------------------------------------------------------------
def test_the_spec_matches_the_capability_mapping():
    assert SKILL_NORMALISER.model == HAIKU  # CW-3: "frontier spend buys nothing measurable"
    assert SKILL_NORMALISER.effort is None  # Haiku rejects effort
    assert SKILL_NORMALISER.cw == "cw-3"
    assert SKILL_NORMALISER.prompt.label == "skill_normalise.v1"
    assert SKILL_NORMALISER.tool_names == ()


def test_the_options_are_lean_and_isolated():
    options = build_options(SKILL_NORMALISER)
    assert options.tools == [] and options.setting_sources == [] and options.allowed_tools == []


def test_the_output_schema_obeys_the_rules():
    assert check_schema_rules(SkillNormalisation) == []


def test_it_refuses_to_run_without_the_gate():
    from app.agents.base import LLMCallsDisabled

    with pytest.raises(LLMCallsDisabled):
        run(run_skill_normaliser(["Postgres"], tiny_canon(), query_fn=FakeQuery([reply([])])))


# --- the bar's own shape: aliases vs tools, the scales, collisions ---------
def tooled_canon() -> SkillCanon:
    return SkillCanon(
        role_key="test", version="v1",
        skills=(
            CanonSkill("retrieval.embeddings", "Embedding trade-offs", "retrieval",
                       aliases=("embeddings", "embedding"),
                       tools=("pgvector", "bge")),
            CanonSkill("data.sql", "SQL", "data", aliases=("postgresql",), tools=()),
        ),
    )


def test_a_tool_and_an_alias_are_told_apart():
    """"pgvector" is not another word for judging embedding trade-offs — it is a
    thing you might have used without ever making one."""
    canon = tooled_canon()
    named = canon.candidates("embeddings")[0]
    tooled = canon.candidates("pgvector")[0]
    assert named.key == tooled.key == "retrieval.embeddings"
    assert named.via == "alias" and named.names_the_skill
    assert tooled.via == "tool" and not tooled.names_the_skill


def test_naming_the_skill_outranks_naming_a_tool():
    """Both hit the same skill, so the ordering only matters when they compete."""
    from app.skillcanon import TOOL_MATCH_CEILING

    canon = SkillCanon(
        role_key="test", version="v1",
        skills=(
            CanonSkill("a.named", "Thing A", "a", aliases=("kafka",), tools=()),
            CanonSkill("b.tooled", "Thing B", "b", aliases=(), tools=("kafka",)),
        ),
    )
    ranked = canon.candidates("kafka")
    assert [c.key for c in ranked] == ["a.named", "b.tooled"]
    assert TOOL_MATCH_CEILING < 100


def test_a_skill_with_no_tools_still_works():
    assert tooled_canon().candidates("postgresql")[0].via == "alias"


def test_the_real_bar_separates_its_tools(canon):
    """The placeholder bar was shipped with pgvector, ragas and langgraph filed
    as aliases — they are tools, and are now filed as such."""
    assert canon.candidates("pgvector")[0].via == "tool"
    assert canon.candidates("ragas")[0].via == "tool"
    assert canon.candidates("langgraph")[0].via == "tool"
    assert canon.candidates("embeddings")[0].via == "alias"
    assert canon.candidates("evals")[0].via == "alias"


def test_the_match_kind_reaches_the_model(canon):
    """The model has to know which kind of hit it is looking at to weigh it."""
    prompt = build_user_prompt({"pgvector": canon.candidates("pgvector")})
    assert '\\"matched_as\\": \\"tool\\"' in prompt or '"matched_as": "tool"' in prompt


def test_a_depth_number_carries_its_meaning(canon):
    """`senior: 3` on its own is not a requirement anyone can author against."""
    assert canon.depth_word(1) == "aware of it"
    assert canon.depth_word(3) == "can design with it"
    assert canon.depth_word(4) == "can defend it under load"


def test_the_weight_scale_is_stated_too(canon):
    assert canon.weight_scale[5] == "critical to the role"
    assert canon.weight_scale[3] == "expected"


def test_an_unknown_depth_does_not_invent_a_word(canon):
    assert canon.depth_word(9) == "depth 9"


def test_no_two_skills_claim_the_same_word(canon):
    """The lint. "long context" was claimed by systems.context AND
    landscape.capability_limits; a duplicate is silent, so it needs a test."""
    from app.skillcanon import collisions

    assert collisions(canon) == {}


def test_the_lint_catches_a_duplicate_when_there_is_one():
    from app.skillcanon import collisions

    clashing = SkillCanon(
        role_key="test", version="v1",
        skills=(
            CanonSkill("a.one", "One", "a", aliases=("long context",), tools=()),
            CanonSkill("b.two", "Two", "b", aliases=("long context",), tools=()),
        ),
    )
    assert collisions(clashing) == {"long context": ["a.one", "b.two"]}


def test_the_lint_sees_tools_as_well_as_aliases():
    from app.skillcanon import collisions

    clashing = SkillCanon(
        role_key="test", version="v1",
        skills=(
            CanonSkill("a.one", "One", "a", aliases=("pgvector",), tools=()),
            CanonSkill("b.two", "Two", "b", aliases=(), tools=("pgvector",)),
        ),
    )
    assert "pgvector" in collisions(clashing)


def test_the_common_tools_of_the_role_are_covered(canon):
    """Coverage pass: a CV built on Pinecone and LlamaIndex must not show up
    with no retrieval evidence at all. These are tools, never aliases — the
    candidate named a product, not the skill."""
    for tool, expected in [
        ("FAISS", "retrieval.embeddings"),
        ("Pinecone", "retrieval.embeddings"),
        ("LlamaIndex", "retrieval.rag_design"),
        ("LangChain", "agents.orchestration"),
        ("vLLM", "systems.cost_latency"),
        ("LangSmith", "evaluation.observability"),
    ]:
        best = canon.candidates(tool)[0]
        assert best.key == expected, f"{tool} -> {best.key}"
        assert best.via == "tool"


def test_the_bar_still_has_no_duplicate_spellings_after_the_tool_pass(canon):
    """30 entries were added by hand; the lint is what makes that safe."""
    from app.skillcanon import collisions

    assert collisions(canon) == {}
