"""The shared agent runner — every Caliber agent calls `run_agent()`.

One agent step = one `query()` call (RULEBOOK §3.3, §4):
    AgentSpec  ->  build_options()  ->  query()  ->  ResultMessage  ->  validated output

What this module does NOT do (on purpose):
  * retries and saving results — the pipeline runner owns those (Step 3);
  * business checks (quotes, score sums, D8) — each agent's validators own those.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from claude_agent_sdk import (
    ClaudeAgentOptions,
    EffortLevel,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    SystemMessage,
    ToolPermissionContext,
    query,
)
from pydantic import ValidationError

from app.config import (
    AGENT_CWD,
    DEFAULT_MAX_BUDGET_USD,
    DEFAULT_MAX_TURNS,
    EFFORT_CAPABLE_MODELS,
    LLM_GATE_ENV,
    PROMPTS_DIR,
)
from app.schemas import AgentSchema

T = TypeVar("T", bound=AgentSchema)

# Claude Code delivers `output_format` results through an internal tool with this
# name (observed 2026-09-17), so the tool gate must never deny it.
STRUCTURED_OUTPUT_TOOL = "StructuredOutput"

QueryFn = Callable[..., AsyncIterator[Any]]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class LLMCallsDisabled(RuntimeError):
    """A live call was attempted without the user's permission gate being set."""


class AgentError(RuntimeError):
    """Base for failures of one agent call. Carries the audit metadata."""

    def __init__(self, message: str, meta: CallMeta | None = None) -> None:
        super().__init__(message)
        self.meta = meta


class AgentRunError(AgentError):
    """The SDK/provider reported a failure (error subtype, transport error, no result)."""

    def __init__(self, message: str, kind: str, meta: CallMeta | None = None) -> None:
        super().__init__(message, meta)
        self.kind = kind  # e.g. "transport", "no_result", "error_max_turns", ...


class AgentOutputError(AgentError):
    """The call finished but its output is missing or breaks the schema."""

    def __init__(
        self,
        message: str,
        problems: list[str],
        raw: Any = None,
        meta: CallMeta | None = None,
    ) -> None:
        super().__init__(message, meta)
        self.problems = problems  # fed back to the model on a repair retry (Step 3)
        self.raw = raw


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PromptBundle:
    """A versioned system prompt loaded from prompts/<name>.v<version>.md."""

    name: str
    version: int
    text: str
    sha256: str

    @property
    def label(self) -> str:
        return f"{self.name}.v{self.version}"


def load_prompt(name: str, version: int) -> PromptBundle:
    path = PROMPTS_DIR / f"{name}.v{version}.md"
    if not path.is_file():
        raise FileNotFoundError(f"prompt file not found: {path}")
    text = path.read_text(encoding="utf-8")
    return PromptBundle(name, version, text, hashlib.sha256(text.encode("utf-8")).hexdigest())


_TAG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def fence(tag: str, payload: str | dict[str, Any], *, source: str) -> str:
    """Wrap untrusted content as inert data (RULEBOOK §5, §12).

    The payload is JSON-encoded and angle brackets are escaped, so text such as
    "</resume>" inside a candidate's document cannot close its own fence.
    """
    if not _TAG_RE.match(tag):
        raise ValueError(f"invalid fence tag: {tag!r}")
    body = {"text": payload} if isinstance(payload, str) else payload
    encoded = json.dumps(body, ensure_ascii=False)
    encoded = encoded.replace("<", "\\u003c").replace(">", "\\u003e")
    return f'<{tag} source="{source}" trust="untrusted">{encoded}</{tag}>'


# ---------------------------------------------------------------------------
# Agent spec and result
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AgentSpec(Generic[T]):
    """Everything that makes one agent different from another."""

    name: str
    prompt: PromptBundle
    output_model: type[T]
    model: str
    effort: EffortLevel | None = None
    max_turns: int = DEFAULT_MAX_TURNS
    max_budget_usd: float | None = DEFAULT_MAX_BUDGET_USD
    # Full tool names this agent may call (e.g. "mcp__caliber__load_role_bar").
    tool_names: tuple[str, ...] = ()
    # SDK MCP servers backing those tools (created with create_sdk_mcp_server()).
    mcp_servers: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.effort is not None and self.model not in EFFORT_CAPABLE_MODELS:
            raise ValueError(f"{self.name}: model {self.model!r} does not accept `effort`")
        if self.effort == "max":
            raise ValueError(f"{self.name}: effort 'max' is not allowed (RULEBOOK §10)")
        if self.tool_names and not self.mcp_servers:
            raise ValueError(f"{self.name}: tool_names given but no mcp_servers provide them")


@dataclass
class CallMeta:
    """Audit facts about one agent call (RULEBOOK §11). No prompt text, no PII."""

    agent: str
    prompt_version: str
    prompt_sha256: str
    model_requested: str
    effort: str | None
    input_sha256: str
    started_at: str
    latency_ms: int | None = None
    session_id: str | None = None
    subtype: str | None = None
    is_error: bool | None = None
    stop_reason: str | None = None
    terminal_reason: str | None = None
    num_turns: int | None = None
    duration_api_ms: int | None = None
    total_cost_usd: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_creation_tokens: int | None = None
    models_served: list[str] = field(default_factory=list)
    permission_denials: int = 0
    errors: list[str] | None = None
    api_error_status: int | None = None

    def absorb(self, result: ResultMessage) -> None:
        usage = result.usage or {}
        self.session_id = result.session_id
        self.subtype = result.subtype
        self.is_error = result.is_error
        self.stop_reason = result.stop_reason
        self.terminal_reason = result.terminal_reason
        self.num_turns = result.num_turns
        self.duration_api_ms = result.duration_api_ms
        self.total_cost_usd = result.total_cost_usd
        self.input_tokens = usage.get("input_tokens")
        self.output_tokens = usage.get("output_tokens")
        self.cache_read_tokens = usage.get("cache_read_input_tokens")
        self.cache_creation_tokens = usage.get("cache_creation_input_tokens")
        self.models_served = sorted((result.model_usage or {}).keys())
        self.permission_denials = len(result.permission_denials or [])
        self.errors = result.errors
        self.api_error_status = result.api_error_status


@dataclass
class AgentResult(Generic[T]):
    output: T
    meta: CallMeta


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
def make_tool_gate(allowed: tuple[str, ...]) -> Callable[..., Any]:
    """`can_use_tool` callback: allow this agent's own tools, deny everything else."""
    permitted = frozenset(allowed) | {STRUCTURED_OUTPUT_TOOL}

    async def gate(
        tool_name: str, input_data: dict[str, Any], context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        if tool_name in permitted:
            return PermissionResultAllow()
        return PermissionResultDeny(message=f"Tool '{tool_name}' is not permitted for this agent.")

    return gate


def build_options(spec: AgentSpec[Any]) -> ClaudeAgentOptions:
    """Translate an AgentSpec into SDK options (lean by construction, RULEBOOK §3.5)."""
    AGENT_CWD.mkdir(parents=True, exist_ok=True)
    return ClaudeAgentOptions(
        system_prompt=spec.prompt.text,  # the exact text that was hashed
        model=spec.model,
        effort=spec.effort,
        output_format={"type": "json_schema", "schema": spec.output_model.model_json_schema()},
        tools=[],  # no built-in tools
        allowed_tools=[],  # nothing auto-approved; the gate decides
        can_use_tool=make_tool_gate(spec.tool_names),
        mcp_servers=dict(spec.mcp_servers),
        setting_sources=[],  # ignore the user's Claude Code settings
        max_turns=spec.max_turns,
        max_budget_usd=spec.max_budget_usd,
        cwd=AGENT_CWD,
    )


# ---------------------------------------------------------------------------
# The runner
# ---------------------------------------------------------------------------
async def run_agent(
    spec: AgentSpec[T],
    user_prompt: str,
    *,
    query_fn: QueryFn | None = None,
) -> AgentResult[T]:
    """Run one agent once and return its validated output.

    Raises LLMCallsDisabled, AgentRunError or AgentOutputError. The errors carry
    `meta` so the caller can still write the audit record.
    """
    if os.environ.get(LLM_GATE_ENV) != "1":
        raise LLMCallsDisabled(
            f"live LLM calls are disabled; set {LLM_GATE_ENV}=1 only for an approved run"
        )

    options = build_options(spec)
    meta = CallMeta(
        agent=spec.name,
        prompt_version=spec.prompt.label,
        prompt_sha256=spec.prompt.sha256,
        model_requested=spec.model,
        effort=spec.effort,
        input_sha256=hashlib.sha256(user_prompt.encode("utf-8")).hexdigest(),
        started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )

    result: ResultMessage | None = None
    started = time.monotonic()
    try:
        async for message in (query_fn or query)(prompt=user_prompt, options=options):
            if isinstance(message, SystemMessage) and message.subtype == "init":
                meta.session_id = message.data.get("session_id")
            elif isinstance(message, ResultMessage):
                result = message
    except Exception as exc:  # the SDK raises after yielding an error result
        meta.latency_ms = int((time.monotonic() - started) * 1000)
        if result is None:
            raise AgentRunError(f"{spec.name}: call failed: {exc}", "transport", meta) from exc
        meta.absorb(result)
        raise AgentRunError(f"{spec.name}: call ended with {result.subtype}", result.subtype, meta) from exc
    meta.latency_ms = int((time.monotonic() - started) * 1000)

    if result is None:
        raise AgentRunError(f"{spec.name}: stream ended without a result", "no_result", meta)
    meta.absorb(result)

    if result.subtype != "success" or result.is_error:
        raise AgentRunError(f"{spec.name}: call ended with {result.subtype}", result.subtype, meta)
    if result.structured_output is None:
        raise AgentOutputError(
            f"{spec.name}: no structured output returned",
            ["the reply contained no structured output"],
            raw=result.result,
            meta=meta,
        )

    try:
        output = spec.output_model.model_validate(result.structured_output)
    except ValidationError as exc:
        problems = [f"{'.'.join(map(str, e['loc'])) or '<root>'}: {e['msg']}" for e in exc.errors()]
        raise AgentOutputError(
            f"{spec.name}: output failed validation", problems, raw=result.structured_output, meta=meta
        ) from exc

    return AgentResult(output=output, meta=meta)
