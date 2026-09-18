import itertools
from datetime import date

import pytest

from app.candidate_profile import (
    EVIDENCE_ORDER,
    build_profile,
    dated_years,
    evidence_cap,
    evidence_rank,
    final_evidence,
    is_present,
    parse_raw_date,
    parse_stated_years,
)
from app.config import DATA_DIR
from app.schemas import ProfileDraft

TODAY = date(2026, 9, 18)
FIXTURES = DATA_DIR / "fixtures"


def role(rid="r1", employer="Acme", title="Engineer", start="Jan 2020", end="Dec 2021", current=False):
    return {"analysis": "a", "role_id": rid, "employer_raw": employer, "title_raw": title,
            "start_raw": start, "end_raw": end, "is_current": current}


def project(pid="p1", rid="r1", summary="Built the thing", impact="Saved 10%", hardest="I chose X", stack=None):
    return {"analysis": "a", "project_id": pid, "role_id": rid, "name": "thing", "summary_quote": summary,
            "impact_quote": impact, "hardest_problem_quote": hardest, "stack": stack or []}


def claim(skill, quote, verdict, pid="p1"):
    return {"analysis": "a", "project_id": pid, "skill": skill, "quote": quote, "verdict": verdict,
            "confidence": "high"}


def draft(roles=(), projects=(), skills=(), years=None):
    return ProfileDraft.model_validate(
        {"analysis": "a", "stated_years_raw": years, "roles": list(roles), "projects": list(projects),
         "skills": list(skills)}
    )


# --- dates ---------------------------------------------------------------------
@pytest.mark.parametrize(
    "raw,is_end,expected",
    [
        ("Apr 2023", False, (2023, 4)),
        ("April 2023", False, (2023, 4)),
        ("Sept. 2021", False, (2021, 9)),
        ("03/2021", False, (2021, 3)),
        ("2021-03", False, (2021, 3)),
        ("2019", False, (2019, 1)),
        ("2019", True, (2019, 12)),
        ("Present", False, None),
        ("13/2021", False, None),
        ("Spring 2020", False, None),
        (None, False, None),
    ],
)
def test_parse_raw_date(raw, is_end, expected):
    assert parse_raw_date(raw, is_end=is_end) == expected


def test_is_present():
    assert is_present("Present") and is_present(" current ") and is_present("Till date")
    assert not is_present("Mar 2023") and not is_present(None)


def test_parse_stated_years():
    assert parse_stated_years("6 years") == 6.0
    assert parse_stated_years("5+ yrs") == 5.0
    assert parse_stated_years("7.5 years of experience") == 7.5
    assert parse_stated_years("many years") is None
    assert parse_stated_years(None) is None


# --- evidence ------------------------------------------------------------------
@pytest.mark.parametrize(
    "skill,quote,verified,expected",
    [
        ("Kafka", "I chose Kafka over Kinesis", True, "led"),
        ("Kafka", "Owned the Kafka migration", True, "led"),
        ("Redis", "caching embeddings (Redis)", True, "demonstrated"),
        ("Ragas", "We added an evaluation step (Ragas)", True, "mentioned"),
        ("Grafana", "Maintained the team's dashboards (Grafana)", True, "mentioned"),
        ("OpenAI", "I chose hybrid search in pgvector", True, "mentioned"),  # quote about another skill
        ("Kafka", "I chose Kafka over Kinesis", False, "mentioned"),  # quote not in text
        ("Kafka", None, False, "mentioned"),
    ],
)
def test_evidence_cap(skill, quote, verified, expected):
    assert evidence_cap(skill, quote, verified) == expected


def test_final_evidence_is_weaker_wins_with_a_mentioned_floor():
    for agent, cap in itertools.product([*EVIDENCE_ORDER, None], EVIDENCE_ORDER):
        out = final_evidence(agent, cap)
        agent_rank = evidence_rank(agent) if agent else evidence_rank("mentioned")
        assert evidence_rank(out) >= evidence_rank("mentioned")  # floor
        assert evidence_rank(out) <= max(agent_rank, evidence_rank("mentioned"))  # never above the model
        assert evidence_rank(out) <= max(evidence_rank(cap), evidence_rank("mentioned"))  # never above the cap


# --- the Ravi fixture: every planted mistake is caught ------------------------
@pytest.fixture(scope="module")
def ravi():
    resume = (FIXTURES / "ravi_resume.txt").read_text(encoding="utf-8")
    d = ProfileDraft.model_validate_json((FIXTURES / "ravi_draft_example.json").read_text(encoding="utf-8"))
    return build_profile(d, [resume], today=TODAY)


def test_ravi_fabricated_title_is_dropped_and_asked(ravi):
    r2 = next(r for r in ravi.roles if r.role_id == "r2")
    assert r2.title is None
    assert any("Senior Machine Learning Engineer" in x for x in ravi.grounding.dropped_fields)
    assert "role:r2:title" in {m.key for m in ravi.missing_fields}


def test_ravi_fabricated_skill_is_dropped(ravi):
    assert "Kubernetes" not in {s.name for s in ravi.skills}
    assert any("Kubernetes" in x for x in ravi.grounding.dropped_claims)


def test_ravi_evidence_after_weaker_wins(ravi):
    ev = {s.name: s.evidence for s in ravi.skills}
    assert ev["pgvector"] == "led"
    assert ev["LangChain"] == ev["Redis"] == ev["Python"] == ev["scikit-learn"] == ev["Java"] == "demonstrated"
    assert ev["Airflow"] == ev["Spring Boot"] == "mentioned"
    # over-claims are capped and flagged for probing
    for name in ("OpenAI", "Ragas", "Grafana"):
        s = next(s for s in ravi.skills if s.name == name)
        assert s.evidence == "mentioned" and s.probe_first
    assert len(ravi.grounding.capped_claims) == 3


def test_ravi_stack_only_skill_is_mentioned_without_a_quote(ravi):
    spring = next(s for s in ravi.skills if s.name == "Spring Boot")
    assert spring.evidence == "mentioned" and spring.quote is None and spring.project_ids == ["p5"]


def test_ravi_dates_years_and_recency(ravi):
    months = {r.role_id: r.months for r in ravi.roles}
    assert months == {"r1": 42, "r2": 21, "r3": 10}
    assert [r.recency for r in ravi.roles] == ["current", "dated", "dated"]
    assert ravi.dated_years == 6.1 and ravi.stated_years == 6.0
    assert ravi.years_experience == 6.0 and not ravi.years_mismatch


def test_ravi_completeness_asks_impact_and_hardest_problem(ravi):
    keys = {m.key for m in ravi.missing_fields}
    assert not ravi.is_complete
    assert len(keys) == 9
    for pid in ("p2", "p3", "p4", "p5"):
        assert f"project:{pid}:impact" in keys and f"project:{pid}:hardest_problem" in keys
    assert not any(k.startswith("project:p1") for k in keys)


# --- smaller cases -------------------------------------------------------------
TEXT = "Acme Engineer Jan 2020 Dec 2021 Built the thing Saved 10% I chose X"


def test_empty_draft_asks_for_everything():
    p = build_profile(draft(), ["Sam Lee"], today=TODAY)
    assert {m.key for m in p.missing_fields} == {"roles", "years_experience", "projects"}
    assert p.skills == [] and p.years_experience is None


def test_years_mismatch_is_flagged_not_corrected():
    p = build_profile(draft([role()], [project()], years="10 years"), [TEXT + " 10 years"], today=TODAY)
    assert p.dated_years == 2.0 and p.stated_years == 10.0
    assert p.years_mismatch and p.years_experience == 10.0
    assert any("ask, don't correct" in n for n in p.grounding.notes)


def test_no_stated_years_falls_back_to_dated():
    p = build_profile(draft([role()], [project()]), [TEXT], today=TODAY)
    assert p.years_experience == 2.0 and not p.years_mismatch


def test_overlapping_roles_count_once():
    roles = [role("r1", start="Jan 2020", end="Dec 2021"), role("r2", employer="Beta", start="Jan 2021", end="Dec 2021")]
    p = build_profile(draft(roles, [project()]), [TEXT + " Beta"], today=TODAY)
    assert dated_years(p.roles) == 2.0


def test_start_after_end_asks_for_dates():
    p = build_profile(draft([role(start="Dec 2021", end="Jan 2020")], [project()]), [TEXT], today=TODAY)
    assert p.roles[0].months is None
    assert "role:r1:dates" in {m.key for m in p.missing_fields}


def test_end_date_beats_stray_is_current():
    p = build_profile(draft([role(current=True)], [project()]), [TEXT], today=TODAY)
    assert p.roles[0].is_current is False and p.roles[0].end == "2021-12"


def test_present_as_end_raw_means_current():
    p = build_profile(draft([role(end="Present")], [project()]), [TEXT + " Present"], today=TODAY)
    assert p.roles[0].is_current and p.roles[0].recency == "current"


def test_recency_window_comes_from_config():
    # 36 months after the end is still "recent"; 37 is "dated" (scoring.yaml recent_window_months)
    recent = build_profile(draft([role(start="Jan 2020", end="Sep 2023")]), ["Acme Engineer Jan 2020 Sep 2023"], today=TODAY)
    dated = build_profile(draft([role(start="Jan 2020", end="Aug 2023")]), ["Acme Engineer Jan 2020 Aug 2023"], today=TODAY)
    assert recent.roles[0].recency == "recent" and dated.roles[0].recency == "dated"


def test_unknown_role_id_is_reported_and_asked():
    p = build_profile(draft([role()], [project(rid="r9")]), [TEXT], today=TODAY)
    assert p.projects[0].role_id is None
    assert "project:p1:role" in {m.key for m in p.missing_fields}


def test_stack_items_not_in_text_are_dropped():
    p = build_profile(draft([role()], [project(stack=["Python", "Rust"])]), [TEXT + " (Python)"], today=TODAY)
    assert p.projects[0].stack == ["Python"]
    assert any("Rust" in x for x in p.grounding.dropped_fields)


def test_answers_count_as_grounding_sources():
    answer = "It cut support tickets by 40%"
    p = build_profile(
        draft([role()], [project(impact="cut support tickets by 40%")]), [TEXT, answer], today=TODAY
    )
    assert p.projects[0].impact == "cut support tickets by 40%"


def test_same_skill_across_projects_merges_to_the_strongest():
    text = TEXT + " Python scripts. I designed the Python service. Other work"
    projects = [project("p1"), project("p2", summary="Other work")]
    skills = [claim("Python", "Python scripts", "mentioned", "p1"), claim("Python", "I designed the Python service", "led", "p2")]
    p = build_profile(draft([role()], projects, skills), [text], today=TODAY)
    [py] = p.skills
    assert py.evidence == "led" and py.project_ids == ["p1", "p2"]
    assert py.quote == "I designed the Python service"
