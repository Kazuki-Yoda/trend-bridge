"""Minimal output renderer — plain-text header + indented JSON dumps.

P0 implementation intentionally does no fancy formatting. P1 swaps the body
for Rich panels while keeping the same two public functions, so callers
(``cli.py`` and ``demo.py``) don't change. See DESIGN.md §5 and §10.
"""

from __future__ import annotations

import json
import sys
from typing import TextIO

from trend_bridge.schemas import ScoreOutcome


def render_pair(outcome: ScoreOutcome, *, out: TextIO | None = None) -> None:
    """Print one source's header + ScoringReport + LocalizationPlan to ``out``."""
    stream = out if out is not None else sys.stdout
    m = outcome.metadata
    fit = outcome.report.fit_score
    print(f'=== fit_score={fit} — "{m.title}" [{m.source_platform}] ===', file=stream)
    print("--- ScoringReport ---", file=stream)
    print(_dump(outcome.report.model_dump()), file=stream)
    print("--- LocalizationPlan ---", file=stream)
    print(_dump(outcome.plan.model_dump()), file=stream)


def render_demo(outcomes: list[ScoreOutcome], *, out: TextIO | None = None) -> None:
    """Print each outcome prefixed with a rank header."""
    stream = out if out is not None else sys.stdout
    total = len(outcomes)
    for rank, outcome in enumerate(outcomes, start=1):
        print(f"=== rank {rank} of {total} ===", file=stream)
        render_pair(outcome, out=stream)
        print("", file=stream)


def _dump(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)
