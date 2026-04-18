"""L: produce a localization plan for a source video.

Consumes A's ``ScoringReport`` as prompt context so L can focus on remix
actions without re-deriving fit reasoning. One Gemini call per invocation.
See DESIGN.md §5.
"""

from __future__ import annotations

from trend_bridge.api_clients.gemini import (
    GeminiStructuredOutputService,
    MediaPart,
)
from trend_bridge.schemas import LocalizationPlan, ScoringReport, VideoMetadata


def plan_localization(
    *,
    media: MediaPart,
    metadata: VideoMetadata,
    report: ScoringReport,
    service: GeminiStructuredOutputService,
) -> LocalizationPlan:
    """Produce a prioritized localization plan for ``media``."""
    raise NotImplementedError
