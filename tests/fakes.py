"""Shared offline stand-ins for claude_agent_sdk.query (no network, no tokens)."""

from typing import Any

from claude_agent_sdk import ResultMessage


def make_result(structured_output: Any = None, **overrides: Any) -> ResultMessage:
    fields: dict[str, Any] = dict(
        subtype="success",
        duration_ms=10,
        duration_api_ms=8,
        is_error=False,
        num_turns=2,
        session_id="sess-1",
        stop_reason="end_turn",
        total_cost_usd=0.001,
        usage={"input_tokens": 400, "output_tokens": 60, "cache_read_input_tokens": 0},
        result=None,
        structured_output=structured_output,
        model_usage={"claude-haiku-4-5": {}},
        terminal_reason="completed",
    )
    fields.update(overrides)
    return ResultMessage(**fields)


class FakeQuery:
    """Records each call and yields scripted messages, optionally raising at the end."""

    def __init__(self, messages: list[Any], raise_after: Exception | None = None) -> None:
        self.messages = messages
        self.raise_after = raise_after
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *, prompt: str, options: Any):
        self.calls.append({"prompt": prompt, "options": options})
        return self._stream()

    async def _stream(self):
        for m in self.messages:
            yield m
        if self.raise_after is not None:
            raise self.raise_after
