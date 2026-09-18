"""Profiler arithmetic — the code half of step [1] (RULEBOOK §7 row 1, §9, §13).

The model only *reads* the resume (ProfileDraft). Everything with a computable
answer happens here:

  1. grounding   — every copied field and quote must be verbatim in the candidate's
                   text, or it is dropped (never fuzzy-accepted);
  2. dates       — raw strings like "Apr 2023" / "Present" are parsed here, never by the model;
  3. years       — dated years from the role spans; the candidate's stated years win (D6),
                   a mismatch is flagged, never silently corrected;
  4. recency     — current / recent / dated / unknown, window from data/config/scoring.yaml;
  5. evidence    — weaker-wins: final = min(agent verdict, code cap), floored at "mentioned"
                   because a skill the candidate wrote down is at least mentioned;
  6. completeness— the missing fields the app must ask the candidate about.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.config import YEARS_TOLERANCE
from app.rules import recent_window_months
from app.schemas import ProfileDraft, ProjectEntry, RoleEntry, SkillClaim, Verdict
from app.textmatch import GroundingText, mentions, normalise_for_match

Recency = Literal["current", "recent", "dated", "unknown"]

EVIDENCE_ORDER: tuple[Verdict, ...] = ("none", "mentioned", "demonstrated", "led")
_RECENCY_RANK: dict[str, int] = {"unknown": 0, "dated": 1, "recent": 2, "current": 3}


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
    start: str | None = None  # "YYYY-MM"
    end: str | None = None  # "YYYY-MM"; None when current or unknown
    months: int | None = None
    recency: Recency = "unknown"


class Project(BaseModel):
    project_id: str
    role_id: str | None
    name: str | None
    summary: str | None
    impact: str | None
    hardest_problem: str | None
    stack: list[str] = Field(default_factory=list)


class SkillEvidence(BaseModel):
    name: str
    evidence: Verdict
    quote: str | None  # the quote behind the strongest verified claim
    project_ids: list[str] = Field(default_factory=list)
    recency: Recency = "unknown"
    # The text read as stronger than the evidence could verify: assess this first.
    probe_first: bool = False


class MissingField(BaseModel):
    key: str
    question: str


class GroundingReport(BaseModel):
    dropped_fields: list[str] = Field(default_factory=list)  # copied values not in the text
    dropped_claims: list[str] = Field(default_factory=list)  # skills not in the text
    capped_claims: list[str] = Field(default_factory=list)  # verdicts lowered by the code cap
    notes: list[str] = Field(default_factory=list)  # other inconsistencies


class CandidateProfile(BaseModel):
    roles: list[Role]
    projects: list[Project]
    skills: list[SkillEvidence]
    years_experience: float | None  # stated years if given, else dated years (D6)
    stated_years: float | None
    dated_years: float | None
    years_mismatch: bool
    missing_fields: list[MissingField]
    grounding: GroundingReport

    @property
    def is_complete(self) -> bool:
        return not self.missing_fields


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}  # fmt: skip
_PRESENT = {"present", "current", "now", "today", "ongoing", "to date", "till date"}
_NAMED = re.compile(r"^(?P<m>[a-z]+)\.?\s*,?\s*(?P<y>\d{4})$")
_NUM_MY = re.compile(r"^(?P<m>\d{1,2})\s*[/.-]\s*(?P<y>\d{4})$")
_NUM_YM = re.compile(r"^(?P<y>\d{4})\s*[/.-]\s*(?P<m>\d{1,2})$")
_YEAR = re.compile(r"^(?P<y>\d{4})$")


def is_present(raw: str | None) -> bool:
    return bool(raw) and normalise_for_match(raw) in _PRESENT


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
    if month is None or year is None or not 1 <= month <= 12 or not 1950 <= year <= 2100:
        return None
    return year, month


def _idx(ym: tuple[int, int]) -> int:
    return ym[0] * 12 + (ym[1] - 1)


def _fmt(ym: tuple[int, int] | None) -> str | None:
    return f"{ym[0]:04d}-{ym[1]:02d}" if ym else None


# ---------------------------------------------------------------------------
# Evidence cap (code side of weaker-wins)
# ---------------------------------------------------------------------------
# Language markers, not role content (FR-I5 safe). POC heuristic, see RULEBOOK §13.
_TEAM = re.compile(r"\b(we|we've|we'd|our team|the team)\b")
_LEAD = re.compile(
    r"\b(led|owned|chose|decided|designed|architected|drove|headed|spearheaded|responsible for)\b"
)


def evidence_cap(skill: str, quote: str | None, quote_verified: bool) -> Verdict:
    """The strongest verdict this quote can support, whatever the model said.

    * no verified quote, or the quote is about something else  -> mentioned
    * team language ("we", "the team") is not personal evidence -> mentioned
    * an ownership/decision verb                                -> led
    * otherwise the candidate did something with it             -> demonstrated
    """
    if not quote_verified or not mentions(quote, skill):
        return "mentioned"
    q = normalise_for_match(quote or "")
    if _TEAM.search(q):
        return "mentioned"
    if _LEAD.search(q):
        return "led"
    return "demonstrated"


def final_evidence(agent: Verdict | None, cap: Verdict) -> Verdict:
    """Weaker of agent and cap, never below 'mentioned' (the skill is in the text)."""
    agent_rank = evidence_rank(agent) if agent else evidence_rank("mentioned")
    chosen = min(agent_rank, evidence_rank(cap))
    return EVIDENCE_ORDER[max(chosen, evidence_rank("mentioned"))]


# ---------------------------------------------------------------------------
# Building the profile
# ---------------------------------------------------------------------------
def _ground_field(value: str | None, text: GroundingText, where: str, report: GroundingReport) -> str | None:
    if value is None or value.strip() == "":
        return None
    if text.contains(value):
        return value
    report.dropped_fields.append(f"{where}: {value!r} is not in the candidate's text")
    return None


def _build_roles(entries: Iterable[RoleEntry], text: GroundingText, today: date, report: GroundingReport) -> list[Role]:
    roles: list[Role] = []
    seen: set[str] = set()
    window = recent_window_months()
    today_ym = (today.year, today.month)
    for n, e in enumerate(entries, start=1):
        rid = e.role_id if e.role_id and e.role_id not in seen else f"r{n}"
        seen.add(rid)
        where = f"role {rid}"
        start_raw = _ground_field(e.start_raw, text, f"{where} start_raw", report)
        end_raw = _ground_field(e.end_raw, text, f"{where} end_raw", report)
        is_current = bool(e.is_current) or is_present(end_raw)
        if is_present(end_raw):
            end_raw_for_parse = None
        else:
            end_raw_for_parse = end_raw
        if end_raw_for_parse and e.is_current:
            # a dated end beats a stray is_current flag
            report.notes.append(f"{where}: has an end date and is_current; treated as ended")
            is_current = False
        role = Role(
            role_id=rid,
            employer=_ground_field(e.employer_raw, text, f"{where} employer_raw", report),
            title=_ground_field(e.title_raw, text, f"{where} title_raw", report),
            start_raw=start_raw,
            end_raw=end_raw,
            is_current=is_current,
        )
        start = parse_raw_date(start_raw)
        end = today_ym if is_current else parse_raw_date(end_raw_for_parse, is_end=True)
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


def _build_projects(
    entries: Iterable[ProjectEntry], roles: list[Role], text: GroundingText, report: GroundingReport
) -> list[Project]:
    role_ids = {r.role_id for r in roles}
    projects: list[Project] = []
    seen: set[str] = set()
    for n, e in enumerate(entries, start=1):
        pid = e.project_id if e.project_id and e.project_id not in seen else f"p{n}"
        seen.add(pid)
        where = f"project {pid}"
        role_id = e.role_id if e.role_id in role_ids else None
        if e.role_id and role_id is None:
            report.notes.append(f"{where}: role_id {e.role_id!r} does not exist")
        stack: list[str] = []
        stack_keys: set[str] = set()
        for item in e.stack or []:
            grounded = _ground_field(item, text, f"{where} stack", report)
            if grounded and normalise_for_match(grounded) not in stack_keys:
                stack_keys.add(normalise_for_match(grounded))
                stack.append(grounded)
        projects.append(
            Project(
                project_id=pid,
                role_id=role_id,
                name=e.name,  # a label, not a quote: not grounded
                summary=_ground_field(e.summary_quote, text, f"{where} summary_quote", report),
                impact=_ground_field(e.impact_quote, text, f"{where} impact_quote", report),
                hardest_problem=_ground_field(
                    e.hardest_problem_quote, text, f"{where} hardest_problem_quote", report
                ),
                stack=stack,
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

    merged: dict[str, SkillEvidence] = {}
    claimed: set[tuple[str, str]] = set()

    def add(name: str, level: Verdict, quote: str | None, pid: str | None, probe: bool) -> None:
        key = normalise_for_match(name)
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
        if not c.skill or not text.contains(c.skill):
            report.dropped_claims.append(f"skill {c.skill!r}: not in the candidate's text")
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
        add(c.skill, level, c.quote if quote_ok else None, pid, probe)
        if pid:
            claimed.add((pid, normalise_for_match(c.skill)))

    # A technology listed in a project's stack is at least "mentioned" (a dated fact).
    for p in projects:
        for item in p.stack:
            if (p.project_id, normalise_for_match(item)) not in claimed:
                add(item, "mentioned", None, p.project_id, False)

    return sorted(merged.values(), key=lambda s: (-evidence_rank(s.evidence), s.name.casefold()))


_YEARS_NUM = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b")


def parse_stated_years(raw: str | None) -> float | None:
    if not raw:
        return None
    m = _YEARS_NUM.search(normalise_for_match(raw))
    return float(m.group(1)) if m else None


def dated_years(roles: list[Role]) -> float | None:
    """Union of dated role spans (overlaps counted once), in years to 1 dp."""
    months: set[int] = set()
    for r in roles:
        if r.start and r.months:
            y, m = map(int, r.start.split("-"))
            start = _idx((y, m))
            months.update(range(start, start + r.months))
    return round(len(months) / 12, 1) if months else None


def _missing_fields(
    roles: list[Role], projects: list[Project], years_experience: float | None
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
    if years_experience is None:
        missing.append(MissingField(key="years_experience", question="How many years of professional experience do you have in total?"))
    if not projects:
        missing.append(MissingField(key="projects", question="Describe at least one project you worked on: what it was, what you did, and the result."))
    for p in projects:
        label = p.name or p.project_id
        if not p.role_id:
            missing.append(MissingField(key=f"project:{p.project_id}:role", question=f"Which role was '{label}' part of?"))
        if not p.summary:
            missing.append(MissingField(key=f"project:{p.project_id}:summary", question=f"In a sentence or two, what was '{label}'?"))
        # PRD §7.1: impact and hardest problem are the highest-value prompts, always asked.
        if not p.impact:
            missing.append(MissingField(key=f"project:{p.project_id}:impact", question=f"What was the measurable result of '{label}'?"))
        if not p.hardest_problem:
            missing.append(MissingField(key=f"project:{p.project_id}:hardest_problem", question=f"What was the hardest problem you solved on '{label}', and what did you decide?"))
    return missing


def build_profile(draft: ProfileDraft, sources: Iterable[str], *, today: date | None = None) -> CandidateProfile:
    """Turn the model's draft into the app's profile. `sources` = resume text + candidate answers."""
    today = today or date.today()
    text = GroundingText(*sources)
    report = GroundingReport()

    roles = _build_roles(draft.roles, text, today, report)
    projects = _build_projects(draft.projects, roles, text, report)
    skills = _build_skills(draft.skills, projects, roles, text, report)

    stated_raw = _ground_field(draft.stated_years_raw, text, "stated_years_raw", report)
    stated = parse_stated_years(stated_raw)
    dated = dated_years(roles)
    mismatch = stated is not None and dated is not None and abs(stated - dated) > YEARS_TOLERANCE
    if mismatch:
        report.notes.append(f"stated {stated} years vs {dated} dated years — ask, don't correct")
    years = stated if stated is not None else dated

    return CandidateProfile(
        roles=roles,
        projects=projects,
        skills=skills,
        years_experience=years,
        stated_years=stated,
        dated_years=dated,
        years_mismatch=mismatch,
        missing_fields=_missing_fields(roles, projects, years),
        grounding=report,
    )
