"""Offline tests for app/signals.py — ownership, seniority signals, depth score."""

import pytest

from app import policy
from app.signals import (
    ProjectFacts,
    RoleFacts,
    depth_score,
    education_weight,
    leads_people,
    ownership,
    ownership_level,
    parse_team_size,
    seniority_signals,
    signal_tier,
)


def proj(
    pid: str = "p1",
    your_role: str | None = None,
    scale: str = "thin",
    hardest: str = "thin",
    flags: frozenset[str] = frozenset(),
    words: int = 0,
) -> ProjectFacts:
    return ProjectFacts(pid, None, your_role, scale, hardest, flags, words)


def role(rid: str = "r1", led: bool | None = None, size: int | None = None) -> RoleFacts:
    return RoleFacts(rid, led, size)


# ---------------------------------------------------------------------------
# parse_team_size
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("quote", "expected"),
    [
        ("I was on a team of 6", 6),
        ("6 engineers reported into the group", 6),
        ("led 4 people across two sites", 4),
        ("a 12-person team", 12),
        ("a 12 person team", 12),
        ("a 12–person team", 12),  # en dash
        ("team of six", 6),
        ("I led three people", 3),
        ("Twelve engineers", 12),
        ("managed a team of 9 over 3 years", 9),
        ("worked 3 years with 5 developers", 5),
        ("In 2021 I led a team of 5", 5),
        ("supported 500 users", None),
        ("led 2 projects", None),
        ("a small team", None),
        ("", None),
        (None, None),
        ("team of 0", None),
        ("team of 20000", None),
        ("team of 10000", 10000),
    ],
)
def test_parse_team_size(quote: str | None, expected: int | None) -> None:
    assert parse_team_size(quote) == expected


# ---------------------------------------------------------------------------
# leads_people
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("quote", "expected"),
    [
        ("Led a team of 5", True),
        ("I managed four developers", True),
        ("Mentored two juniors", True),
        ("Headed the platform group", True),
        ("Supervised the night shift", True),
        ("three direct reports", True),
        ("two analysts reporting to me", True),
        ("I was part of a team of 8", False),
        ("member of a team that led the migration", False),
        ("was part of the group; I mentored one intern", False),
        ("a team of 8", False),
        ("worked closely with the team", False),
        (None, None),
        ("   ", None),
    ],
)
def test_leads_people(quote: str | None, expected: bool | None) -> None:
    assert leads_people(quote) is expected


# Review fix v1.2: a lead marker counts only when the candidate is its subject.
@pytest.mark.parametrize(
    "quote",
    [
        "We were a team of 5, led by our manager",  # passive, someone else
        "I was managed by the CTO in a team of 8",  # passive ("was managed by")
        "We led the migration",  # team word as subject
        "Our manager led a team of 6",  # third party as subject
        "The team was led by Priya",  # passive
        "The CTO managed four developers",  # third party
        "I worked with a lead who mentored the juniors",  # relative clause, someone else
        "We hired and led a team of 5",  # team word behind chained verbs
        "Our manager had three direct reports",  # phrase with a third-party subject
        "I was mentored by a senior engineer",  # passive on the candidate
        "Led by example",  # passive-shaped, no people
    ],
)
def test_leads_people_someone_else_led(quote: str) -> None:
    assert leads_people(quote) is False


@pytest.mark.parametrize(
    "quote",
    [
        "I led a team of 6 engineers",
        "Led a team of 4",  # resume style, no subject
        "Managed 3 direct reports",
        "I mentored two juniors",
        "Hired and led a team of 5",
        "I led the team of 5 engineers",
        "In 2021 I led a team of 5",
        "I also successfully managed four developers",
        "I was hired and later led a team of 4",
        "I was leading a team of 6",  # progressive, active
        "The team of 6 was managed by me",  # passive, the candidate is the agent
        "We were a team of 8; I mentored two of them",  # the candidate's own clause
        "three direct reports",
        "I had 4 direct reports",
        "two analysts reporting to me",
    ],
)
def test_leads_people_candidate_led(quote: str) -> None:
    assert leads_people(quote) is True


# ---------------------------------------------------------------------------
# ownership
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("roles", "projects", "expected"),
    [
        ([role(led=True)], [], "leader"),
        ([], [proj(your_role="led")], "leader"),
        ([role(led=True)], [proj(your_role="contributed")], "leader"),
        ([role(led=False)], [proj(your_role="owned"), proj("p2", your_role="led")], "leader"),  # led beats owned
        ([], [proj(your_role="owned")], "owner"),
        ([], [proj(your_role="built_solo")], "owner"),
        ([role(led=None, size=20)], [proj(your_role="owned")], "owner"),  # big team is not leading
        ([role(led=False)], [proj(your_role="contributed"), proj("p2", your_role=None)], "contributor"),
        ([], [], "contributor"),
    ],
)
def test_ownership_level(roles: list[RoleFacts], projects: list[ProjectFacts], expected: str) -> None:
    assert ownership_level(roles, projects) == expected
    read = ownership(roles, projects)
    assert read.level == expected
    assert read.basis.lower().startswith(expected)


def test_ownership_basis_counts() -> None:
    read = ownership([role(led=True)], [proj(your_role="led"), proj("p2", your_role="led")])
    assert read.basis == "Leader: led a team in 1 role and led 2 projects."


# ---------------------------------------------------------------------------
# signal tiers and seniority signals
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("count", "total", "expected"),
    [
        (0, 4, "none"),
        (0, 0, "none"),
        (1, 1, "some"),  # 100% but only one instance
        (1, 2, "some"),
        (2, 4, "strong"),  # exactly 0.5
        (2, 5, "some"),  # 0.4
        (2, 2, "strong"),
        (3, 4, "strong"),
    ],
)
def test_signal_tier(count: int, total: int, expected: str) -> None:
    assert signal_tier(count, total) == expected


def test_no_projects_project_signals_none() -> None:
    sig = seniority_signals([role(led=True, size=10)], [])
    assert set(sig) == {"scope", "tradeoffs", "ambiguity", "cross_team"}
    for key in ("scope", "tradeoffs", "ambiguity"):
        read = sig[key]
        assert (read.tier, read.count, read.total) == ("none", 0, 0)
        assert read.basis == "No project evidence captured yet"


# Review fix v1.2: cross_team comes from the roles, projects or not.
@pytest.mark.parametrize(
    ("roles", "expected"),
    [
        ([role(led=True, size=9)], ("some", 1, 1)),
        ([role(led=False, size=policy.SIZABLE_TEAM), role("r2", led=True)], ("strong", 2, 2)),
        ([role(led=False, size=2)], ("none", 0, 1)),
        ([], ("none", 0, 0)),
    ],
)
def test_cross_team_without_projects(roles: list[RoleFacts], expected: tuple[str, int, int]) -> None:
    read = seniority_signals(roles, [])["cross_team"]
    assert (read.tier, read.count, read.total) == expected
    assert "role" in read.basis
    assert read == seniority_signals(roles, [proj()])["cross_team"]


def test_managed_team_quote_without_projects_gives_cross_team() -> None:
    quote = "I managed a team of 9 engineers"
    r = RoleFacts("r1", leads_people(quote), parse_team_size(quote))
    assert (r.led_team, r.team_size) == (True, 9)
    read = seniority_signals([r], [])["cross_team"]
    assert (read.tier, read.count, read.total) == ("some", 1, 1)


@pytest.mark.parametrize(
    ("scales", "expected_tier", "expected_count"),
    [
        (["thin", "noise", "empty", "thin"], "none", 0),
        (["substantive", "thin", "thin", "thin"], "some", 1),
        (["substantive", "specific", "thin", "thin"], "strong", 2),  # 2/4 = 0.5
        (["substantive", "specific", "thin", "thin", "noise"], "some", 2),  # 2/5
        (["specific"], "some", 1),
    ],
)
def test_scope_signal(scales: list[str], expected_tier: str, expected_count: int) -> None:
    projects = [proj(f"p{i}", scale=s) for i, s in enumerate(scales)]
    read = seniority_signals([], projects)["scope"]
    assert (read.tier, read.count, read.total) == (expected_tier, expected_count, len(scales))
    assert f"{expected_count} of {len(scales)} project" in read.basis


@pytest.mark.parametrize(
    ("hardest", "expected_tier", "expected_count"),
    [
        (["substantive", "thin"], "none", 0),
        (["specific", "substantive"], "some", 1),
        (["specific", "specific", "thin", "thin"], "strong", 2),
        (["specific", "specific", "thin", "thin", "thin"], "some", 2),
    ],
)
def test_tradeoffs_signal(hardest: list[str], expected_tier: str, expected_count: int) -> None:
    projects = [proj(f"p{i}", hardest=h) for i, h in enumerate(hardest)]
    read = seniority_signals([], projects)["tradeoffs"]
    assert (read.tier, read.count) == (expected_tier, expected_count)


CAUSAL = frozenset({"decision", "causal"})
MIN = policy.DEFENDED_MIN_WORDS


@pytest.mark.parametrize(
    ("project", "counts"),
    [
        (proj(hardest="specific", flags=CAUSAL, words=MIN), True),
        (proj(hardest="specific", flags=CAUSAL, words=MIN - 1), False),
        (proj(hardest="specific", flags=frozenset({"decision"}), words=MIN + 10), False),
        (proj(hardest="substantive", flags=CAUSAL, words=MIN + 10), False),
    ],
)
def test_ambiguity_single_project(project: ProjectFacts, counts: bool) -> None:
    read = seniority_signals([], [project])["ambiguity"]
    assert read.count == int(counts)
    assert read.tier == ("some" if counts else "none")


def test_ambiguity_strong_at_half() -> None:
    good = proj("a", hardest="specific", flags=CAUSAL, words=MIN)
    weak = proj("b", hardest="specific", flags=frozenset(), words=MIN)
    read = seniority_signals([], [good, good, weak, weak])["ambiguity"]
    assert (read.tier, read.count, read.total) == ("strong", 2, 4)
    assert seniority_signals([], [good, good, weak, weak])["tradeoffs"].count == 4


@pytest.mark.parametrize(
    ("roles", "expected_tier", "expected_count"),
    [
        ([role(led=False, size=5), role("r2", led=None, size=None)], "none", 0),
        ([role(led=False, size=policy.SIZABLE_TEAM), role("r2"), role("r3")], "some", 1),
        ([role(led=True, size=2), role("r2", size=policy.SIZABLE_TEAM), role("r3"), role("r4")], "strong", 2),
        ([role(led=True), role("r2"), role("r3"), role("r4"), role("r5")], "some", 1),
        ([], "none", 0),
    ],
)
def test_cross_team_signal(roles: list[RoleFacts], expected_tier: str, expected_count: int) -> None:
    read = seniority_signals(roles, [proj()])["cross_team"]
    assert (read.tier, read.count, read.total) == (expected_tier, expected_count, len(roles))
    assert "role" in read.basis


def test_unknown_tier_counts_as_lowest() -> None:
    read = seniority_signals([], [proj(scale="bogus")])["scope"]
    assert read.count == 0


# ---------------------------------------------------------------------------
# depth score
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("sources", "recency", "expected"),
    [
        ([("mentioned", False)], "dated", 8),  # 20 - 12
        ([("demonstrated", False)], "current", 59),  # 55 + 4
        ([("demonstrated", True), ("demonstrated", False)], "recent", 68),  # 55 + 8 + 5
        ([("led", False), ("mentioned", False), ("mentioned", False)], "recent", 79),  # 75 + 2*2
        ([("led", False)] + [("mentioned", False)] * 5, "recent", 79),  # mention cap 4
        ([("mentioned", False)] * 3, "recent", 24),  # first mention is the base: 20 + 2*2
        ([("mentioned", True)], "recent", 20),  # quantified only counts on deep sources
        ([("led", True)] * 4, "current", 100),  # 75 + 16 + 5 + 4 = 100
        ([("led", True)] * 4 + [("mentioned", False)] * 3, "current", 100),  # 104 clamped
        ([], "dated", 0),  # 0 - 12 clamped
        ([("none", False)], "unknown", 0),
        ([("demonstrated", False)], "unknown", 49),
        ([("demonstrated", False)], "weird", 49),  # unknown recency label -> unknown adj
    ],
)
def test_depth_score(sources: list[tuple[str, bool]], recency: str, expected: int) -> None:
    score, basis = depth_score(sources, recency)
    assert score == expected
    assert basis.endswith(f"= {expected}") or "clamped" in basis


def test_depth_basis_text() -> None:
    _, basis = depth_score([("demonstrated", True), ("demonstrated", False)], "current")
    assert basis == "demonstrated 55 + corroboration 8 + quantified 5 + recency current +4 = 72"
    _, basis = depth_score([("mentioned", False)], "dated")
    assert basis == "mentioned 20 + recency dated -12 = 8"
    _, basis = depth_score([], "dated")
    assert basis == "none 0 + recency dated -12 = 0 (clamped from -12)"
    _, basis = depth_score([("led", False), ("mentioned", False)], "recent")
    assert basis == "led 75 + mentions 2 + recency recent 0 = 77"


# ---------------------------------------------------------------------------
# education weight
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(("years", "expected"), [(4.9, 1), (5.0, 0), (0.0, 1), (12, 0), (None, 0)])
def test_education_weight(years: float | None, expected: int) -> None:
    assert education_weight(years) == expected
