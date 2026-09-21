"""CW-4 claim-evidence verdict — the offline scorer.

The eval gate the reference names for CW-4 is *"asymmetric cost-matrix gold set; quote
survival"* (`reference/agents/AGENT_CAPABILITIES_AND_MODELS.md` §4.1). This module is the
cost-matrix half: it takes verdicts someone else produced and grades them against
`data/fixtures/cw4_gold.json`.

**It never calls a model.** It is the measuring instrument, not the thing measured.

Why not flat accuracy
---------------------
The two errors are not worth the same. The reference says a false "demonstrated" is
*unrecoverable*: a skill rated as proven is never assessed, so nothing downstream can
discover the mistake. A skill rated too low is caught by the probe-first mechanism — it
simply gets asked about, at the price of one question. So the report separates
**over-credit** from **under-credit**, weights them differently, and shows how far the
verdict moved (one rung or three).

The weights in `CostWeights` are a **POC choice, not a Caliber number** — see the class
docstring for the reasoning, and change them there if you disagree.

Ladder
------
`none / mentioned / demonstrated / led`, defined locally as `LEVELS` so this module has no
import dependency on the CW-4 agent (which is being built alongside it). It is the same
ladder as `app.candidate_profile.EVIDENCE_ORDER`, and `tests/test_cw4_gold.py` asserts so.
**A later wiring step should import the agent's own constant instead of redeclaring it.**
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# The evidence ladder, weakest first (RULEBOOK §9; app.candidate_profile.EVIDENCE_ORDER).
LEVELS: tuple[str, ...] = ("none", "mentioned", "demonstrated", "led")

# Below this line the skill is still probed, so a wrong verdict is recoverable.
# At or above it the skill reads as proven and is never assessed again.
PROBE_LINE: int = LEVELS.index("demonstrated")

GOLD_PATH = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "cw4_gold.json"

MISSING = "(missing)"  # the column a gold row with no prediction lands in

# Slices reported separately. "d10" is the one the workload exists for.
DEFAULT_SLICES: tuple[str, ...] = ("d10", "team", "passive", "stack_list", "borderline")


def rank(level: str) -> int:
    """Position on the ladder. Raises on anything that is not one of the four levels."""
    try:
        return LEVELS.index(level)
    except ValueError:
        raise ValueError(f"{level!r} is not one of {LEVELS}") from None


# ---------------------------------------------------------------------------
# The cost matrix
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CostWeights:
    """What each kind of mistake costs. **A POC choice, not a Caliber number.**

    * `under_credit_per_rung = 1.0` — the unit. An under-credited skill is probed and the
      truth comes out; the cost is one extra question.
    * `over_credit_per_rung = 4.0` — four questions' worth per rung. Over-crediting is the
      expensive direction because nothing downstream re-opens it.
    * `over_credit_crosses_probe_line = 6.0` — a flat surcharge when the prediction lands
      on `demonstrated` or `led` while the truth is below it. This is the error the
      reference calls unrecoverable, and it is a *threshold* effect rather than a distance
      one: `mentioned -> demonstrated` is one rung and still fatal.
    * `missing_prediction = 2.0` — a gold row the caller never answered. Cheap, because the
      code half floors an absent verdict at `mentioned` and the row gets probed; non-zero,
      because silence is not a correct answer.

    The ordering these produce, which is the thing to argue about rather than the numbers:

        led -> none       (3 rungs under)   3.0
        none -> mentioned (1 rung over, below the line)     4.0
        mentioned -> demonstrated (1 rung over, crosses)   10.0
        none -> demonstrated (2 rungs over, crosses)       14.0
        none -> led (3 rungs over, crosses)                18.0

    So the worst under-credit in the set is cheaper than the cheapest over-credit, and the
    reference's own example — "demonstrated" where the truth is "none" — costs 7x the
    reverse. Raise `over_credit_per_rung` if you want distance to matter more than the
    threshold; raise the surcharge if you want the opposite.
    """

    under_credit_per_rung: float = 1.0
    over_credit_per_rung: float = 4.0
    over_credit_crosses_probe_line: float = 6.0
    missing_prediction: float = 2.0


DEFAULT_WEIGHTS = CostWeights()


def row_cost(gold: str, predicted: str | None, weights: CostWeights = DEFAULT_WEIGHTS) -> float:
    """Cost of answering `predicted` when the truth is `gold`. Exact match costs nothing."""
    if predicted is None:
        return weights.missing_prediction
    distance = rank(predicted) - rank(gold)
    if distance == 0:
        return 0.0
    if distance < 0:
        return -distance * weights.under_credit_per_rung
    cost = distance * weights.over_credit_per_rung
    if rank(predicted) >= PROBE_LINE > rank(gold):
        cost += weights.over_credit_crosses_probe_line
    return cost


# ---------------------------------------------------------------------------
# The gold set
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GoldClaim:
    id: str
    candidate: str
    project: str
    skill: str
    quote: str
    gold: str
    why: str
    slices: tuple[str, ...]


@dataclass(frozen=True)
class GoldSet:
    meta: dict
    claims: tuple[GoldClaim, ...]

    def __len__(self) -> int:
        return len(self.claims)

    def __iter__(self):
        return iter(self.claims)

    def slice(self, name: str) -> tuple[GoldClaim, ...]:
        return tuple(c for c in self.claims if name in c.slices)

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(c.id for c in self.claims)


REQUIRED_FIELDS = ("id", "candidate", "project", "skill", "quote", "gold", "why", "slices")


def load_gold(path: Path | str = GOLD_PATH) -> GoldSet:
    """Read the fixture and check its shape. A malformed row is a loud failure, not a skip."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    claims: list[GoldClaim] = []
    seen: set[str] = set()
    for i, row in enumerate(raw["claims"]):
        missing = [f for f in REQUIRED_FIELDS if f not in row]
        if missing:
            raise ValueError(f"gold row {i} ({row.get('id', '?')}) is missing {missing}")
        if row["gold"] not in LEVELS:
            raise ValueError(f"gold row {row['id']}: verdict {row['gold']!r} is not one of {LEVELS}")
        if row["id"] in seen:
            raise ValueError(f"gold row {row['id']}: duplicate id")
        seen.add(row["id"])
        claims.append(
            GoldClaim(
                id=row["id"],
                candidate=row["candidate"],
                project=row["project"],
                skill=row["skill"],
                quote=row["quote"],
                gold=row["gold"],
                why=row["why"],
                slices=tuple(row["slices"]),
            )
        )
    return GoldSet(meta=raw.get("meta", {}), claims=tuple(claims))


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------
@dataclass
class SliceScore:
    """One population of gold rows, scored. The whole set is just the slice named 'all'."""

    name: str
    rows: int = 0
    predicted: int = 0
    missing: int = 0
    exact: int = 0
    over_credit: int = 0
    under_credit: int = 0
    over_cost: float = 0.0
    under_cost: float = 0.0
    missing_cost: float = 0.0
    # matrix[gold][predicted-or-MISSING] -> count
    matrix: dict[str, dict[str, int]] = field(default_factory=dict)
    distance: Counter = field(default_factory=Counter)  # signed rungs moved

    def __post_init__(self) -> None:
        if not self.matrix:
            self.matrix = {g: {p: 0 for p in (*LEVELS, MISSING)} for g in LEVELS}

    @property
    def total_cost(self) -> float:
        return self.over_cost + self.under_cost + self.missing_cost

    @property
    def exact_rate(self) -> float:
        return self.exact / self.rows if self.rows else 0.0

    @property
    def coverage(self) -> float:
        return self.predicted / self.rows if self.rows else 0.0

    @property
    def mean_cost(self) -> float:
        return self.total_cost / self.rows if self.rows else 0.0

    @property
    def matrix_total(self) -> int:
        return sum(sum(r.values()) for r in self.matrix.values())

    def add(self, gold: str, predicted: str | None, cost: float) -> None:
        self.rows += 1
        self.matrix[gold][predicted or MISSING] += 1
        if predicted is None:
            self.missing += 1
            self.missing_cost += cost
            return
        self.predicted += 1
        d = rank(predicted) - rank(gold)
        self.distance[d] += 1
        if d == 0:
            self.exact += 1
        elif d > 0:
            self.over_credit += 1
            self.over_cost += cost
        else:
            self.under_credit += 1
            self.under_cost += cost


@dataclass
class RowResult:
    claim: GoldClaim
    predicted: str | None
    cost: float

    @property
    def distance(self) -> int | None:
        return None if self.predicted is None else rank(self.predicted) - rank(self.claim.gold)


@dataclass
class Cw4Report:
    weights: CostWeights
    overall: SliceScore
    slices: dict[str, SliceScore]
    results: list[RowResult]
    missing_ids: list[str]
    unknown_ids: list[str]

    @property
    def worst(self) -> list[RowResult]:
        """Most expensive rows first — where to look before touching the prompt."""
        return sorted((r for r in self.results if r.cost > 0), key=lambda r: -r.cost)

    def __str__(self) -> str:
        return render(self)


def score(
    predictions: dict[str, str | None],
    gold: GoldSet | None = None,
    *,
    weights: CostWeights = DEFAULT_WEIGHTS,
    slices: tuple[str, ...] = DEFAULT_SLICES,
) -> Cw4Report:
    """Grade a mapping of claim id -> verdict against the gold set.

    A gold row with no prediction is reported (`missing_ids`, the `(missing)` matrix column
    and its own cost line), never dropped. A predicted id that is not in the gold set is
    reported in `unknown_ids` and scored against nothing. A verdict that is not one of the
    four levels raises `ValueError` — that is a caller bug, not a bad answer.
    """
    gold = gold or load_gold()
    known = set(gold.ids)
    unknown = sorted(k for k in predictions if k not in known)

    overall = SliceScore("all")
    per_slice = {name: SliceScore(name) for name in slices}
    results: list[RowResult] = []
    missing_ids: list[str] = []

    for claim in gold:
        predicted = predictions.get(claim.id)
        if predicted is not None and predicted not in LEVELS:
            raise ValueError(f"{claim.id}: predicted verdict {predicted!r} is not one of {LEVELS}")
        if predicted is None:
            missing_ids.append(claim.id)
        cost = row_cost(claim.gold, predicted, weights)
        overall.add(claim.gold, predicted, cost)
        for name in claim.slices:
            if name in per_slice:
                per_slice[name].add(claim.gold, predicted, cost)
        results.append(RowResult(claim=claim, predicted=predicted, cost=cost))

    return Cw4Report(
        weights=weights,
        overall=overall,
        slices=per_slice,
        results=results,
        missing_ids=missing_ids,
        unknown_ids=unknown,
    )


# ---------------------------------------------------------------------------
# Rendering (terminal)
# ---------------------------------------------------------------------------
_RULE = "-" * 72


def _headline(s: SliceScore) -> list[str]:
    if not s.rows:
        return [f"  (no rows in slice {s.name!r})"]
    return [
        f"  rows {s.rows:>3}   predicted {s.predicted:>3}   missing {s.missing:>3}"
        f"   exact {s.exact:>3} ({s.exact_rate:6.1%})",
        f"  cost  {s.total_cost:>7.1f} total   {s.mean_cost:>6.2f} per row"
        f"   |  over-credit {s.over_credit:>3} = {s.over_cost:>6.1f}"
        f"   under-credit {s.under_credit:>3} = {s.under_cost:>6.1f}"
        + (f"   missing = {s.missing_cost:.1f}" if s.missing else ""),
    ]


def _matrix(s: SliceScore) -> list[str]:
    cols = (*LEVELS, MISSING)
    width = max(len(c) for c in cols) + 2
    label = 2 + max(len(g) for g in LEVELS) + 2
    lines = [
        " " * label + "predicted",
        " " * label + "".join(c.rjust(width) for c in cols),
        "  gold",
    ]
    for g in LEVELS:
        row = s.matrix[g]
        total = sum(row.values())
        cells = "".join((str(row[c]) if row[c] else ".").rjust(width) for c in cols)
        lines.append(f"    {g.ljust(label - 4)}{cells}   (n={total})")
    return lines


def _distance(s: SliceScore) -> str:
    if not s.distance:
        return "  rungs moved: (nothing predicted)"
    parts = [
        f"{d:+d}: {s.distance[d]}" if d else f" 0: {s.distance[d]}"
        for d in sorted(s.distance)
    ]
    return "  rungs moved:  " + "   ".join(parts)


def render(report: Cw4Report, *, worst: int = 8) -> str:
    """The whole report as terminal text."""
    w = report.weights
    out: list[str] = [
        "CW-4 claim-evidence verdict - gold-set score",
        _RULE,
        "cost weights (POC choice, not a Caliber number - evals/cw4.py:CostWeights)",
        f"  under-credit {w.under_credit_per_rung:g}/rung   "
        f"over-credit {w.over_credit_per_rung:g}/rung   "
        f"+{w.over_credit_crosses_probe_line:g} when the prediction crosses into "
        f"'demonstrated'/'led'   missing {w.missing_prediction:g}",
        "  rationale: an under-credited skill is probed and recovers; a false 'demonstrated'",
        "             is never assessed again, so it is unrecoverable.",
        _RULE,
        "OVERALL",
        *_headline(report.overall),
        "",
        *_matrix(report.overall),
        "",
        _distance(report.overall),
        _RULE,
        "BY SLICE",
    ]
    for name, s in report.slices.items():
        tag = "  <- the defect class CW-4 exists for" if name == "d10" else ""
        out.append(f"  [{name}]{tag}")
        if not s.rows:
            out.append("    (empty)")
            continue
        out.append(
            f"    rows {s.rows:>3}   exact {s.exact:>3} ({s.exact_rate:6.1%})"
            f"   over {s.over_credit:>3}   under {s.under_credit:>3}"
            f"   missing {s.missing:>3}   cost {s.total_cost:>7.1f}"
            f"   ({s.mean_cost:.2f}/row)"
        )
    out.append(_RULE)

    if report.missing_ids:
        out.append(f"NOT PREDICTED ({len(report.missing_ids)} gold rows, charged "
                   f"{w.missing_prediction:g} each)")
        out.append("  " + ", ".join(report.missing_ids))
    else:
        out.append("NOT PREDICTED: none - every gold row was answered")
    if report.unknown_ids:
        out.append(f"IDS NOT IN THE GOLD SET ({len(report.unknown_ids)}, scored against nothing)")
        out.append("  " + ", ".join(report.unknown_ids))
    out.append(_RULE)

    bad = report.worst[:worst]
    if not bad:
        out.append("WORST ROWS: none - every prediction matched the gold label")
    else:
        out.append(f"WORST ROWS (top {len(bad)} by cost)")
        for r in bad:
            d = r.distance
            move = "missing" if d is None else f"{d:+d} rung(s)"
            pred = r.predicted or MISSING
            slices = ",".join(r.claim.slices) or "-"
            out.append(
                f"  {r.cost:>5.1f}  {r.claim.id}  {r.claim.gold} -> {pred}  ({move})"
                f"  [{slices}]"
            )
            out.append(f"         skill {r.claim.skill!r}: {r.claim.quote[:80]!r}")
    out.append(_RULE)
    out.append(f"gold set: {report.overall.rows} rows, "
               f"{report.slices['d10'].rows if 'd10' in report.slices else 0} in the D10 slice - "
               "SYNTHETIC AND UNREVIEWED (see the fixture's meta.caveat)")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# `python -m evals.cw4` — describe the gold set and self-score it (no model call)
# ---------------------------------------------------------------------------
def _main() -> None:
    gold = load_gold()
    counts = Counter(c.gold for c in gold)
    print(f"{GOLD_PATH.name}: {len(gold)} rows - {gold.meta.get('status', '')}")
    print("  levels: " + "  ".join(f"{lv} {counts[lv]}" for lv in LEVELS))
    slices = Counter(s for c in gold for s in c.slices)
    print("  slices: " + "  ".join(f"{k} {v}" for k, v in sorted(slices.items())))
    print()
    print("A perfect run, to show the report shape:")
    print()
    print(render(score({c.id: c.gold for c in gold}, gold)))


if __name__ == "__main__":  # pragma: no cover
    _main()
