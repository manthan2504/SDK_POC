"""Step 1 demo — shows what run_agent() would send, without calling any LLM.

    python step1_demo.py                 # dry run (default): no call, no tokens
    python step1_demo.py --live          # real call; also needs CALIBER_ALLOW_LLM=1

Only use --live for a run the user has approved.
"""

import argparse
import asyncio
import json
from dataclasses import asdict

from app.agents.base import AgentError, LLMCallsDisabled, build_options
from app.agents.probe import PROBE, ask_probe, build_user_prompt
from app.schemas import check_schema_rules


def dry_run(topic: str) -> None:
    options = build_options(PROBE)
    print("=== agent ===")
    print(f"name            : {PROBE.name}")
    print(f"prompt          : {PROBE.prompt.label}  sha256={PROBE.prompt.sha256[:16]}...")
    print(f"model / effort  : {options.model} / {options.effort}")
    print(f"tools           : {options.tools}   allowed_tools: {options.allowed_tools}")
    print(f"setting_sources : {options.setting_sources}")
    print(f"max_turns       : {options.max_turns}   max_budget_usd: {options.max_budget_usd}")
    print(f"cwd             : {options.cwd}")
    print(f"schema rules    : {check_schema_rules(PROBE.output_model) or 'all pass'}")
    print("\n=== output_format schema ===")
    print(json.dumps(options.output_format, indent=2))
    print("\n=== user prompt ===")
    print(build_user_prompt(topic))
    print("\n(dry run — nothing was sent)")


async def live(topic: str) -> None:
    try:
        result = await ask_probe(topic)
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
    print(result.output.model_dump_json(indent=2))
    print(json.dumps(asdict(result.meta), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("topic", nargs="?", default="retrieval-augmented generation")
    parser.add_argument("--live", action="store_true", help="make a real LLM call")
    args = parser.parse_args()
    if args.live:
        asyncio.run(live(args.topic))
    else:
        dry_run(args.topic)


if __name__ == "__main__":
    main()
