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
    project_role,
    years_mismatch,
)
from app.config import DATA_DIR
from app.policy import MAX_QUOTE_CHARS
from app.schemas import ProfileDraft
from app.textmatch import GroundingText

TODAY = date(2026, 9, 18)
FIXTURES = DATA_DIR / "fixtures"

# A synthetic candidate whose every field is present and substantive (HUM-3: invented).
FULL = (
    "Acme Corp - Staff Engineer, Full-time, Jan 2020 - Dec 2021. Fintech payments. I led a team of 6 engineers.\n"
    "Built the payment reconciliation service for card transactions across three regions.\n"
    "I was responsible for the service design, the rollout plan and the on-call rota.\n"
    "Cut reconciliation time from 6 hours to 20 minutes for the finance team.\n"
    "I chose event sourcing over nightly batch jobs because late card refunds broke the batch totals, "
    "which would have kept finance waiting days.\n"
    "Handled 2 million transactions a day under a strict audit constraint.\n"
    "Stack: Kafka, PostgreSQL. Code review and on-call."
)


def role(rid="r1", employer="Acme Corp", title="Staff Engineer", start="Jan 2020", end="Dec 2021", current=False,
         employment="Full-time", domain="fintech payments", team="I led a team of 6 engineers"):
    return {"analysis": "a", "role_id": rid, "employer_raw": employer, "title_raw": title, "start_raw": start,
            "end_raw": end, "is_current": current, "employment_type_raw": employment, "domain": domain,
            "team_quote": team}


def project(pid="p1", rid="r1",
            summary="Built the payment reconciliation service for card transactions across three regions",
            role_quote="I was responsible for the service design", your_role="owned",
            resp="I was responsible for the service design, the rollout plan and the on-call rota",
            impact="Cut reconciliation time from 6 hours to 20 minutes for the finance team",
            hardest="I chose event sourcing over nightly batch jobs because late card refunds broke the batch totals, "
                    "which would have kept finance waiting days",
            scale="Handled 2 million transactions a day under a strict audit constraint",
            processes=("Code review", "on-call"), stack=("Kafka", "PostgreSQL")):
    return {"analysis": "a", "project_id": pid, "role_id": rid, "name": "reconciliation service",
            "summary_quote": summary, "role_quote": role_quote, "your_role": your_role,
            "responsibilities_quote": resp, "impact_quote": impact, "hardest_problem_quote": hardest,
            "scale_quote": scale, "processes": list(processes), "stack": list(stack)}


def claim(skill, quote, verdict, pid="p1"):
    return {"analysis": "a", "project_id": pid, "skill": skill, "quote": quote, "verdict": verdict,
            "confidence": "high"}


def draft(roles=(), projects=(), skills=(), years=None, educations=()):
    return ProfileDraft.model_validate(
        {"analysis": "a", "stated_years_raw": years, "roles": list(roles), "projects": list(projects),
         "skills": list(skills), "educations": list(educations)}
    )


def keys(p, required=None):
    return {m.key for m in p.missing_fields if required is None or m.required is required}


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


@pytest.mark.parametrize(
    "your_role,quote,expected",
    [
        ("led", "We added an evaluation step", "contributed"),
        ("owned", "the team owned the pipeline", "contributed"),
        ("built_solo", "I built it alone", "built_solo"),
        ("led", "I led four engineers on the rewrite", "led"),
        ("contributed", "We shipped it", "contributed"),
        (None, "anything", None),
    ],
)
def test_project_role_never_stands_on_team_language(your_role, quote, expected):
    assert project_role(your_role, quote) == expected


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
    assert "role:r2:title" in keys(ravi, required=True)


def test_ravi_fabricated_skill_is_dropped(ravi):
    assert "Kubernetes" not in {s.name for s in ravi.skills}
    assert any("Kubernetes" in x for x in ravi.grounding.dropped_claims)


def test_ravi_evidence_after_weaker_wins(ravi):
    ev = {s.name: s.evidence for s in ravi.skills}
    assert ev["pgvector"] == "led"
    assert ev["LangChain"] == ev["Redis"] == ev["Python"] == ev["scikit-learn"] == ev["Java"] == "demonstrated"
    assert ev["Airflow"] == ev["Spring Boot"] == "mentioned"
    for name in ("OpenAI", "Ragas", "Grafana"):  # over-claims are capped and flagged for probing
        s = next(s for s in ravi.skills if s.name == name)
        assert s.evidence == "mentioned" and s.probe_first
    assert len(ravi.grounding.capped_claims) == 3


def test_ravi_team_language_role_is_downgraded(ravi):
    p2 = next(p for p in ravi.projects if p.project_id == "p2")
    assert p2.your_role == "contributed"
    assert ravi.grounding.capped_roles == ["project p2 your_role: led -> contributed (team language)"]
    p1 = next(p for p in ravi.projects if p.project_id == "p1")
    assert p1.your_role == "owned" and p1.role_quote == "owned the retrieval redesign"


def test_ravi_vague_stack_item_is_asked_about_never_a_skill(ravi):
    p2 = next(p for p in ravi.projects if p.project_id == "p2")
    assert p2.stack == ["Ragas"] and p2.vague_stack == ["various tools"]
    assert "various tools" not in {s.name.casefold() for s in ravi.skills}
    vague = [m for m in ravi.missing_fields if m.reason == "vague"]
    assert len(vague) == 1 and not vague[0].required and "various tools" in vague[0].question


def test_ravi_stack_only_skill_is_mentioned_without_a_quote(ravi):
    spring = next(s for s in ravi.skills if s.name == "Spring Boot")
    assert spring.evidence == "mentioned" and spring.quote is None and spring.project_ids == ["p5"]


def test_ravi_dates_years_and_recency(ravi):
    months = {r.role_id: r.months for r in ravi.roles}
    assert months == {"r1": 42, "r2": 21, "r3": 10}
    assert [r.recency for r in ravi.roles] == ["current", "dated", "dated"]
    assert ravi.dated_years == 6.1 and ravi.stated_years == 6.0
    assert ravi.years_experience == 6.0 and not ravi.years_mismatch


def test_ravi_depth_scores(ravi):
    depth = {s.name: s.depth_score for s in ravi.skills}
    assert depth["pgvector"] == 84  # led 75 + quantified 5 + current 4
    assert depth["LangChain"] == 64  # demonstrated 55 + quantified 5 + current 4
    assert depth["Java"] == 43  # demonstrated 55 − dated 12
    assert depth["Airflow"] == 8  # mentioned 20 − dated 12
    assert all(s.depth_basis.endswith(f"= {s.depth_score}") for s in ravi.skills)


def test_ravi_signals_and_education(ravi):
    assert ravi.ownership.level == "owner"
    tiers = {k: v.tier for k, v in ravi.seniority.items()}
    assert tiers == {"scope": "some", "tradeoffs": "some", "ambiguity": "none", "cross_team": "none"}
    assert [(e.institution, e.qualification, e.end_year) for e in ravi.educations] == [
        ("Riverton Institute of Technology", "B.Tech, Computer Science", "2020")
    ]


def test_ravi_completeness_required_vs_optional(ravi):
    req = keys(ravi, required=True)
    assert not ravi.is_complete and len(req) == 18
    assert "project:p1:responsibilities" in req
    assert not any(k.startswith("project:p1:") and k != "project:p1:responsibilities" for k in req)
    for pid in ("p2", "p3", "p4", "p5"):
        for fld in ("responsibilities", "impact", "hardest_problem", "scale"):
            assert f"project:{pid}:{fld}" in req
    opt = keys(ravi, required=False)
    assert {"role:r1:context", "role:r2:context", "role:r3:context", "project:p1:processes"} <= opt
    assert "education" not in opt  # 6 years: education is not asked for


# --- a complete profile ----------------------------------------------------------
def test_a_fully_described_candidate_is_complete():
    p = build_profile(draft([role()], [project()], [claim("Kafka", "Stack: Kafka", "mentioned")]), [FULL], today=TODAY)
    assert p.grounding.dropped_fields == [] and p.grounding.capped_roles == []
    assert p.is_complete and p.required_missing == []
    assert p.projects[0].quality["impact"].tier == "specific" and "quantified" in p.projects[0].quality["impact"].flags
    assert p.projects[0].quality["hardest_problem"].tier == "specific"
    r = p.roles[0]
    assert (r.employment_type, r.team_size, r.led_team) == ("Full-time", 6, True)
    assert p.ownership.level == "leader"
    assert {k: v.tier for k, v in p.seniority.items()} == {
        "scope": "some", "tradeoffs": "some", "ambiguity": "some", "cross_team": "some"
    }
    # 2 years of experience (< 5): education is nudged, but never blocks
    assert keys(p, required=False) == {"education"}


# --- thin answers, refinements, project roles -------------------------------------
def test_a_thin_answer_is_re_asked_with_its_reason():
    text = FULL + "\nMade things better."
    p = build_profile(draft([role()], [project(impact="Made things better")]), [text], today=TODAY)
    m = next(m for m in p.missing_fields if m.key == "project:p1:impact")
    assert m.required and m.reason in ("thin", "noise") and "Your answer so far" in m.question
    assert not p.is_complete


def test_substantive_but_not_specific_answers_get_optional_refinements():
    text = FULL + "\nMade the finance team much faster at month end.\nIt was a tough migration with lots of moving parts to coordinate."
    d = draft([role()], [project(impact="Made the finance team much faster at month end",
                                 hardest="It was a tough migration with lots of moving parts to coordinate")])
    p = build_profile(d, [text], today=TODAY)
    assert p.is_complete  # refinements never block
    assert {"project:p1:impact:quantify", "project:p1:hardest_problem:decision"} <= keys(p, required=False)


def test_your_role_without_a_verified_quote_is_dropped_and_asked():
    d = draft([role()], [project(role_quote="I single-handedly rebuilt everything", your_role="built_solo")])
    p = build_profile(d, [FULL], today=TODAY)
    assert p.projects[0].your_role is None and p.projects[0].role_quote is None
    assert any("your_role" in x for x in p.grounding.dropped_fields)
    assert "project:p1:your_role" in keys(p, required=True)


def test_vague_skill_claims_are_dropped():
    text = FULL + "\nUsed various tools."
    d = draft([role()], [project(stack=("Kafka", "various tools"))], [claim("various tools", "Used various tools", "demonstrated")])
    p = build_profile(d, [text], today=TODAY)
    assert "various tools" not in {s.name for s in p.skills}
    assert any("too general" in x for x in p.grounding.dropped_claims)


def test_no_concrete_stack_is_required():
    p = build_profile(draft([role()], [project(stack=())]), [FULL], today=TODAY)
    assert "project:p1:stack" in keys(p, required=True)


def test_long_quotes_are_clipped_and_stay_grounded():
    long_summary = "Built the reconciliation platform " + "for many regions and teams " * 20
    text = FULL + "\n" + long_summary
    p = build_profile(draft([role()], [project(summary=long_summary.strip())]), [text], today=TODAY)
    s = p.projects[0].summary
    assert s is not None and len(s) <= MAX_QUOTE_CHARS
    assert GroundingText(text).contains(s)


def test_education_is_nudged_only_below_five_years():
    junior = build_profile(draft([role()], [project()], years="2 years"), [FULL + " 2 years"], today=TODAY)
    senior = build_profile(draft([role()], [project()], years="10 years"), [FULL + " 10 years"], today=TODAY)
    assert "education" in keys(junior, required=False)
    assert "education" not in keys(senior)


# --- smaller cases (unchanged rules) --------------------------------------------
def test_empty_draft_asks_for_everything():
    p = build_profile(draft(), ["Sam Lee"], today=TODAY)
    assert keys(p) == {"roles", "years_experience", "projects"}
    assert p.skills == [] and p.years_experience is None
    assert p.ownership.level == "contributor"


def test_years_mismatch_is_flagged_not_corrected():
    p = build_profile(draft([role()], [project()], years="10 years"), [FULL + " 10 years"], today=TODAY)
    assert p.dated_years == 2.0 and p.stated_years == 10.0
    assert p.years_mismatch and p.years_experience == 10.0
    assert any("ask, don't correct" in n for n in p.grounding.notes)


@pytest.mark.parametrize(
    "stated,dated,flagged",
    [
        (6.0, 6.1, False),  # Ravi
        (6.0, 4.1, False),  # 1.9 apart: inside the 2-year floor
        (6.0, 3.9, True),  # 2.1 apart: outside max(2, 1.5)
        (12.0, 9.5, False),  # 2.5 apart: inside 25% of 12 = 3
        (12.0, 8.9, True),  # 3.1 apart: outside 3
        (None, 5.0, False),
        (5.0, None, False),
    ],
)
def test_years_mismatch_uses_caliber_tolerance(stated, dated, flagged):
    assert years_mismatch(stated, dated) is flagged


def test_no_stated_years_falls_back_to_dated():
    p = build_profile(draft([role()], [project()]), [FULL], today=TODAY)
    assert p.years_experience == 2.0 and not p.years_mismatch


def test_overlapping_roles_count_once():
    roles = [role("r1"), role("r2", employer="Beta", start="Jan 2021", end="Dec 2021")]
    p = build_profile(draft(roles, [project()]), [FULL + " Beta Jan 2021 Dec 2021"], today=TODAY)
    assert dated_years(p.roles) == 2.0


def test_start_after_end_asks_for_dates():
    p = build_profile(draft([role(start="Dec 2021", end="Jan 2020")], [project()]), [FULL], today=TODAY)
    assert p.roles[0].months is None
    assert "role:r1:dates" in keys(p, required=True)


def test_end_date_beats_stray_is_current():
    p = build_profile(draft([role(current=True)], [project()]), [FULL], today=TODAY)
    assert p.roles[0].is_current is False and p.roles[0].end == "2021-12"


def test_present_as_end_raw_means_current():
    p = build_profile(draft([role(end="Present")], [project()]), [FULL + " Present"], today=TODAY)
    assert p.roles[0].is_current and p.roles[0].recency == "current"


def test_recency_window_comes_from_config():
    # 36 months after the end is still "recent"; 37 is "dated" (scoring.yaml recent_window_months)
    recent = build_profile(draft([role(end="Sep 2023")]), [FULL + " Sep 2023"], today=TODAY)
    dated = build_profile(draft([role(end="Aug 2023")]), [FULL + " Aug 2023"], today=TODAY)
    assert recent.roles[0].recency == "recent" and dated.roles[0].recency == "dated"


def test_unknown_role_id_is_reported_and_asked():
    p = build_profile(draft([role()], [project(rid="r9")]), [FULL], today=TODAY)
    assert p.projects[0].role_id is None
    assert "project:p1:role" in keys(p, required=True)


def test_stack_items_not_in_text_are_dropped():
    p = build_profile(draft([role()], [project(stack=("Kafka", "Rust"))]), [FULL], today=TODAY)
    assert p.projects[0].stack == ["Kafka"]
    assert any("Rust" in x for x in p.grounding.dropped_fields)


def test_answers_count_as_grounding_sources():
    answer = "It cut support tickets by 40%"
    p = build_profile(draft([role()], [project(impact="cut support tickets by 40%")]), [FULL, answer], today=TODAY)
    assert p.projects[0].impact == "cut support tickets by 40%"


def test_answers_alone_can_build_a_profile():
    """Path B (FR-A2): no resume, only the candidate's answers."""
    p = build_profile(draft([role()], [project()]), ["Candidate answers:", FULL], today=TODAY)
    assert p.is_complete and p.roles[0].employer == "Acme Corp"


def test_same_skill_across_projects_merges_to_the_strongest():
    text = FULL + " Python scripts. I designed the Python service. Other work"
    projects = [project("p1"), project("p2", summary="Other work")]
    skills = [claim("Python", "Python scripts", "mentioned", "p1"), claim("Python", "I designed the Python service", "led", "p2")]
    p = build_profile(draft([role()], projects, skills), [text], today=TODAY)
    py = next(s for s in p.skills if s.name == "Python")
    assert py.evidence == "led" and py.project_ids == ["p1", "p2"]
    assert py.quote == "I designed the Python service"


# --- v1.2 review fixes: each test is a reviewer repro ---------------------------
from app.candidate_profile import has_lead_language, has_team_language, unique_ids  # noqa: E402
from app.policy import MAX_SKILL_CHARS  # noqa: E402


@pytest.mark.parametrize(
    "raw,prefix,expected",
    [
        (["r2", None], "r", ["r2", "r1"]),
        (["r1", "r1"], "r", ["r1", "r2"]),
        ([None, "r1"], "r", ["r2", "r1"]),
        (["p2", None, "p2"], "p", ["p2", "p1", "p3"]),
    ],
)
def test_ids_are_always_unique(raw, prefix, expected):
    assert unique_ids(raw, prefix) == expected


def test_duplicate_role_ids_do_not_duplicate_questions():
    roles = [role("r2", title=None), role(None, title=None)]
    p = build_profile(draft(roles, [project(rid="r2")]), [FULL], today=TODAY)
    ids = [r.role_id for r in p.roles]
    assert len(ids) == len(set(ids)) == 2
    ks = [m.key for m in p.missing_fields]
    assert len(ks) == len(set(ks))


@pytest.mark.parametrize(
    "text,team",
    [
        ("I led the team of 5 engineers", False),
        ("Managed my team of 6 through the migration", False),
        ("My team built the pipeline in Spark", True),
        ("We shipped it", True),
        ("Worked together with the data team", True),
        ("Maintained the team's dashboards", True),
        ("I built the pipeline in Spark", False),
    ],
)
def test_team_language(text, team):
    assert has_team_language(text) is team


@pytest.mark.parametrize(
    "text,lead",
    [
        ("I chose Kafka over Kinesis", True),
        ("Owned the migration end to end", True),
        ("The project was led by my manager; I wrote the Terraform modules.", False),
        ("The design was decided by the architecture board", False),
        ("I wrote the Terraform modules", False),
    ],
)
def test_lead_language_ignores_the_passive_voice(text, lead):
    assert has_lead_language(text) is lead


def test_leading_the_team_keeps_led():
    q = "I led the team of 5 engineers that rebuilt billing in Kafka"
    assert evidence_cap("Kafka", q, True) == "led"
    assert project_role("led", "I led the team of 5 engineers") == "led"


def test_my_team_is_not_personal_evidence():
    assert evidence_cap("Spark", "My team built the pipeline in Spark", True) == "mentioned"


def test_passive_led_by_caps_at_demonstrated():
    q = "The project was led by my manager; I wrote the Terraform modules."
    assert evidence_cap("Terraform", q, True) == "demonstrated"


def test_short_skill_names_need_whole_terms():
    text = FULL + "\nJava Script dashboards years ago using PostgreSQL. I chose PostgreSQL for reliability."
    d = draft([role()], [project(stack=("Go", "SQL", "R", "Kafka"))],
              [claim("SQL", "I chose PostgreSQL for reliability", "led"), claim("Go", "years ago", "demonstrated")])
    p = build_profile(d, [text], today=TODAY)
    names = {s.name for s in p.skills}
    assert {"SQL", "Go", "R"}.isdisjoint(names) and "Kafka" in names


@pytest.mark.parametrize("raw,years", [("6", 6.0), ("six years", 6.0), ("Six years of experience", 6.0), ("5+", 5.0), ("12 yrs", 12.0)])
def test_stated_years_accepts_bare_numbers_and_number_words(raw, years):
    assert parse_stated_years(raw) == years


def test_answering_the_years_question_with_a_bare_number_closes_it():
    d = draft([role(start=None, end=None)], [project()], years="6")
    p = build_profile(d, [FULL, "6"], today=TODAY)
    assert p.years_experience == 6.0 and "years_experience" not in keys(p)


def test_a_role_without_a_project_is_asked_about():
    roles = [role("r1"), role("r2", employer="Beta")]
    p = build_profile(draft(roles, [project(rid="r1")]), [FULL + " Beta"], today=TODAY)
    assert "role:r2:projects" in keys(p, required=True)
    assert "role:r1:projects" not in keys(p)


def test_claimed_but_weak_role_is_probed_first():
    text = FULL + "\nIt was a tough migration with lots of moving parts to coordinate. Elasticsearch search layer."
    d = draft([role()], [project(hardest="It was a tough migration with lots of moving parts to coordinate",
                                 stack=("Elasticsearch",))],
              [claim("Elasticsearch", "Elasticsearch search layer", "demonstrated")])
    p = build_profile(d, [text], today=TODAY)
    assert p.projects[0].your_role == "owned"
    es = next(s for s in p.skills if s.name == "Elasticsearch")
    assert es.probe_first  # owns it, but no decision named


def test_a_named_decision_clears_the_weak_claim_flag():
    p = build_profile(draft([role()], [project()], [claim("Kafka", "Stack: Kafka", "mentioned")]), [FULL], today=TODAY)
    assert not next(s for s in p.skills if s.name == "Kafka").probe_first


def test_over_long_stack_items_are_dropped():
    long_item = "Kafka " + "x" * (MAX_SKILL_CHARS + 10)
    text = FULL + "\n" + long_item
    p = build_profile(draft([role()], [project(stack=("Kafka", long_item))]), [text], today=TODAY)
    assert p.projects[0].stack == ["Kafka"]
    assert all(len(s.name) <= MAX_SKILL_CHARS for s in p.skills)


def test_clipped_quotes_keep_the_skill():
    quote = "Worked on many platform chores " + "and more chores " * 22 + "and chose Redis"
    text = FULL + "\n" + quote
    d = draft([role()], [project(stack=("Kafka",))], [claim("Redis", quote, "led")])
    p = build_profile(d, [text], today=TODAY)
    redis = next(s for s in p.skills if s.name == "Redis")
    assert redis.quote is not None and len(redis.quote) <= MAX_QUOTE_CHARS and "Redis" in redis.quote
    assert GroundingText(text).contains(redis.quote)


def test_future_end_dates_count_only_up_to_today():
    p = build_profile(draft([role(start="Jan 2025", end="Dec 2030")], [project()]), [FULL + " Jan 2025 Dec 2030"], today=TODAY)
    assert p.roles[0].months == 21 and p.dated_years == 1.8
    assert any("in the future" in n for n in p.grounding.notes)


def test_a_resume_bullet_may_serve_as_summary_and_impact():
    bullet = "Built a search service that cut latency by 40% for 2M users"
    d = draft([role()], [project(summary=bullet, impact=bullet)])
    from_resume = build_profile(d, [FULL + "\n" + bullet], today=TODAY, typed_sources=[])
    typed_twice = build_profile(d, [FULL + "\n" + bullet], today=TODAY, typed_sources=[bullet])
    assert from_resume.projects[0].quality["impact"].tier == "specific"
    assert "project:p1:impact" not in keys(from_resume)
    assert typed_twice.projects[0].quality["impact"].tier == "thin"
    assert "project:p1:impact" in keys(typed_twice, required=True)
