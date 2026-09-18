"""Step 1 example agent — not part of Caliber's pipeline.

It exists only to show the pattern every real agent will follow:
a spec (prompt + schema + model) and a small function that calls run_agent().
"""

from app.agents.base import AgentResult, AgentSpec, fence, load_prompt, run_agent
from app.config import HAIKU
from app.schemas import ProbeQuestion

PROBE = AgentSpec(
    name="probe",
    prompt=load_prompt("probe", 1),
    output_model=ProbeQuestion,
    model=HAIKU,  # Haiku: no `effort`
    max_budget_usd=0.05,
)


def build_user_prompt(topic: str) -> str:
    return f"{fence('topic', topic, source='app')}\n\nWrite one interview question about this topic."


async def ask_probe(topic: str) -> AgentResult[ProbeQuestion]:
    return await run_agent(PROBE, build_user_prompt(topic))
