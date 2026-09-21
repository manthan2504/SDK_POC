"""Step 0 demo — document text extraction, the deterministic half of ingestion.

    python step0_demo.py                    # run over every fixture in data/fixtures/extraction
    python step0_demo.py path/to/resume.pdf # run over one real file
    python step0_demo.py --text FILE        # also print the extracted text

There is no --live flag: this step never calls a model. That is the point — every
rejection below happens before a single token is spent.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from app.config import DATA_DIR
from app.extraction import ExtractionError, MIN_USEFUL_CHARS, extract, load_resume_text
from app.policy import MAX_RESUME_CHARS

FIXTURES = DATA_DIR / "fixtures" / "extraction"

# Each failure carries one HTTP status. The FastAPI layer (step 12) will map them.
STATUS = {
    "UnsupportedFileType": 415,
    "FileTooLarge": 413,
    "UnreadableDocument": 400,
    "NoTextLayer": 422,
}


def run_one(path: Path, show_text: bool) -> None:
    raw = path.read_bytes()
    started = time.perf_counter()
    try:
        result = extract(path.name, raw)
    except ExtractionError as exc:
        elapsed = (time.perf_counter() - started) * 1000
        status = STATUS.get(type(exc).__name__, 400)
        print(f"{path.name:28} {elapsed:7.1f} ms  REJECTED {status} {type(exc).__name__}")
        print(f"{'':28}          {exc}")
        return

    elapsed = (time.perf_counter() - started) * 1000
    print(
        f"{path.name:28} {elapsed:7.1f} ms  chars={len(result.text):6}  pages={result.pages}  "
        f"layout={result.layout:13} usable={result.is_usable}"
    )

    if not result.is_usable:
        # Parsed fine, but there is nothing for the model to read.
        try:
            load_resume_text(path.name, raw)
        except ExtractionError as exc:
            print(f"{'':28}          REJECTED {STATUS['NoTextLayer']} NoTextLayer: {exc}")
        return

    source = load_resume_text(path.name, raw)
    handoff = f"{'':28}          -> Profiler gets {len(source.text):,} chars"
    if source.was_clipped:
        handoff += f" (clipped {source.clipped_chars:,}; cap is {MAX_RESUME_CHARS:,})"
    print(handoff)

    if show_text:
        print("-" * 72)
        print(source.text)
        print("-" * 72)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="files to extract (default: fixtures)")
    parser.add_argument("--text", action="store_true", help="print the extracted text too")
    args = parser.parse_args()

    paths = args.paths or sorted(p for p in FIXTURES.iterdir() if p.is_file())

    print(f"Step [0] extraction — no model is called. Usable means >= {MIN_USEFUL_CHARS} chars.\n")
    for path in paths:
        run_one(path, args.text)

    print(
        "\nEvery line above was decided by plain Python. Step [1] (the Profiler, Haiku) only ever\n"
        "sees the text of the rows that reached a Profiler hand-off."
    )


if __name__ == "__main__":
    main()
