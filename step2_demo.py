"""Step 2 demo — the Profiler.

    python step2_demo.py            # offline (default): show the request, run the CODE half
                                    # on a hand-written example draft. No LLM call.
    python step2_demo.py --live     # real Profiler call; also needs CALIBER_ALLOW_LLM=1

Only use --live for a run the user has approved.
"""

import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import date

from app.agents.base import AgentError, LLMCallsDisabled, build_options
from app.agents.profiler import PROFILER, build_user_prompt, run_profiler
from app.candidate_profile import CandidateProfile, build_profile
from app.config import DATA_DIR
from app.schemas import ProfileDraft, check_schema_rules

FIXTURES = DATA_DIR / "fixtures"
TODAY = date(2026, 9, 18)  # fixed so the demo output is reproducible


def show_profile(profile: CandidateProfile) -> None:
    print("\n--- roles ---")
    for r in profile.roles:
        print(f"{r.role_id}: {r.title!s:28} @ {r.employer!s:18} {r.start} -> {r.end or ('now' if r.is_current else '?')}"
              f"  months={r.months}  recency={r.recency}  team={r.team_size} led_team={r.led_team}")
    print("\n--- projects (your_role, stack, answer quality) ---")
    for p in profile.projects:
        tiers = " ".join(f"{f}={q.tier}" for f, q in p.quality.items())
        print(f"{p.project_id} ({p.role_id}) {p.name}: your_role={p.your_role} stack={p.stack}"
              + (f" vague={p.vague_stack}" if p.vague_stack else ""))
        print(f"     {tiers}")
    print("\n--- skills (final evidence after weaker-wins, depth score) ---")
    for s in profile.skills:
        flag = "  <- probe first" if s.probe_first else ""
        print(f"{s.evidence:13} {s.name:14} depth={s.depth_score:3} {s.recency:8} projects={s.project_ids}{flag}")
    print("\n--- signals ---")
    print(f"ownership: {profile.ownership.level} — {profile.ownership.basis}")
    for k, v in profile.seniority.items():
        print(f"{k:11} {v.tier:6} {v.basis}")
    print("\n--- years / education ---")
    print(f"stated={profile.stated_years}  dated={profile.dated_years}  used={profile.years_experience}"
          f"  mismatch={profile.years_mismatch}")
    for e in profile.educations:
        print(f"education: {e.qualification} — {e.institution}, {e.end_year}")
    print("\n--- grounding report (what the code caught) ---")
    for label, items in profile.grounding.model_dump().items():
        for item in items:
            print(f"[{label}] {item}")
    req = profile.required_missing
    opt = [m for m in profile.missing_fields if not m.required]
    state = "COMPLETE" if profile.is_complete else f"{len(req)} required questions"
    print(f"\n--- completeness: {state}, {len(opt)} optional nudges ---")
    for m in req:
        print(f"REQUIRED {m.key:32} {m.question}")
    for m in opt:
        print(f"optional {m.key:32} {m.question}")


def offline() -> None:
    resume = (FIXTURES / "ravi_resume.txt").read_text(encoding="utf-8")
    options = build_options(PROFILER)
    print("=== Profiler agent ===")
    print(f"prompt          : {PROFILER.prompt.label}  sha256={PROFILER.prompt.sha256[:16]}...")
    print(f"model / effort  : {options.model} / {options.effort}")
    print(f"tools           : {options.tools}   setting_sources: {options.setting_sources}")
    print(f"max_turns       : {options.max_turns}   max_budget_usd: {options.max_budget_usd}")
    print(f"schema rules    : {check_schema_rules(PROFILER.output_model) or 'all pass'}")
    prompt = build_user_prompt(resume)
    print(f"\n=== user prompt ({len(prompt):,} chars) ===")
    print(prompt[:400] + " ...")

    draft = ProfileDraft.model_validate_json((FIXTURES / "ravi_draft_example.json").read_text(encoding="utf-8"))
    print("\n=== CODE half on the hand-written example draft (no model involved) ===")
    show_profile(build_profile(draft, [resume], today=TODAY))
    print("\n(offline — nothing was sent)")


async def live() -> None:
    resume = (FIXTURES / "ravi_resume.txt").read_text(encoding="utf-8")
    try:
        run = await run_profiler(resume, today=TODAY)
    except LLMCallsDisabled as exc:
        print(f"refused: {exc}")
        return
    except AgentError as exc:
        print(f"failed: {exc}")
        if getattr(exc, "problems", None):
            print("problems:", exc.problems)
        if exc.meta:
            print(json.dumps(asdict(exc.meta), indent=2))
        return
    show_profile(run.profile)
    print("\n--- call ---")
    print(json.dumps(asdict(run.meta), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="make a real LLM call")
    args = parser.parse_args()
    asyncio.run(live()) if args.live else offline()


if __name__ == "__main__":
    main()
