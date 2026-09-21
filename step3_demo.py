"""Step 3 demo — the pipeline runner. Offline: no model is called.

    python step3_demo.py            # a full run: extract -> [1] Profiler -> pauses -> resumes
    python step3_demo.py --runs      # list what is in runs/caliber.db

The agent half is replaced by a fake that returns the hand-written example draft,
so what you are watching is the *sequence*: save before next, retry, pause,
resume, audit. That is the part D11 says belongs to plain Python.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

from app.agents.base import AgentOutputError
from app.config import DATA_DIR, RUNS_DIR
from app.pipeline.runner import StepResult, run_pipeline
from app.pipeline.steps import ANSWERS_NEEDED, CONFIRM_PROFILE, PROFILER_STEP, questions_for
from app.pipeline.store import Store, open_store
from app.candidate_profile import build_profile
from app.schemas import ProfileDraft

FIXTURES = DATA_DIR / "fixtures"
TODAY = date(2026, 9, 21)
DB = RUNS_DIR / "demo.db"


def banner(text: str) -> None:
    print(f"\n{'=' * 70}\n{text}\n{'=' * 70}")


def fake_profiler(fail_first: bool = False):
    """Stands in for the Haiku call. First call may fail, to show the retry."""
    state = {"calls": 0}
    resume = (FIXTURES / "ravi_resume.txt").read_text(encoding="utf-8")
    draft = ProfileDraft.model_validate_json(
        (FIXTURES / "ravi_draft_example.json").read_text(encoding="utf-8")
    )

    async def execute(pipeline_state, feedback):
        state["calls"] += 1
        print(f"    [1] Profiler call #{state['calls']}"
              + (f"  (repairing: {feedback})" if feedback else ""))
        if fail_first and state["calls"] == 1:
            raise AgentOutputError("profiler: output failed validation", ["roles.0.title: required"])
        answers = pipeline_state.get("answers", [])
        sources = [resume, *(a["answer"] for a in answers)]
        profile = build_profile(draft, sources, today=TODAY)
        if answers:
            # The demo's stand-in cannot really re-read; pretend the gaps closed.
            profile = profile.model_copy(update={"missing_fields": []})
        return StepResult(output=profile)

    return execute


async def demo() -> None:
    if DB.exists():
        DB.unlink()  # a fresh demo every time

    # The real step, with only its agent call swapped for the fake.
    steps = [replace(PROFILER_STEP, execute=fake_profiler(fail_first=True))]

    with open_store(DB) as store:
        banner("RUN 1 — first attempt fails validation, the runner repairs it")
        outcome = await run_pipeline(steps, {"resume_text": "…", "today": TODAY}, store)
        print(f"  status      : {outcome.status}")
        print(f"  waiting for : {outcome.waiting_for}")
        print(f"  attempts    : {outcome.attempts}")
        show_attempts(store, outcome.run_id)

        if outcome.waiting_for == ANSWERS_NEEDED:
            profile = outcome.outputs["profile"]
            asked = questions_for(profile)[:3]
            banner(f"CHECKPOINT — {len(questions_for(profile))} questions; the app pauses (FR-I11)")
            for q in asked:
                print(f"  {'REQUIRED' if q['required'] == 'True' else 'optional'}  {q['question']}")
            print("\n  ...candidate answers, the app records the decision and calls again.")
            store.decide(outcome.run_id, ANSWERS_NEEDED,
                         [{"key": q["key"], "question": q["question"], "answer": "…"} for q in asked])

            banner("RUN 2 — same run_id: step [1] repeats with the answers")
            outcome = await run_pipeline(steps, {"resume_text": "…", "today": TODAY},
                                         store, run_id=outcome.run_id)
            print(f"  status      : {outcome.status}   waiting for: {outcome.waiting_for}")
            show_attempts(store, outcome.run_id)

        if outcome.waiting_for == CONFIRM_PROFILE:
            banner("CHECKPOINT — the candidate confirms the profile (PRD §7.1)")
            store.decide(outcome.run_id, CONFIRM_PROFILE, {"confirmed": True})
            outcome = await run_pipeline(steps, {"resume_text": "…", "today": TODAY},
                                         store, run_id=outcome.run_id)
            print(f"  status      : {outcome.status}")

        banner("WHAT THE STORE KEPT")
        show_attempts(store, outcome.run_id)
        print(f"\n  run status : {store.get_run(outcome.run_id).status}")
        print(f"  total cost : ${store.cost(outcome.run_id):.4f}  (fake calls, so $0)")
        print(f"  database   : {DB}")
        print("\n  Nothing above asked a model for permission to continue. The order,")
        print("  the retry, the pauses and the saving are all in app/pipeline/.")


def show_attempts(store: Store, run_id: str) -> None:
    print(f"  {'step':<5}{'attempt':<9}{'status':<10}{'error':<28}output")
    for a in store.attempts(run_id):
        output = "—" if a.output is None else f"{len(json.dumps(a.output)):,} bytes of JSON"
        print(f"  {a.step:<5}{a.attempt:<9}{a.status:<10}{(a.error_kind or '—'):<28}{output}")


def list_runs() -> None:
    for path in (DB, RUNS_DIR / "caliber.db"):
        if not Path(path).exists():
            continue
        print(f"\n{path}")
        with open_store(path) as store:
            for run in store.list_runs():
                print(f"  {run.run_id[:12]}  {run.status:<8} step={run.current_step} "
                      f"waiting={run.waiting_for or '—'}  ${store.cost(run.run_id):.4f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", action="store_true", help="list stored runs and stop")
    args = parser.parse_args()
    list_runs() if args.runs else asyncio.run(demo())


if __name__ == "__main__":
    main()
