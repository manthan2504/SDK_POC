"""Profile policy — every tunable number and word list the Profiler's code half uses.

Mirrors Caliber's `policy.py` (see reference/plan/ARITHMETIC_RULES.md §0), simplified
for the POC. Rule: no other module hard-codes a threshold or word list that lives here;
change a value → bump POLICY_VERSION.
"""

POLICY_VERSION = "poc-2"

# ---------------------------------------------------------------------------
# Text quality (empty < noise < thin < substantive < specific)
# ---------------------------------------------------------------------------
TIERS = ("empty", "noise", "thin", "substantive", "specific")

MIN_WORDS_ANY = 3  # fewer words than this -> noise
WORDLIKE_NOISE_RATIO = 0.34  # word-like share below this -> noise
WORDLIKE_THIN_RATIO = 0.5  # word-like share below this -> thin (gibberish)
REPEAT_RUN_LIMIT = 4  # a character repeated this many times in a row -> noise
NEAR_DUP_JACCARD = 0.80  # a later project field this similar to an earlier one -> thin (duplicate)

# field -> (min_words, min_chars, specificity, echo tokens that merely restate the question)
FIELD_SPECS: dict[str, tuple[int, int, str | None, frozenset[str]]] = {
    "summary": (6, 20, None, frozenset({"project", "summary", "about", "the", "this"})),
    "responsibilities": (6, 20, None, frozenset({"responsible", "responsibilities", "duties", "for", "my", "i", "was"})),
    "impact": (5, 15, "quantified", frozenset({"impact", "achievements", "achievement", "results", "changed", "the"})),
    "hardest_problem": (8, 25, "decision", frozenset({"hardest", "hard", "problem", "solved", "call", "decision", "the", "i"})),
    "scale": (4, 10, None, frozenset({"scale", "constraints", "constraint", "big", "the"})),
}

# "specific" markers
QUANT_WORDS = frozenset({"doubled", "tripled", "halved", "thousand", "million", "billion", "usd", "gbp", "eur", "inr"})
QUANT_SYMBOLS = frozenset("%$£€₹")  # any digit also counts as quantified
DECISION_WORDS = frozenset({"chose", "chosen", "choose", "decided", "decision", "opted", "picked", "vs", "versus", "rejected", "weighed", "trade-off", "trade-offs", "tradeoff", "tradeoffs"})
DECISION_PHRASES = ("went with", "instead of", "rather than", "ruled out")
CAUSAL_WORDS = frozenset({"because", "since", "otherwise"})
CAUSAL_PHRASES = ("so that", "in order to", "the risk was", "the reason", "would have", "to avoid")

# ---------------------------------------------------------------------------
# Vague skill terms (never a skill; ask the candidate for the specific tools)
# ---------------------------------------------------------------------------
VAGUE_WHOLE = frozenset({
    "cloud", "cloud technologies", "cloud tech", "various", "various tools", "tools", "tooling",
    "technologies", "tech", "frameworks", "libraries", "modern frameworks", "modern tooling",
    "misc", "other", "others", "etc", "devops", "devops tools", "analytics", "analytics tools",
    "reporting tools", "marketing tools", "ms office", "office tools", "productivity tools",
    "databases", "scripting", "automation", "automation tools",
})  # fmt: skip
VAGUE_TOKENS = frozenset({"etc", "various", "misc", "tools", "technologies"})
VAGUE_PHRASES = ("and more", "and others")
KNOWN_TOOLS = frozenset({"etcd", "sketch", "fetch api", "prefetch"})  # look vague, are not

# ---------------------------------------------------------------------------
# Ownership and seniority signals
# ---------------------------------------------------------------------------
LEAD_ROLES = frozenset({"led", "owned", "built_solo"})
SIZABLE_TEAM = 6  # team size at or above this counts as cross-team scope
STRONG_MIN_COUNT = 2  # "strong" needs at least this many instances ...
STRONG_MIN_RATIO = 0.5  # ... and at least this share of the total
DEFENDED_MIN_WORDS = 20  # "ambiguity/defended" needs a decision + a reason + this many words

# ---------------------------------------------------------------------------
# Education (PRD §7.1: captured, weighted low for experienced candidates)
# ---------------------------------------------------------------------------
EDUCATION_FULL_WEIGHT_YEARS = 5  # below this many years, education is asked for

# ---------------------------------------------------------------------------
# Length limits on model-written text (clipped, never rejected)
# ---------------------------------------------------------------------------
MAX_QUOTE_CHARS = 300
MAX_SKILL_CHARS = 120
MAX_LABEL_CHARS = 120  # project names, domains

# --- Signals (added by builder C) ---
# Depth score (0-100, display only — never used in gap size). ARITHMETIC_RULES §0, §3.
DEPTH_BASE: dict[str, int] = {"none": 0, "mentioned": 20, "demonstrated": 55, "led": 75}
DEPTH_CORROBORATION_STEP = 8  # per extra demonstrated-or-better source ...
DEPTH_CORROBORATION_CAP = 16  # ... up to this much
DEPTH_MENTION_STEP = 2  # per extra mention-only source ...
DEPTH_MENTION_CAP = 4  # ... up to this much
DEPTH_QUANTIFIED_BONUS = 5  # any deep source with a quantified impact
DEPTH_RECENCY_ADJ: dict[str, int] = {"current": 4, "recent": 0, "dated": -12, "unknown": -6}
DEPTH_DEEP_STRENGTHS = frozenset({"demonstrated", "led"})

# People-leading language in a role's team quote (leads_people)
PEOPLE_LEAD_WORDS = frozenset({"led", "leading", "managed", "managing", "mentored", "mentoring", "headed", "supervised", "supervising"})
PEOPLE_LEAD_PHRASES = ("reporting to me", "reported to me", "direct reports", "direct report")
TEAM_MEMBER_PHRASES = ("was part of", "member of", "worked in a team", "worked on a team")

# Team size from a team quote (parse_team_size)
MAX_TEAM_SIZE = 10000  # team-size numbers above this are not a headcount
TEAM_SIZE_VERBS = frozenset({"led", "leading", "managed", "managing", "mentored", "mentoring", "headed", "supervised", "hired", "grew"})
# a "<number> <word>" whose word is one of these is not a headcount (time, volume)
NOT_HEADCOUNT_NOUNS = frozenset({
    "years", "year", "months", "month", "weeks", "week", "days", "day", "hours", "hour",
    "minutes", "seconds", "sprints", "quarters", "users", "customers", "clients", "requests",
    "transactions", "records", "rows", "services", "countries", "markets", "sites", "stores",
    "products", "projects", "releases", "percent", "times", "million", "thousand", "billion", "k",
})  # fmt: skip
NUMBER_WORDS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}  # fmt: skip

# --- Review fixes (v1.2) ------------------------------------------------------
# Input limits
MAX_RESUME_CHARS = 60_000  # Caliber's cap on resume text sent to the model
MAX_ANSWERS_CHARS = 20_000  # total characters across all follow-up answers

# Years: flag stated vs dated only beyond max(YEARS_TOLERANCE, YEARS_TOLERANCE_RATIO x stated)
YEARS_TOLERANCE = 2.0
YEARS_TOLERANCE_RATIO = 0.25

# Dates
PRESENT_WORDS = frozenset({"present", "current", "now", "today", "ongoing", "to date", "till date"})
DATE_YEAR_MIN = 1950
DATE_YEAR_MAX = 2100

# Team language: never personal evidence, never supports led / owned / built_solo.
TEAM_WORDS = frozenset({"we", "we've", "we'd", "we're", "our", "ours", "us"})
TEAM_PHRASES = ("my team", "our team", "the team", "as a team", "together with", "team's")
# "led/managed … the team" is the candidate leading people, not team language:
# these verbs directly before a team phrase neutralise it.
TEAM_OBJECT_VERBS = frozenset({"led", "managed", "mentored", "headed", "supervised", "built", "hired", "grew", "coached"})

# Ownership / decision verbs that can support a "led" skill verdict ...
LEAD_VERBS = frozenset({"led", "owned", "chose", "decided", "designed", "architected", "drove", "headed", "spearheaded"})
LEAD_PHRASES = ("responsible for",)
# ... unless used in the passive ("was led by my manager").
PASSIVE_MARKERS = ("led by", "owned by", "decided by", "designed by", "headed by", "chosen by", "driven by",
                   "was led", "were led", "was owned", "was decided", "was designed")

# Grounding: needles this short (or any skill name) must match on word boundaries
SHORT_NEEDLE_CHARS = 3

# Text quality: word-like test
WORDLIKE_MAX_CONSONANT_RUN = 5  # a run of this many consonants -> not a word
ACRONYM_MAX_CHARS = 6  # an all-caps token this short may be an acronym ...
ACRONYM_MAX_SHARE = 0.5  # ... but a text mostly made of all-caps tokens is noise

# --- Signals fixes (v1.2) ---
# leads_people: a people-lead marker counts only when the candidate is its subject.
# Clause boundaries for the subject scan.
LEAD_CLAUSE_BREAKS = ",;.:!?()[]"
# The candidate as subject ("I led ...").
LEAD_SELF_SUBJECTS = frozenset({"i", "i've", "i'd", "myself"})
# A past-participle marker right after one of these is passive ("was managed", "got led").
PASSIVE_AUXILIARIES = frozenset({"was", "were", "been", "being", "is", "are", "am", "be", "got", "get", "gets"})
# Words skipped while looking back from a marker for its subject
# (adverbs, conjunctions, perfect-tense "have", verbs chained with the marker).
LEAD_SUBJECT_ADVERBS = frozenset({
    "also", "then", "later", "successfully", "personally", "directly", "formally", "informally",
    "eventually", "effectively", "subsequently", "currently", "previously", "jointly", "actively",
    "now", "further", "both",
})  # fmt: skip
LEAD_SUBJECT_FILLERS = frozenset({"and", "have", "has", "had", "promoted", "recruited", "formed", "joined", "built", "hired", "grew", "coached"})
# Lead phrases that name the candidate themselves, so need no subject check.
PEOPLE_LEAD_SELF_PHRASES = ("reporting to me", "reported to me")
# "led by me" / "managed by myself" is the candidate leading.
PASSIVE_SELF_AGENTS = frozenset({"me", "myself"})


# ---------------------------------------------------------------------------
# CW-2 elicitation: what each gap is FOR, and how to tell the question still asks it
# ---------------------------------------------------------------------------
# Measured failure (RULEBOOK §16.4): given only a key and a template, Haiku
# rewrote 5 of 8 questions into something adjacent — "What was your focus area?"
# for a gap that needs employment type, team size and whether they led anyone.
# The key was right, so the key check passed and three answers would have come
# back unusable.
#
# Two halves that must agree, so they live side by side:
#   FIELD_PURPOSE   goes INTO the prompt — what a usable answer contains
#   FIELD_ASK_TERMS comes back OUT as the check — a question that mentions none
#                   of these is not asking for this field, whatever it says
# Change one, change the other.

FIELD_PURPOSE: dict[str, str] = {
    "employer": "the company name",
    "title": "the job title they held",
    "start": "the month and year the role began",
    "end": "the month and year it ended, or that it is ongoing",
    "dates": "the start and end dates, which currently disagree",
    "context": "whether the role was full-time, part-time or contract; how many people were on the team; and whether they led anyone",
    "projects": "at least one project: what it was, what they did, and what came of it",
    "role": "which of their roles this project belonged to",
    "your_role": "their own part in it: built it alone, owned the outcome, led others, or contributed to a team",
    "summary": "what the project was, in a sentence or two",
    "responsibilities": "what they personally owned on it, not what the team did",
    "impact": "the measurable result — a number, a rate, a time, a cost",
    "hardest_problem": "the hardest problem and the decision they made about it, not just that it was hard",
    "scale": "how big it was: users, data volume, traffic, or the constraint that made it hard",
    "stack": "the specific named technologies, tools or methods used",
    "processes": "how they worked on it — design review, code review, on-call, pairing, agile ceremonies",
    "vague": "which specific named tools they meant by a term that names none",
    "impact:quantify": "a number attached to the result they already described",
    "hardest_problem:decision": "the decision they made and what they chose it over",
}

# A question for this field must mention at least one of these, as a whole word.
# Deliberately broad: this catches a question about a different subject, not a
# question worded unusually. A false reject only costs the template wording.
FIELD_ASK_TERMS: dict[str, frozenset[str]] = {
    "employer": frozenset({"company", "employer", "organisation", "organization", "firm", "worked"}),
    "title": frozenset({"title", "role", "called", "position"}),
    "start": frozenset({"start", "started", "begin", "began", "when", "month", "year", "join", "joined"}),
    "end": frozenset({"end", "ended", "finish", "finished", "leave", "left", "when", "ongoing", "still"}),
    "dates": frozenset({"start", "end", "date", "dates", "when", "month", "year"}),
    "context": frozenset({"full-time", "part-time", "contract", "permanent", "freelance", "employment",
                          "team", "lead", "led", "leading", "manage", "managed", "report", "reported",
                          "people", "engineers", "many"}),
    "projects": frozenset({"project", "work", "worked", "built", "build"}),
    "role": frozenset({"role", "job", "position", "part of", "belong", "which"}),
    "your_role": frozenset({"your part", "you personally", "alone", "own", "owned", "lead", "led",
                            "contribute", "contributed", "team", "part"}),
    "summary": frozenset({"what", "describe", "about", "project"}),
    "responsibilities": frozenset({"responsible", "responsibility", "responsibilities", "own", "owned",
                                   "personally", "your part", "handled", "did you do"}),
    "impact": frozenset({"result", "impact", "change", "changed", "outcome", "measure", "measurable",
                         "number", "how much", "how many", "improve", "improved", "effect"}),
    "hardest_problem": frozenset({"decide", "decided", "decision", "choose", "chose", "choice",
                                  "trade-off", "tradeoff", "option", "alternative", "instead of",
                                  "over", "call"}),
    "scale": frozenset({"big", "size", "scale", "users", "data", "load", "traffic", "volume",
                        "how many", "how much", "requests", "records", "constraint"}),
    "stack": frozenset({"technolog", "tool", "tools", "language", "framework", "stack", "database",
                        "library", "which", "what"}),
    # NB: "process" itself is deliberately absent. Both the right question ("how
    # did you work") and the wrong one ("what processes did the system automate")
    # contain it, so it discriminates nothing. The concrete practices do.
    "processes": frozenset({"design review", "code review", "review", "on-call", "oncall", "agile",
                            "scrum", "standup", "stand-up", "pairing", "pair", "ci", "testing",
                            "how did you work", "ways of working", "worked on it", "day to day"}),
    "vague": frozenset({"which", "what", "specific", "mean", "tool", "tools"}),
    "impact:quantify": frozenset({"number", "how much", "how many", "figure", "percent", "measure",
                                  "quantif", "put a number"}),
    "hardest_problem:decision": frozenset({"decide", "decided", "decision", "choose", "chose",
                                           "choice", "over", "instead", "alternative", "option"}),
}
