"""Offline tests for the text-quality ladder (app/textquality.py)."""

import pytest

from app import policy
from app.textquality import (
    TextRead,
    at_least,
    is_wordlike,
    near_duplicate,
    read_project_fields,
    read_text,
    tier_rank,
    wordlike_ratio,
)

# --- ladder helpers ---------------------------------------------------------


def test_tier_rank_follows_policy_order():
    assert [tier_rank(t) for t in policy.TIERS] == [0, 1, 2, 3, 4]


@pytest.mark.parametrize(
    "tier, floor, expected",
    [
        ("specific", "substantive", True),
        ("substantive", "substantive", True),
        ("thin", "substantive", False),
        ("empty", "empty", True),
        ("noise", "thin", False),
    ],
)
def test_at_least(tier, floor, expected):
    assert at_least(tier, floor) is expected


@pytest.mark.parametrize(
    "token, expected",
    [
        ("k8s", True),  # digit
        ("API", True),  # short all-caps acronym
        ("Kubernetes", True),  # capitalised, pronounceable
        ("Northwind", True),
        ("REST", True),  # short all-caps acronym
        ("KUBERNETES", True),  # long all-caps: vowel test
        ("Qwrtz", False),  # Title-case no longer auto word-like
        ("Bnmkl", False),
        ("Strengths", False),  # Title-case 5-consonant run
        ("pipeline", True),  # vowel, no long consonant run
        ("rhythm", True),  # y counts as a vowel
        ("xqzt", False),  # no vowel
        ("bcdfg", False),
        ("strengths", False),  # 5-consonant run "ngths"
        ("abcdfgh", False),  # vowel but 6-consonant run
    ],
)
def test_is_wordlike(token, expected):
    assert is_wordlike(token) is expected


def test_wordlike_ratio_empty_is_zero():
    assert wordlike_ratio([]) == 0.0


# --- 1. empty ---------------------------------------------------------------


@pytest.mark.parametrize("text", [None, "", "   ", "\n\t "])
def test_empty(text):
    r = read_text(text, "summary")
    assert r == TextRead("empty", "nothing captured yet", frozenset(), 0)


# --- 2. noise (no tokens / repeat run / word-like ratio) --------------------


@pytest.mark.parametrize("text", ["!!! ??? ...", "---", "@#$%"])
def test_noise_no_tokens(text):
    r = read_text(text)
    assert r.tier == "noise" and r.words == 0


@pytest.mark.parametrize(
    "text",
    ["this is sooooo good really", "aaaa bbbb cccc", "great work zzzzzzzz on the service"],
)
def test_noise_repeated_letters(text):
    assert read_text(text).tier == "noise"


def test_three_repeated_letters_is_not_noise():
    assert read_text("the zzz cache warmed slowly").tier == "substantive"


def test_digit_runs_are_not_noise():
    r = read_text("Grew daily active users to 1000000 within one year", "impact")
    assert r.tier == "specific"


def test_noise_low_wordlike_ratio():
    # 1 of 3 tokens word-like = 0.33 < 0.34
    r = read_text("qwrtp bcdfg hello")
    assert r.tier == "noise"
    assert r.reason == "that doesn't read as a real answer"


# --- 3. noise: too few words ------------------------------------------------


@pytest.mark.parametrize("text, n", [("Kafka", 1), ("built pipelines", 2)])
def test_noise_under_min_words_any(text, n):
    r = read_text(text, "summary")
    assert r.tier == "noise"
    assert r.words == n
    assert "too thin to assess" in r.reason


def test_one_word_reason_is_singular():
    assert read_text("Kafka").reason == "1 word — too thin to assess"


def test_exactly_min_words_any_passes_without_field():
    assert policy.MIN_WORDS_ANY == 3
    r = read_text("Built search tooling")
    assert r.tier == "substantive" and r.words == 3


# --- 4. thin: field floors --------------------------------------------------


def test_thin_under_field_min_words():
    r = read_text("Built a search service quickly", "summary")  # 5 < 6
    assert r.tier == "thin"
    assert r.reason == "say a bit more (6+ words)"
    assert r.flags == frozenset()


def test_exact_field_min_words_passes():
    r = read_text("Built a search service for invoices", "summary")  # exactly 6
    assert r.tier == "substantive"


def test_thin_under_field_min_chars():
    r = read_text("we ran it on a box", "summary")  # 6 words, 18 chars
    assert r.tier == "thin"
    assert r.reason == "say a bit more (20+ characters)"


def test_exact_field_min_chars_passes():
    text = "we ran it on a boxes"
    assert len(text) == 20
    assert read_text(text, "summary").tier == "substantive"


@pytest.mark.parametrize("field", list(policy.FIELD_SPECS))
def test_each_field_uses_its_own_min_words(field):
    min_words = policy.FIELD_SPECS[field][0]
    text = " ".join(["Kafka"] + ["pipeline"] * (min_words - 2))  # min_words - 1 words
    assert read_text(text, field).tier == "thin"


# --- 5. thin: echo ----------------------------------------------------------


def test_echo_restates_question():
    r = read_text("this project is about the project summary", "summary")
    assert r.tier == "thin"
    assert r.flags == frozenset({"echo"})
    assert r.reason == "mostly restates the question"


def test_exactly_half_fresh_is_not_echo():
    # distinct {the, project, about, kafka, pipeline, rewrite}: 3 fresh of 6
    r = read_text("the project about kafka pipeline rewrite", "summary")
    assert r.tier == "substantive"
    assert "echo" not in r.flags


def test_echo_hardest_problem():
    r = read_text("the hardest problem i solved was the hard problem", "hardest_problem")
    assert r.tier == "thin" and "echo" in r.flags


def test_echo_needs_a_field():
    assert read_text("this project is about the project summary").tier == "substantive"


# --- 6. thin: gibberish -----------------------------------------------------


def test_gibberish_between_ratios():
    r = read_text("qwrtp bcdfg hello there zzkxw")  # 2/5 = 0.4
    assert r.tier == "thin"
    assert r.flags == frozenset({"gibberish"})


def test_ratio_exactly_thin_threshold_is_not_gibberish():
    r = read_text("qwrtp bcdfg xqzt hello there nice")  # 3/6 = 0.5
    assert r.tier == "substantive"


# --- 7. specificity ---------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Cut monthly cloud cost by 40 percent overall",  # digit
        "Latency dropped by a large % after the rewrite",  # symbol
        "Saved the team $ on hosting every month",  # currency symbol
        "Checkout conversion doubled after the redesign shipped",  # quant word
        "Served a million users every single day",  # quant word
        "Billing is now reported in USD for every region",  # currency word
    ],
)
def test_impact_quantified(text):
    r = read_text(text, "impact")
    assert r.tier == "specific"
    assert r.flags == frozenset({"quantified"})


def test_impact_without_number_is_substantive():
    r = read_text("Made checkout much faster for every customer", "impact")
    assert r.tier == "substantive"
    assert r.reason == "no number yet"


@pytest.mark.parametrize(
    "text",
    [
        "We chose Postgres over Mongo for the ledger service",  # word
        "Postgres vs Mongo for the ledger was the real question",  # word "vs"
        "The main trade-off was latency against cost for batch jobs",  # hyphenated word
        "We went with a queue for the ingestion path overall",  # phrase
        "Used polling instead of webhooks for the partner sync job",  # phrase
        "We ruled out a rewrite and patched the old parser",  # phrase
    ],
)
def test_hardest_problem_decision(text):
    r = read_text(text, "hardest_problem")
    assert r.tier == "specific"
    assert "decision" in r.flags
    assert "causal" not in r.flags


@pytest.mark.parametrize(
    "text",
    [
        "We picked batching because the upstream API rate limits were strict",
        "We chose a queue so that spikes would not drop any orders",
        "We opted for retries to avoid losing payments during outages",
    ],
)
def test_hardest_problem_decision_and_causal(text):
    r = read_text(text, "hardest_problem")
    assert r.tier == "specific"
    assert r.flags == frozenset({"decision", "causal"})


def test_hardest_problem_causal_without_decision():
    r = read_text("The deploy kept failing because the cache warmed too slowly", "hardest_problem")
    assert r.tier == "substantive"
    assert r.reason == "no decision named yet"
    assert r.flags == frozenset({"causal"})


def test_hardest_problem_plain():
    r = read_text("Debugging a memory leak in the ingestion workers over weeks", "hardest_problem")
    assert r.tier == "substantive"
    assert r.flags == frozenset()


def test_decision_word_must_be_whole_word():
    # "choosey" / "decisions" are not whole-word hits for "choose" / "decision"
    r = read_text("Customers were choosey and the decisions took many long weeks", "hardest_problem")
    assert r.tier == "substantive"


@pytest.mark.parametrize("field", [None, "summary", "responsibilities", "scale", "not_a_field"])
def test_no_specificity_rule_is_substantive(field):
    r = read_text("Cut monthly cloud cost by 40 percent and chose Postgres", field)
    assert r.tier == "substantive"
    assert r.flags == frozenset()


def test_words_counted():
    assert read_text("Built a search service for invoices", "summary").words == 6


# --- near duplicates --------------------------------------------------------


@pytest.mark.parametrize(
    "a, b, expected",
    [
        ("Built the search service", "built the SEARCH service!", True),
        ("alpha beta gamma delta epsilon", "alpha beta gamma delta", True),  # 4/5 = 0.8
        ("alpha beta gamma delta epsilon", "alpha beta gamma zeta", False),  # 3/6
        ("Built the search service", "Ran the billing migration", False),
        (None, "anything", False),
        ("", "", False),
        ("!!!", "!!!", False),
    ],
)
def test_near_duplicate(a, b, expected):
    assert near_duplicate(a, b) is expected


# --- project fields ---------------------------------------------------------

SUMMARY = "Built an internal search service for support tickets"
RESP = "Owned the indexing pipeline and the query API for agents"
IMPACT = "Cut average ticket handling time by 30 percent"
HARD = "We chose hybrid search over pure vectors because recall on codes was poor"
SCALE = "Two million tickets across four regions"


def test_project_fields_clean():
    reads = read_project_fields(
        {"summary": SUMMARY, "responsibilities": RESP, "impact": IMPACT, "hardest_problem": HARD, "scale": SCALE}
    )
    assert {k: r.tier for k, r in reads.items()} == {
        "summary": "substantive",
        "responsibilities": "substantive",
        "impact": "specific",
        "hardest_problem": "specific",
        "scale": "substantive",
    }


def test_only_present_fields_are_read():
    reads = read_project_fields({"impact": None, "extra": "ignored text here"})
    assert set(reads) == {"impact"}
    assert reads["impact"].tier == "empty"


def test_later_duplicate_is_demoted():
    reads = read_project_fields({"summary": SUMMARY, "responsibilities": SUMMARY})
    assert reads["summary"].tier == "substantive"
    r = reads["responsibilities"]
    assert r.tier == "thin"
    assert r.flags == frozenset({"duplicate"})
    assert r.reason == "repeats the summary answer almost word for word"


def test_duplicate_names_the_matching_earlier_field():
    reads = read_project_fields({"summary": SUMMARY, "impact": HARD, "hardest_problem": HARD})
    assert reads["impact"].tier == "substantive"  # the earlier one keeps its tier
    assert reads["hardest_problem"].tier == "thin"
    assert reads["hardest_problem"].reason == "repeats the impact answer almost word for word"


def test_order_is_fixed_not_dict_order():
    # Dict lists hardest_problem first, but summary is still the "earlier" field.
    reads = read_project_fields({"hardest_problem": SUMMARY, "summary": SUMMARY})
    assert reads["summary"].tier == "substantive"
    assert "duplicate" in reads["hardest_problem"].flags


def test_scale_is_excluded_from_duplicates():
    reads = read_project_fields({"summary": SCALE + " overall", "scale": SCALE + " overall"})
    assert reads["scale"].tier == "substantive"
    assert "duplicate" not in reads["scale"].flags


def test_already_thin_field_is_not_relabelled():
    reads = read_project_fields({"summary": SUMMARY, "impact": "support tickets"})
    assert reads["impact"].tier == "noise"
    assert "duplicate" not in reads["impact"].flags


def test_duplicate_of_a_thin_earlier_field_still_counts():
    thin = "Built search for support tickets"  # 5 words < 6 → thin summary
    reads = read_project_fields({"summary": thin, "impact": thin + " fast"})
    assert reads["summary"].tier == "thin"
    # impact: 6 words, Jaccard 5/6 ≥ 0.8 with the summary
    assert reads["impact"].tier == "thin"
    assert "duplicate" in reads["impact"].flags


# --- v1.2: capitalised gibberish --------------------------------------------


def test_title_case_gibberish_is_not_substantive():
    r = read_text("Qwrtz Bnmkl Asdfg Hjklp Zxcvb Plmnk Tyuio Rewqz Gfdsa", "summary")
    assert not at_least(r.tier, "substantive")


def test_all_caps_gibberish_is_noise():
    r = read_text("ASDF QWER ZXCV TYUI GHJK BNML 42", "impact")
    assert r.tier == "noise"
    assert r.reason == "that doesn't read as a real answer"


def test_caps_share_needs_no_lowercase_word():
    # mostly caps but one lowercase word -> not the caps-noise rule
    assert read_text("AWS ECS RDS SQS on", None).tier == "substantive"


@pytest.mark.parametrize(
    "text, field, tier",
    [
        ("Built REST APIs on AWS ECS for the billing team", "summary", "substantive"),
        ("Cut p95 latency from 900ms to 120ms", "impact", "specific"),
        ("Led search at Northwind Health for three years", None, "substantive"),
        ("Joined Kestrel Analytics to build the ingestion platform", "summary", "substantive"),
    ],
)
def test_real_sentences_still_pass(text, field, tier):
    assert read_text(text, field).tier == tier


# --- v1.2: dedupe only candidate-typed fields -------------------------------


def test_dedupe_fields_limits_demotion():
    fields = {"summary": SUMMARY, "impact": SUMMARY}
    reads = read_project_fields(fields, dedupe_fields={"hardest_problem"})
    assert reads["impact"].tier == "substantive"
    assert "duplicate" not in reads["impact"].flags


def test_dedupe_fields_named_field_is_demoted():
    fields = {"summary": SUMMARY, "impact": SUMMARY}
    reads = read_project_fields(fields, dedupe_fields=frozenset({"impact"}))
    assert reads["impact"].tier == "thin"
    assert "duplicate" in reads["impact"].flags


def test_dedupe_fields_none_keeps_old_behaviour():
    fields = {"summary": SUMMARY, "impact": SUMMARY}
    assert read_project_fields(fields, None) == read_project_fields(fields)
    assert "duplicate" in read_project_fields(fields)["impact"].flags


def test_undeduped_field_still_counts_as_earlier():
    # summary is not candidate-typed, but a typed later field copying it is demoted
    fields = {"summary": SUMMARY, "responsibilities": SUMMARY}
    reads = read_project_fields(fields, dedupe_fields={"responsibilities"})
    assert reads["summary"].tier == "substantive"
    assert "duplicate" in reads["responsibilities"].flags
