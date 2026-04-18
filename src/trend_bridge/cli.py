"""Arg-driven CLI — ``score`` and ``build-insight`` subcommands.

``demo.py`` calls ``run_score`` directly for each bundled sample so the zero-arg
demo reads as real arg-passing rather than hardcoded inline logic.
See DESIGN.md §5 and §9.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def run_score(
    *,
    source: Path,
    metadata_path: Path,
    target: str,
) -> None:
    """Execute A + L for one source video and render the result."""
    raise NotImplementedError


def run_build_insight(
    *,
    region: str,
    platform: str,
    n: int,
    out_path: Path,
) -> None:
    """Execute the offline regional-insight builder and write the JSON fixture."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """Entry point dispatched by ``python -m trend_bridge``."""
    parser = argparse.ArgumentParser(prog="trend_bridge")
    sub = parser.add_subparsers(dest="command", required=True)

    p_score = sub.add_parser("score", help="Score one source video against a target corpus")
    p_score.add_argument("--source", type=Path, required=True)
    p_score.add_argument("--metadata", type=Path, required=True)
    p_score.add_argument("--target", required=True, help="e.g., us-tiktok")

    p_build = sub.add_parser("build-insight", help="Build a regional-insight corpus")
    p_build.add_argument("--region", required=True)
    p_build.add_argument("--platform", required=True)
    p_build.add_argument("--n", type=int, default=12)
    p_build.add_argument("--out", type=Path, required=True)

    sub.add_parser("demo", help="Run the zero-arg demo over bundled samples")

    args = parser.parse_args(argv)
    raise NotImplementedError
