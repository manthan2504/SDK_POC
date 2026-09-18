"""Test safety net: no test may ever reach a real LLM.

* the live-call gate env var is removed for every test (tests that need it set
  it themselves and always pass a fake `query_fn`);
* the SDK's real `query` inside app.agents.base is replaced by a tripwire.
"""

import pytest

from app.config import LLM_GATE_ENV


def _tripwire(*args, **kwargs):
    raise AssertionError("a test tried to call the real claude_agent_sdk.query()")


@pytest.fixture(autouse=True)
def _no_live_calls(monkeypatch):
    monkeypatch.delenv(LLM_GATE_ENV, raising=False)
    monkeypatch.setattr("app.agents.base.query", _tripwire)
