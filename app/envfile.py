"""Read `.env` without ever showing it.

Neither the Claude Agent SDK nor this POC reads `.env` on its own (RULEBOOK §3.4),
so the database URL — which carries a password — has to be loaded explicitly.
Two rules keep that safe:

  * **Only `POC_*` keys are loaded.** `CALIBER_ALLOW_LLM` is the live-call gate
    (RULEBOOK §2 rule 7). It must be set deliberately, for one approved run, in
    that process — never as a side effect of a file someone edited last week. A
    loader that copied every key would let an uncommented line open the gate.
  * **A real environment variable always wins.** The file fills gaps; it never
    overrides what the caller exported.

Nothing here prints, logs or returns the values to anything but the caller's
environment mapping.
"""

from __future__ import annotations

import os
from collections.abc import MutableMapping
from pathlib import Path

LOADED_PREFIX = "POC_"


def parse_env_file(text: str) -> dict[str, str]:
    """`KEY=value` lines. `#` starts a comment; one pair of matching quotes is dropped.

    No expansion, no `export` prefix handling beyond stripping it, no multi-line
    values: a URL and a flag are all this file holds.
    """
    pairs: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            pairs[key] = value
    return pairs


def load_poc_env(
    path: Path,
    environ: MutableMapping[str, str] | None = None,
) -> list[str]:
    """Copy `POC_*` settings from `path` into `environ`. Returns the KEY NAMES set.

    Never returns or logs a value. A missing file is not an error — the offline
    suite runs with no `.env` at all, on purpose.
    """
    target = os.environ if environ is None else environ
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return []

    loaded: list[str] = []
    for key, value in parse_env_file(text).items():
        if not key.startswith(LOADED_PREFIX) or key in target:
            continue
        target[key] = value
        loaded.append(key)
    return loaded
