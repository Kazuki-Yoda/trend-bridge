"""Zero-arg demo: run A + L on every bundled sample, sort, and render.

Internally dispatches ``cli.run_score`` for each sample so the demo reads as
real arg-passing rather than hardcoded inline logic. See DESIGN.md §5 and §9.
"""

from __future__ import annotations

from trend_bridge.schemas import ScoreOutcome


def run_demo() -> list[ScoreOutcome]:
    """Run ``run_score`` over every bundled sample and return sorted outcomes.

    Sort order is ``report.fit_score`` desc. Stdout rendering is the caller's
    responsibility (see ``renderer.render_demo``).
    """
    raise NotImplementedError
