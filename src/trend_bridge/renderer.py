"""Rich-based terminal renderer for scoring + localization output.

Used by both the arg-driven ``score`` command and the zero-arg ``demo``.
See DESIGN.md §5 (data flow) and §9 (demo script).
"""

from __future__ import annotations

from trend_bridge.schemas import LocalizationPlan, ScoringReport, VideoMetadata


def render_pair(
    metadata: VideoMetadata,
    report: ScoringReport,
    plan: LocalizationPlan,
) -> None:
    """Print a full scoring + localization panel set for one source video."""
    raise NotImplementedError


def render_demo(
    triples: list[tuple[VideoMetadata, ScoringReport, LocalizationPlan]],
) -> None:
    """Print the full demo output: header + one panel set per source, sorted."""
    raise NotImplementedError
