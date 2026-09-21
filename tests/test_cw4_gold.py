"""CW-4 gold set and its offline scorer.

The rule the whole workload rests on, quoted from the reference: "a false 'demonstrated'
is unrecoverable". So the instrument that measures CW-4 must not be a flat accuracy — an
over-credit has to cost more than the equivalent under-credit, and these tests pin that.

Nothing here calls a model.
"""

from __future__ import annotations

import json
from collections import Counter

import pytest

from evals.cw4 import (
    DEFAULT_WEIGHTS,
    GOLD_PATH,
    LEVELS,
    MISSING,
    CostWeights,
    GoldSet,
    load_gold,
    rank,
    render,
    row_cost,
    score,
)


@pytest.fixture(scope="module")
def gold() -> GoldSet:
    return load_gold()


def perfect(gold: GoldSet) -> dict[str, str]:
    return {c.id: c.gold for c in gold}


# --- the fixture ---------------------------------------------------------
def test_the_gold_set_parses(gold):
    assert len(gold) >= 40
    assert gold.meta["status"] == "SYNTHETIC AND UNREVIEWED"


def test_every_row_has_every_field(gold):
    for c in gold:
        assert c.id and c.skill and c.quote and c.project and c.candidate and c.why
        assert isinstance(c.slices, tuple)


def test_ids_are_unique(gold):
    ids = [c.id for c in gold]
    assert len(set(ids)) == len(ids)


def test_every_gold_verdict_is_one_of_the_four_levels(gold):
    assert {c.gold for c in gold} <= set(LEVELS)


def test_the_ladder_is_the_profilers_own_not_a_parallel_scale():
    """§13's weaker-wins rule and this scorer must read the same four rungs.

    `evals.cw4` declares them locally so it does not import the CW-4 agent while that
    agent is still being written; this test is what stops the copy drifting.
    """
    from app.candidate_profile import EVIDENCE_ORDER

    assert LEVELS == tuple(EVIDENCE_ORDER)


def test_all_four_levels_are_represented_with_a_real_share_of_none(gold):
    counts = Counter(c.gold for c in gold)
    assert all(counts[lv] >= 5 for lv in LEVELS)
    assert counts["none"] / len(gold) >= 0.20


def test_a_malformed_row_is_refused_not_skipped(tmp_path):
    raw = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    raw["claims"][0].pop("why")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="missing"):
        load_gold(bad)


def test_a_gold_verdict_off_the_ladder_is_refused(tmp_path):
    raw = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    raw["claims"][0]["gold"] = "expert"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="not one of"):
        load_gold(bad)


# --- the D10 slice -------------------------------------------------------
def test_the_d10_slice_is_a_real_population(gold):
    assert len(gold.slice("d10")) >= 15


def test_no_d10_row_is_gold_led(gold):
    """A quote that is only adjacent to the skill can never prove ownership of it."""
    assert [c.id for c in gold.slice("d10") if c.gold == "led"] == []


def test_most_d10_rows_are_gold_none(gold):
    d10 = gold.slice("d10")
    counts = Counter(c.gold for c in d10)
    assert counts["none"] > counts["mentioned"] + counts["demonstrated"] - counts["none"]
    assert counts["none"] >= len(d10) / 2


def test_the_reference_defect_shape_is_in_the_set(gold):
    """Terraform rated on "I ran the schema migrations" — the example in §4.1."""
    row = next(c for c in gold if c.id == "cw4-029")
    assert row.skill == "Terraform"
    assert "schema migrations" in row.quote
    assert row.gold == "none"
    assert "d10" in row.slices


def test_team_language_never_reaches_led(gold):
    assert [c.id for c in gold.slice("team") if c.gold == "led"] == []


def test_a_tool_in_a_stack_list_is_mentioned_at_best(gold):
    stack = gold.slice("stack_list")
    assert stack
    assert all(rank(c.gold) <= rank("mentioned") for c in stack)


def test_every_borderline_row_says_so_in_its_why(gold):
    """A disagreement on a near-miss is read differently from one on a clear case, so the
    reason a row is arguable has to be legible to whoever audits the score."""
    borderline = gold.slice("borderline")
    assert len(borderline) >= 5
    assert all("BORDERLINE" in c.why for c in borderline)


# --- the cost matrix -----------------------------------------------------
def test_an_exact_verdict_costs_nothing():
    assert all(row_cost(lv, lv) == 0.0 for lv in LEVELS)


def test_an_over_credit_costs_more_than_the_equivalent_under_credit():
    for far, near in (("demonstrated", "none"), ("led", "mentioned"), ("led", "none")):
        assert row_cost(near, far) > row_cost(far, near)


def test_the_references_own_example_costs_several_times_the_reverse():
    """"A false 'demonstrated' is unrecoverable"; a too-low rating is merely probed."""
    assert row_cost("none", "demonstrated") >= 5 * row_cost("demonstrated", "none")


def test_crossing_into_demonstrated_costs_more_than_a_longer_move_below_it():
    """The surcharge is a threshold, not a distance: one rung over the probe line beats
    three rungs of under-crediting."""
    assert row_cost("mentioned", "demonstrated") > row_cost("led", "none")


def test_distance_still_matters_above_the_line():
    assert row_cost("none", "led") > row_cost("none", "demonstrated") > row_cost("none", "mentioned")


def test_the_weights_are_changeable_without_editing_the_scorer():
    flat = CostWeights(under_credit_per_rung=1.0, over_credit_per_rung=1.0,
                       over_credit_crosses_probe_line=0.0)
    assert row_cost("none", "demonstrated", flat) == row_cost("demonstrated", "none", flat)


# --- the scorer ----------------------------------------------------------
def test_a_perfect_prediction_scores_perfectly(gold):
    report = score(perfect(gold), gold)
    assert report.overall.exact == len(gold)
    assert report.overall.exact_rate == 1.0
    assert report.overall.total_cost == 0.0
    assert report.missing_ids == []
    assert report.worst == []


def test_an_over_credit_costs_more_than_the_equivalent_under_credit_end_to_end(gold):
    row = next(c for c in gold if c.gold == "mentioned")
    over = score({**perfect(gold), row.id: "led"}, gold)
    under = score({**perfect(gold), row.id: "none"}, gold)
    assert over.overall.total_cost > under.overall.total_cost
    assert over.overall.over_credit == 1 and over.overall.under_credit == 0
    assert under.overall.under_credit == 1 and under.overall.over_credit == 0


def test_over_and_under_credit_are_reported_separately(gold):
    a = next(c for c in gold if c.gold == "none")
    b = next(c for c in gold if c.gold == "led")
    report = score({**perfect(gold), a.id: "led", b.id: "none"}, gold)
    assert report.overall.over_credit == 1
    assert report.overall.under_credit == 1
    assert report.overall.over_cost > report.overall.under_cost
    assert report.overall.distance[3] == 1 and report.overall.distance[-3] == 1


def test_a_missing_prediction_is_reported_rather_than_silently_ignored(gold):
    preds = perfect(gold)
    dropped = gold.claims[0].id
    del preds[dropped]
    report = score(preds, gold)
    assert report.missing_ids == [dropped]
    assert report.overall.missing == 1
    assert report.overall.missing_cost == DEFAULT_WEIGHTS.missing_prediction
    assert report.overall.exact_rate < 1.0  # a skipped row is not a free row
    assert dropped in render(report)


def test_an_id_that_is_not_in_the_gold_set_is_reported(gold):
    report = score({**perfect(gold), "cw4-does-not-exist": "led"}, gold)
    assert report.unknown_ids == ["cw4-does-not-exist"]
    assert report.overall.rows == len(gold)


def test_a_verdict_off_the_ladder_is_a_caller_bug(gold):
    with pytest.raises(ValueError, match="not one of"):
        score({**perfect(gold), gold.claims[0].id: "expert"}, gold)


def test_the_confusion_matrix_sums_to_the_number_of_rows(gold):
    preds = perfect(gold)
    del preds[gold.claims[0].id]
    preds[gold.claims[1].id] = "led"
    report = score(preds, gold)
    assert report.overall.matrix_total == len(gold)
    assert report.overall.matrix[gold.claims[0].gold][MISSING] == 1


def test_the_per_level_breakdown_shows_where_the_misses_went(gold):
    row = next(c for c in gold if c.gold == "none")
    report = score({**perfect(gold), row.id: "demonstrated"}, gold)
    assert report.overall.matrix["none"]["demonstrated"] == 1
    assert report.overall.matrix["none"]["none"] == sum(1 for c in gold if c.gold == "none") - 1


def test_the_d10_slice_is_scored_separately(gold):
    d10 = gold.slice("d10")[0]
    clear = next(c for c in gold if not c.slices and c.gold == "none")
    report = score({**perfect(gold), d10.id: "led", clear.id: "led"}, gold)
    assert report.slices["d10"].rows == len(gold.slice("d10"))
    assert report.slices["d10"].over_credit == 1
    assert report.slices["d10"].total_cost < report.overall.total_cost


def test_the_report_renders_for_a_terminal(gold):
    text = render(score(perfect(gold), gold))
    assert "OVERALL" in text and "[d10]" in text
    assert "POC choice, not a Caliber number" in text
    assert max(len(line) for line in text.splitlines()) < 120
