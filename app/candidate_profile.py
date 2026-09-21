"""Profiler arithmetic — the code half of step [1] (RULEBOOK §7 row 1, §9, §13; PRD v1.7 §7.1).

The model only *reads* the candidate's material (ProfileDraft v2). Everything with a
computable answer happens here:

  1. grounding    — every copied field and quote must be verbatim in the candidate's text
                    (resume and/or answers), or it is dropped (never fuzzy-accepted);
  2. dates        — raw strings like "Apr 2023" / "Present" are parsed here, never by the model;
  3. years        — dated years from the role spans; the candidate's stated years win (D6),
                    a mismatch is flagged, never silently corrected;
  4. recency      — current / recent / dated / unknown, window from data/config/scoring.yaml;
  5. project role — `your_role` stands only on a verified quote; team language never
                    supports led / owned / built_solo;
  6. evidence     — weaker-wins: final = min(agent verdict, code cap), floored at "mentioned";
                    vague stack items ("various tools") are never skills;
  7. signals      — ownership level, seniority signals, per-skill depth score (app.signals);
  8. completeness — what the app must ask: required items (missing or too thin, judged by
                    app.textquality) and optional nudges. The model never decides completeness.

All thresholds and word lists live in app.policy / data/config.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.policy import (
    DATE_YEAR_MAX,
    DATE_YEAR_MIN,
    LEAD_PHRASES,
    LEAD_ROLES,
    LEAD_VERBS,
    MAX_LABEL_CHARS,
    MAX_QUOTE_CHARS,
    MAX_SKILL_CHARS,
    NUMBER_WORDS,
    PASSIVE_MARKERS,
    POLICY_VERSION,
    PRESENT_WORDS,
    TEAM_OBJECT_VERBS,
    TEAM_PHRASES,
    TEAM_WORDS,
    YEARS_TOLERANCE,
    YEARS_TOLERANCE_RATIO,
)
from app.rules import recent_window_months
from app.schemas import (
    EducationEntry,
    ProfileDraft,
    ProjectEntry,
    ProjectRole,
    RoleEntry,
    SkillClaim,
    Verdict,
)
from app.signals import (
    ProjectFacts,
    RoleFacts,
    depth_score,
    education_weight,
    leads_people,
    ownership,
    parse_team_size,
    seniority_signals,
)
from app.textmatch import GroundingText, mentions, normalise_for_match
from app.textquality import TextRead, at_least, read_project_fields
from app.vague import is_vague_skill, vague_reason

Recency = Literal["current", "recent", "dated", "unknown"]

EVIDENCE_ORDER: tuple[Verdict, ...] = ("none", "mentioned", "demonstrated", "led")
_RECENCY_RANK: dict[str, int] = {"unknown": 0, "dated": 1, "recent": 2, "current": 3}
PROJECT_TEXT_FIELDS = ("summary", "responsibilities", "impact", "hardest_problem", "scale")


def evidence_rank(level: Verdict) -> int:
    return EVIDENCE_ORDER.index(level)


# ---------------------------------------------------------------------------
# App-owned records (never sent to the model)
# ---------------------------------------------------------------------------
class Role(BaseModel):
    role_id: str
    employer: str | None
    title: str | None
    start_raw: str | None
    end_raw: str | None
    is_current: bool
    employment_type: str | None = None
    domain: str | None = None  # a label, not a quote
    team_quote: str | None = None
    team_size: int | None = None  # parsed from team_quote
    led_team: bool | None = None  # people-leading language in team_quote
    start: str | None = None  # "YYYY-MM"
    end: str | None = None  # "YYYY-MM"; None when current or unknown
    months: int | None = None
    recency: Recency = "unknown"


class FieldQuality(BaseModel):
    tier: str  # empty / noise / thin / substantive / specific
    reason: str
    flags: list[str] = Field(default_factory=list)


class Project(BaseModel):
    project_id: str
    role_id: str | None
    name: str | None  # a label, not a quote
    summary: str | None
    role_quote: str | None = None
    your_role: ProjectRole | None = None
    responsibilities: str | None = None
    impact: str | None = None
    hardest_problem: str | None = None
    scale: str | None = None
    processes: list[str] = Field(default_factory=list)
    stack: list[str] = Field(default_factory=list)  # concrete technologies only
    vague_stack: list[str] = Field(default_factory=list)  # "various tools" etc. — asked about
    quality: dict[str, FieldQuality] = Field(default_factory=dict)


class Education(BaseModel):
    institution: str | None
    qualification: str | None
    end_year: str | None


class SkillEvidence(BaseModel):
    name: str
    evidence: Verdict
    quote: str | None  # the quote behind the strongest verified claim
    project_ids: list[str] = Field(default_factory=list)
    recency: Recency = "unknown"
    # The text read as stronger than the evidence could verify: assess this first.
    probe_first: bool = False
    depth_score: int = 0  # 0–100, display only (never used in gap size)
    depth_basis: str = ""


class MissingField(BaseModel):
    key: str
    question: str
    required: bool = True  # False = an optional nudge that never blocks confirmation
    reason: str = "missing"  # missing / thin / noise / vague / refine


class GroundingReport(BaseModel):
    dropped_fields: list[str] = Field(default_factory=list)  # copied values not in the text
    dropped_claims: list[str] = Field(default_factory=list)  # skills not in the text, or vague
    capped_claims: list[str] = Field(default_factory=list)  # skill verdicts lowered by the code cap
    capped_roles: list[str] = Field(default_factory=list)  # project roles lowered (team language)
    notes: list[str] = Field(default_factory=list)  # other inconsistencies


class OwnershipInfo(BaseModel):
    level: Literal["leader", "owner", "contributor"]
    basis: str


class SignalInfo(BaseModel):
    tier: Literal["none", "some", "strong"]
    count: int
    total: int
    basis: str


class CandidateProfile(BaseModel):
    roles: list[Role]
    projects: list[Project]
    skills: list[SkillEvidence]
    educations: list[Education]
    years_experience: float | None  # stated years if given, else dated years (D6)
    stated_years: float | None
    dated_years: float | None
    years_mismatch: bool
    ownership: OwnershipInfo
    seniority: dict[str, SignalInfo]
    missing_fields: list[MissingField]
    grounding: GroundingReport
    policy_version: str = POLICY_VERSION

    @property
    def required_missing(self) -> list[MissingField]:
        return [m for m in self.missing_fields if m.required]

    @property
    def is_complete(self) -> bool:
        """The completeness gate: nothing required is missing or too thin (nudges don't block)."""
        return not self.required_missing


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}  # fmt: skip
_NAMED = re.compile(r"^(?P<m>[a-z]+)\.?\s*,?\s*(?P<y>\d{4})$")
_NUM_MY = re.compile(r"^(?P<m>\d{1,2})\s*[/.-]\s*(?P<y>\d{4})$")
_NUM_YM = re.compile(r"^(?P<y>\d{4})\s*[/.-]\s*(?P<m>\d{1,2})$")
_YEAR = re.compile(r"^(?P<y>\d{4})$")


def is_present(raw: str | None) -> bool:
    return bool(raw) and normalise_for_match(raw) in PRESENT_WORDS


def parse_raw_date(raw: str | None, *, is_end: bool = False) -> tuple[int, int] | None:
    """'Apr 2023' -> (2023, 4); '2019' -> (2019, 1) as a start, (2019, 12) as an end."""
    if not raw:
        return None
    text = normalise_for_match(raw)
    year = month = None
    if m := _NAMED.match(text):
        month, year = _MONTHS.get(m["m"]), int(m["y"])
    elif m := _NUM_MY.match(text) or _NUM_YM.match(text):
        month, year = int(m["m"]), int(m["y"])
    elif m := _YEAR.match(text):
        month, year = (12 if is_end else 1), int(m["y"])
    if month is None or year is None or not 1 <= month <= 12 or not DATE_YEAR_MIN <= year <= DATE_YEAR_MAX:
        return None
    return year, month


def _idx(ym: tuple[int, int]) -> int:
    return ym[0] * 12 + (ym[1] - 1)


def _fmt(ym: tuple[int, int] | None) -> str | None:
    return f"{ym[0]:04d}-{ym[1]:02d}" if ym else None


# ---------------------------------------------------------------------------
# Evidence cap (code side of weaker-wins)
# ---------------------------------------------------------------------------
# Language markers (app.policy), not role content (FR-I5 safe). POC heuristic, see RULEBOOK §13.
_WORD = re.compile(r"[a-z0-9']+")
# "led the team" / "managed my team of 6": the candidate leading people, not team language.
_TEAM_AS_OBJECT = re.compile(
    r"\b(?:" + "|".join(sorted(TEAM_OBJECT_VERBS)) + r")\s+(?:(?:the|my|our|a|an)\s+)?(?:[\w-]+\s+)?team(?:'s)?\b"
)


def _has_phrase(text: str, phrase: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text) is not None


def has_team_language(text: str | None) -> bool:
    """"We", "our", "my team", "the team" … — but not the object of "I led the team"."""
    if not text:
        return False
    q = _TEAM_AS_OBJECT.sub(" ", normalise_for_match(text))
    return bool(set(_WORD.findall(q)) & TEAM_WORDS) or any(_has_phrase(q, p) for p in TEAM_PHRASES)


def has_lead_language(text: str | None) -> bool:
    """An ownership/decision verb in the active voice ("was led by my manager" does not count)."""
    if not text:
        return False
    q = normalise_for_match(text)
    for marker in PASSIVE_MARKERS:
        q = re.sub(r"(?<!\w)" + re.escape(marker) + r"(?!\w)", " ", q)
    return bool(set(_WORD.findall(q)) & LEAD_VERBS) or any(_has_phrase(q, p) for p in LEAD_PHRASES)


def evidence_cap(skill: str, quote: str | None, quote_verified: bool) -> Verdict:
    """The strongest verdict this quote can support, whatever the model said.

    * no verified quote, or the quote is about something else  -> mentioned
    * team language ("we", "the team") is not personal evidence -> mentioned
    * an ownership/decision verb                                -> led
    * otherwise the candidate did something with it             -> demonstrated
    """
    if not quote_verified or not mentions(quote, skill):
        return "mentioned"
    if has_team_language(quote):
        return "mentioned"
    if has_lead_language(quote):
        return "led"
    return "demonstrated"


def final_evidence(agent: Verdict | None, cap: Verdict) -> Verdict:
    """Weaker of agent and cap, never below 'mentioned' (the skill is in the text)."""
    agent_rank = evidence_rank(agent) if agent else evidence_rank("mentioned")
    chosen = min(agent_rank, evidence_rank(cap))
    return EVIDENCE_ORDER[max(chosen, evidence_rank("mentioned"))]


def project_role(your_role: ProjectRole | None, role_quote: str | None) -> ProjectRole | None:
    """A lead-type role (led / owned / built_solo) never stands on team language."""
    if your_role in LEAD_ROLES and has_team_language(role_quote):
        return "contributed"
    return your_role


# ---------------------------------------------------------------------------
# Building the profile
# ---------------------------------------------------------------------------
def _clip(value: str | None, limit: int) -> str | None:
    """Clip over-long model text (never reject). A clipped quote is still a prefix of a verified quote."""
    if value is None or len(value) <= limit:
        return value
    return value[:limit].rstrip()


def _clip_around(quote: str | None, term: str, limit: int) -> str | None:
    """Clip a long verified quote to a window that still contains `term` (still a substring)."""
    if quote is None or len(quote) <= limit:
        return quote
    i = quote.casefold().find(term.casefold())
    if i < 0:
        return quote[:limit].rstrip()
    start = max(0, min(i - (limit - len(term)) // 2, len(quote) - limit))
    return quote[start:start + limit].strip()


def _ground_field(value: str | None, text: GroundingText, where: str, report: GroundingReport) -> str | None:
    if value is None or value.strip() == "":
        return None
    if text.contains(value):
        return _clip(value, MAX_QUOTE_CHARS)
    report.dropped_fields.append(f"{where}: {value!r} is not in the candidate's text")
    return None


def unique_ids(raw_ids: list[str | None], prefix: str) -> list[str]:
    """Keep each model id once; give a missing/duplicate id the smallest number no other entry uses."""
    reserved = {i for i in raw_ids if i}
    seen: set[str] = set()
    out: list[str] = []
    for rid in raw_ids:
        if rid and rid not in seen:
            new = rid
        else:
            k = 1
            while f"{prefix}{k}" in seen or f"{prefix}{k}" in reserved:
                k += 1
            new = f"{prefix}{k}"
        seen.add(new)
        out.append(new)
    return out


def _ground_list(
    values: Iterable[str] | None, text: GroundingText, where: str, report: GroundingReport, *, terms: bool = False
) -> list[str]:
    """Grounded, de-duplicated items. `terms=True` (stack items) needs whole-term matches."""
    out: list[str] = []
    keys: set[str] = set()
    for item in values or []:
        if terms and item and item.strip() and not text.contains_term(item):
            report.dropped_fields.append(f"{where}: {item!r} is not in the candidate's text as a whole term")
            continue
        grounded = _ground_field(item, text, where, report)
        if grounded and normalise_for_match(grounded) not in keys:
            keys.add(normalise_for_match(grounded))
            out.append(grounded)
    return out


def _build_roles(entries: Iterable[RoleEntry], text: GroundingText, today: date, report: GroundingReport) -> list[Role]:
    entries = list(entries)
    roles: list[Role] = []
    window = recent_window_months()
    today_ym = (today.year, today.month)
    for e, rid in zip(entries, unique_ids([e.role_id for e in entries], "r")):
        where = f"role {rid}"
        start_raw = _ground_field(e.start_raw, text, f"{where} start_raw", report)
        end_raw = _ground_field(e.end_raw, text, f"{where} end_raw", report)
        is_current = bool(e.is_current) or is_present(end_raw)
        end_raw_for_parse = None if is_present(end_raw) else end_raw
        if end_raw_for_parse and e.is_current:
            # a dated end beats a stray is_current flag
            report.notes.append(f"{where}: has an end date and is_current; treated as ended")
            is_current = False
        team_quote = _ground_field(e.team_quote, text, f"{where} team_quote", report)
        role = Role(
            role_id=rid,
            employer=_ground_field(e.employer_raw, text, f"{where} employer_raw", report),
            title=_ground_field(e.title_raw, text, f"{where} title_raw", report),
            start_raw=start_raw,
            end_raw=end_raw,
            is_current=is_current,
            employment_type=_ground_field(e.employment_type_raw, text, f"{where} employment_type_raw", report),
            domain=_clip(e.domain, MAX_LABEL_CHARS),
            team_quote=team_quote,
            team_size=parse_team_size(team_quote),
            led_team=leads_people(team_quote),
        )
        start = parse_raw_date(start_raw)
        end = today_ym if is_current else parse_raw_date(end_raw_for_parse, is_end=True)
        if end and _idx(end) > _idx(today_ym):
            report.notes.append(f"{where}: end date {_fmt(end)} is in the future; counted up to today")
            end = today_ym
        role.start = _fmt(start)
        role.end = None if is_current else _fmt(end)
        if start and end:
            months = _idx(end) - _idx(start) + 1
            if months > 0:
                role.months = months
            else:
                report.notes.append(f"{where}: start is after end; span unknown")
        if is_current:
            role.recency = "current"
        elif end:
            role.recency = "recent" if _idx(today_ym) - _idx(end) <= window else "dated"
        roles.append(role)
    return roles


def _quality(read: TextRead) -> FieldQuality:
    return FieldQuality(tier=read.tier, reason=read.reason, flags=sorted(read.flags))


def _build_projects(
    entries: Iterable[ProjectEntry],
    roles: list[Role],
    text: GroundingText,
    report: GroundingReport,
    typed: GroundingText | None = None,
) -> list[Project]:
    entries = list(entries)
    role_ids = {r.role_id for r in roles}
    projects: list[Project] = []
    for e, pid in zip(entries, unique_ids([e.project_id for e in entries], "p")):
        where = f"project {pid}"
        role_id = e.role_id if e.role_id in role_ids else None
        if e.role_id and role_id is None:
            report.notes.append(f"{where}: role_id {e.role_id!r} does not exist")

        # Project role: only on a verified quote; lead-type never on team language.
        role_quote = _ground_field(e.role_quote, text, f"{where} role_quote", report)
        your_role: ProjectRole | None = None
        if e.your_role and role_quote:
            your_role = project_role(e.your_role, role_quote)
            if your_role != e.your_role:
                report.capped_roles.append(f"{where} your_role: {e.your_role} -> {your_role} (team language)")
        elif e.your_role:
            report.dropped_fields.append(f"{where} your_role: {e.your_role!r} has no verified quote")

        # Stack: grounded, then vague items split off (they are asked about, never skills).
        grounded_stack = []
        for item in _ground_list(e.stack, text, f"{where} stack", report, terms=True):
            if len(item) > MAX_SKILL_CHARS:
                report.dropped_fields.append(f"{where} stack: {item[:40]!r}… is longer than {MAX_SKILL_CHARS} characters")
            else:
                grounded_stack.append(item)
        stack = [s for s in grounded_stack if not is_vague_skill(s)]
        vague = [s for s in grounded_stack if is_vague_skill(s)]

        texts = {
            "summary": _ground_field(e.summary_quote, text, f"{where} summary_quote", report),
            "responsibilities": _ground_field(e.responsibilities_quote, text, f"{where} responsibilities_quote", report),
            "impact": _ground_field(e.impact_quote, text, f"{where} impact_quote", report),
            "hardest_problem": _ground_field(e.hardest_problem_quote, text, f"{where} hardest_problem_quote", report),
            "scale": _ground_field(e.scale_quote, text, f"{where} scale_quote", report),
        }
        # Near-duplicate answers are only demoted when the candidate typed them; one resume
        # bullet legitimately serves as both summary and impact.
        dedupe = None if typed is None else {f for f, t in texts.items() if t and typed.contains(t)}
        reads = read_project_fields(texts, dedupe_fields=dedupe)
        projects.append(
            Project(
                project_id=pid,
                role_id=role_id,
                name=_clip(e.name, MAX_LABEL_CHARS),
                summary=texts["summary"],
                role_quote=role_quote,
                your_role=your_role,
                responsibilities=texts["responsibilities"],
                impact=texts["impact"],
                hardest_problem=texts["hardest_problem"],
                scale=texts["scale"],
                processes=_ground_list(e.processes, text, f"{where} processes", report),
                stack=stack,
                vague_stack=vague,
                quality={f: _quality(reads[f]) for f in PROJECT_TEXT_FIELDS},
            )
        )
    return projects


def _build_skills(
    claims: Iterable[SkillClaim],
    projects: list[Project],
    roles: list[Role],
    text: GroundingText,
    report: GroundingReport,
) -> list[SkillEvidence]:
    by_project = {p.project_id: p for p in projects}
    recency_of_role = {r.role_id: r.recency for r in roles}

    def project_recency(pid: str | None) -> Recency:
        p = by_project.get(pid or "")
        return recency_of_role.get(p.role_id, "unknown") if p and p.role_id else "unknown"

    def quantified(pid: str | None) -> bool:
        p = by_project.get(pid or "")
        return bool(p) and "quantified" in p.quality["impact"].flags

    # Caliber "claimed but weak": a lead-type role with no named decision behind it is probed first.
    weak_claim = {
        p.project_id
        for p in projects
        if p.your_role in LEAD_ROLES and p.quality["hardest_problem"].tier != "specific"
    }
    merged: dict[str, SkillEvidence] = {}
    # per skill, per project: the strongest (level, quantified) — one depth source per project
    sources: dict[str, dict[str, tuple[Verdict, bool]]] = {}
    claimed: set[tuple[str, str]] = set()

    def add(name: str, level: Verdict, quote: str | None, pid: str | None, probe: bool) -> None:
        key = normalise_for_match(name)
        if pid:
            prev = sources.setdefault(key, {}).get(pid)
            if prev is None or evidence_rank(level) > evidence_rank(prev[0]):
                sources[key][pid] = (level, quantified(pid))
        probe = probe or (pid in weak_claim)
        rec = project_recency(pid)
        cur = merged.get(key)
        if cur is None:
            merged[key] = SkillEvidence(
                name=name, evidence=level, quote=quote, recency=rec, probe_first=probe,
                project_ids=[pid] if pid else [],
            )
            return
        if evidence_rank(level) > evidence_rank(cur.evidence):
            cur.evidence, cur.quote = level, quote
        if pid and pid not in cur.project_ids:
            cur.project_ids.append(pid)
        if _RECENCY_RANK[rec] > _RECENCY_RANK[cur.recency]:
            cur.recency = rec
        cur.probe_first = cur.probe_first or probe

    for c in claims:
        if not c.skill or not text.contains_term(c.skill):
            report.dropped_claims.append(f"skill {c.skill!r}: not in the candidate's text")
            continue
        if is_vague_skill(c.skill):
            report.dropped_claims.append(f"skill {c.skill!r}: too general to count as a skill")
            continue
        if len(c.skill) > MAX_SKILL_CHARS:
            report.dropped_claims.append(f"skill {c.skill[:40]!r}…: longer than {MAX_SKILL_CHARS} characters")
            continue
        pid = c.project_id if c.project_id in by_project else None
        quote_ok = text.contains(c.quote)
        cap = evidence_cap(c.skill, c.quote, quote_ok)
        level = final_evidence(c.verdict, cap)
        agent = c.verdict or "mentioned"
        if evidence_rank(level) < evidence_rank(agent):
            why = "quote not in text" if not quote_ok else f"quote supports at most {cap!r}"
            report.capped_claims.append(f"skill {c.skill!r}: {agent} -> {level} ({why})")
        probe = agent in ("demonstrated", "led") and evidence_rank(level) < evidence_rank(agent)
        add(c.skill, level, _clip_around(c.quote, c.skill, MAX_QUOTE_CHARS) if quote_ok else None, pid, probe)
        if pid:
            claimed.add((pid, normalise_for_match(c.skill)))

    # A technology listed in a project's stack is at least "mentioned" (a dated fact).
    for p in projects:
        for item in p.stack:
            if (p.project_id, normalise_for_match(item)) not in claimed:
                add(item, "mentioned", None, p.project_id, False)

    for key, skill in merged.items():
        srcs = list(sources.get(key, {}).values()) or [(skill.evidence, False)]
        skill.depth_score, skill.depth_basis = depth_score(srcs, skill.recency)

    return sorted(merged.values(), key=lambda s: (-evidence_rank(s.evidence), s.name.casefold()))


def _build_educations(entries: Iterable[EducationEntry], text: GroundingText, report: GroundingReport) -> list[Education]:
    out: list[Education] = []
    for n, e in enumerate(entries, start=1):
        where = f"education {n}"
        edu = Education(
            institution=_ground_field(e.institution_raw, text, f"{where} institution_raw", report),
            qualification=_ground_field(e.qualification_raw, text, f"{where} qualification_raw", report),
            end_year=_ground_field(e.end_year_raw, text, f"{where} end_year_raw", report),
        )
        if edu.institution or edu.qualification:
            out.append(edu)
    return out


_YEARS_NUM = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b")
_BARE_NUM = re.compile(r"^(\d+(?:\.\d+)?)\s*\+?$")
_NUMBER_WORD = re.compile(r"\b(" + "|".join(NUMBER_WORDS) + r")\b")


def parse_stated_years(raw: str | None) -> float | None:
    """"6 years", "5+ yrs", "six years", or just "6" (the field *is* a statement of total years)."""
    if not raw:
        return None
    text = _NUMBER_WORD.sub(lambda m: str(NUMBER_WORDS[m.group(1)]), normalise_for_match(raw))
    m = _YEARS_NUM.search(text) or _BARE_NUM.match(text)
    return float(m.group(1)) if m else None


def years_mismatch(stated: float | None, dated: float | None) -> bool:
    """Flag (never correct) a gap wider than max(2 years, 25% of the stated years)."""
    if stated is None or dated is None:
        return False
    return abs(stated - dated) > max(YEARS_TOLERANCE, YEARS_TOLERANCE_RATIO * stated)


def dated_years(roles: list[Role]) -> float | None:
    """Union of dated role spans (overlaps counted once), in years to 1 dp."""
    months: set[int] = set()
    for r in roles:
        if r.start and r.months:
            y, m = map(int, r.start.split("-"))
            start = _idx((y, m))
            months.update(range(start, start + r.months))
    return round(len(months) / 12, 1) if months else None


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------
def _signals(roles: list[Role], projects: list[Project]) -> tuple[OwnershipInfo, dict[str, SignalInfo]]:
    role_facts = [RoleFacts(role_id=r.role_id, led_team=r.led_team, team_size=r.team_size) for r in roles]
    project_facts = [
        ProjectFacts(
            project_id=p.project_id,
            role_id=p.role_id,
            your_role=p.your_role,
            scale_tier=p.quality["scale"].tier,
            hardest_tier=p.quality["hardest_problem"].tier,
            hardest_flags=frozenset(p.quality["hardest_problem"].flags),
            hardest_words=len((p.hardest_problem or "").split()),
        )
        for p in projects
    ]
    own = ownership(role_facts, project_facts)
    sig = seniority_signals(role_facts, project_facts)
    return (
        OwnershipInfo(level=own.level, basis=own.basis),
        {k: SignalInfo(tier=v.tier, count=v.count, total=v.total, basis=v.basis) for k, v in sig.items()},
    )


# ---------------------------------------------------------------------------
# Completeness (PRD §7.1: "flag thin areas"; impact and hardest problem always asked)
# ---------------------------------------------------------------------------
_PROJECT_ASKS = {
    "summary": "In a sentence or two, what was '{label}'?",
    "responsibilities": "What were you personally responsible for on '{label}'?",
    "impact": "What was the measurable result of '{label}'?",
    "hardest_problem": "What was the hardest problem you solved on '{label}', and what did you decide?",
    "scale": "How big was '{label}' — users, data, load or other constraints?",
}


def _ask_text(missing: list[MissingField], key: str, question: str, read: FieldQuality) -> None:
    """Required unless the answer is substantive; a thin/noise answer is re-asked with the reason."""
    if at_least(read.tier, "substantive"):  # type: ignore[arg-type]
        return
    if read.tier == "empty":
        missing.append(MissingField(key=key, question=question, reason="missing"))
    else:
        missing.append(
            MissingField(key=key, question=f"{question} (Your answer so far: {read.reason}.)", reason=read.tier)
        )


def _missing_fields(
    roles: list[Role],
    projects: list[Project],
    educations: list[Education],
    years_experience: float | None,
) -> list[MissingField]:
    missing: list[MissingField] = []
    if not roles:
        missing.append(MissingField(key="roles", question="Please add your work experience: employer, job title and dates for each role."))
    for r in roles:
        label = r.title or r.employer or r.role_id
        if not r.employer:
            missing.append(MissingField(key=f"role:{r.role_id}:employer", question=f"Which employer was your '{label}' role with?"))
        if not r.title:
            missing.append(MissingField(key=f"role:{r.role_id}:title", question=f"What was your job title at {r.employer or label}?"))
        if not r.start:
            missing.append(MissingField(key=f"role:{r.role_id}:start", question=f"When did your '{label}' role start (month and year)?"))
        if not r.is_current and not r.end:
            missing.append(MissingField(key=f"role:{r.role_id}:end", question=f"When did your '{label}' role end, or is it ongoing?"))
        if r.start and (r.is_current or r.end) and r.months is None:
            missing.append(MissingField(key=f"role:{r.role_id}:dates", question=f"The dates for your '{label}' role look inconsistent. When did it start and end?"))
        # Optional nudge (POC choice): the PRD's team context / employment type / domain.
        gaps = [
            what
            for what, have in (
                ("was it full-time, part-time or contract", r.employment_type),
                ("what business area was it in", r.domain),
                ("how big was the team, and did you lead anyone", r.team_quote),
            )
            if not have
        ]
        if gaps:
            missing.append(MissingField(key=f"role:{r.role_id}:context", question=f"About your '{label}' role: " + "; ".join(gaps) + "?", required=False))
    if projects:
        linked = {p.role_id for p in projects}
        for r in roles:
            if r.role_id not in linked:
                label = r.title or r.employer or r.role_id
                missing.append(MissingField(key=f"role:{r.role_id}:projects", question=f"What did you work on in your '{label}' role? Describe at least one project: what it was, what you did, and the result."))
    if years_experience is None:
        missing.append(MissingField(key="years_experience", question="How many years of professional experience do you have in total?"))
    if not projects:
        missing.append(MissingField(key="projects", question="Describe at least one project you worked on: what it was, what you did, and the result."))
    for p in projects:
        label = p.name or p.project_id
        key = f"project:{p.project_id}"
        if not p.role_id:
            missing.append(MissingField(key=f"{key}:role", question=f"Which role was '{label}' part of?"))
        if not p.your_role:
            missing.append(MissingField(key=f"{key}:your_role", question=f"What was your part in '{label}': did you build it alone, own the outcome, lead others on it, or contribute to a team?"))
        for fld in PROJECT_TEXT_FIELDS:
            _ask_text(missing, f"{key}:{fld}", _PROJECT_ASKS[fld].format(label=label), p.quality[fld])
        if not p.stack:
            missing.append(MissingField(key=f"{key}:stack", question=f"Which specific technologies, tools or methods did you use on '{label}'?"))
        for term in p.vague_stack:
            missing.append(MissingField(key=f"{key}:vague:{normalise_for_match(term)}", question=vague_reason(term), required=False, reason="vague"))
        if not p.processes:
            missing.append(MissingField(key=f"{key}:processes", question=f"How did you work on '{label}' — e.g. design reviews, code review, on-call, agile?", required=False))
        # Refinements (optional): substantive but not yet specific.
        if p.quality["impact"].tier == "substantive":
            missing.append(MissingField(key=f"{key}:impact:quantify", question=f"Can you put a number on the result of '{label}'?", required=False, reason="refine"))
        if p.quality["hardest_problem"].tier == "substantive":
            missing.append(MissingField(key=f"{key}:hardest_problem:decision", question=f"On '{label}', what did you decide, and what did you choose it over?", required=False, reason="refine"))
    if education_weight(years_experience) and not educations:
        missing.append(MissingField(key="education", question="What is your highest qualification, and where did you study?", required=False))
    return missing


def build_profile(
    draft: ProfileDraft,
    sources: Iterable[str],
    *,
    today: date | None = None,
    typed_sources: Iterable[str] | None = None,
) -> CandidateProfile:
    """Turn the model's draft into the app's profile.

    `sources` = everything quotes may come from (resume and/or answers). `typed_sources` = the
    subset the candidate typed as answers (None = treat everything as typed).
    """
    today = today or date.today()
    text = GroundingText(*sources)
    report = GroundingReport()

    roles = _build_roles(draft.roles, text, today, report)
    typed = None if typed_sources is None else GroundingText(*typed_sources)
    projects = _build_projects(draft.projects, roles, text, report, typed)
    skills = _build_skills(draft.skills, projects, roles, text, report)
    educations = _build_educations(draft.educations, text, report)

    stated_raw = _ground_field(draft.stated_years_raw, text, "stated_years_raw", report)
    stated = parse_stated_years(stated_raw)
    dated = dated_years(roles)
    mismatch = years_mismatch(stated, dated)
    if mismatch:
        report.notes.append(f"stated {stated} years vs {dated} dated years — ask, don't correct")
    years = stated if stated is not None else dated
    own, seniority = _signals(roles, projects)

    return CandidateProfile(
        roles=roles,
        projects=projects,
        skills=skills,
        educations=educations,
        years_experience=years,
        stated_years=stated,
        dated_years=dated,
        years_mismatch=mismatch,
        ownership=own,
        seniority=seniority,
        missing_fields=_missing_fields(roles, projects, educations, years),
        grounding=report,
    )
