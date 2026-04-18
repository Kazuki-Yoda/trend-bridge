"""Zero-arg demo: run A + L on every bundled sample, sort, and render.

Internally dispatches ``cli.run_score`` for each sample so the demo reads as
real arg-passing rather than hardcoded inline logic. See DESIGN.md §5 and §9.
"""

from __future__ import annotations


def run_demo() -> None:
    """Run the full demo pipeline end-to-end on bundled samples."""
    raise NotImplementedError
