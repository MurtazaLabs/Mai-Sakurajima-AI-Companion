"""Emit a GitHub Actions error annotation from a captured command log.

Job logs need repository admin rights, so the steps that must fail loudly (test
run, Docker build, image signing) pipe their output to a file and call this
script. The annotation is visible on the run page and through the check-runs
API, which is enough to debug a failure without log access.

Usage:
    python scripts/ci_annotate_failure.py --title pytest-failed \\
        --from-marker "short test summary info" pytest-output.log
    python scripts/ci_annotate_failure.py --title docker-build-failed \\
        --tail 2500 docker-build.log
    python scripts/ci_annotate_failure.py --title cosign-sign-failed \\
        --prefix "digest=sha256:... " --tail 1800 cosign.log
"""
from __future__ import annotations

import argparse
import urllib.parse
from pathlib import Path

DEFAULT_TAIL = 2500


def tail_of_log(path: Path, from_marker: str | None, limit: int) -> str:
    """Return the last ``limit`` characters of ``path``, optionally after a marker."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"log unavailable: {exc}"
    if from_marker:
        index = text.find(from_marker)
        if index != -1:
            text = text[index:]
    return text[-limit:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Annotate a captured CI log on the run page.")
    parser.add_argument("log", type=Path, help="file the step's output was piped to")
    parser.add_argument("--title", default="ci-failure", help="annotation title")
    parser.add_argument(
        "--tail", type=int, default=DEFAULT_TAIL, help="characters quoted from the end of the log"
    )
    parser.add_argument(
        "--from-marker", default=None, help="start the quoted snippet at this marker when present"
    )
    parser.add_argument("--prefix", default="", help="text prepended to the quoted snippet")
    args = parser.parse_args(argv)

    snippet = f"{args.prefix}{tail_of_log(args.log, args.from_marker, max(args.tail, 200))}"
    # Annotations must be single-line; percent-encoding keeps newlines intact.
    print(snippet)
    print(f"::error title={args.title}::{urllib.parse.quote(snippet, safe='')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
