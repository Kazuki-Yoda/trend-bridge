"""A: score a single source video against a regional-insight corpus.

One Gemini call per invocation. See DESIGN.md §5 (data flow) and §4 (schema).
"""

from __future__ import annotations

from trend_bridge.api_clients.gemini import (
    GeminiStructuredOutputService,
    MediaPart,
)
from trend_bridge.schemas import RegionalInsight, ScoringReport, VideoMetadata


def score_video(
    *,
    media: MediaPart,
    metadata: VideoMetadata,
    insight: RegionalInsight,
    service: GeminiStructuredOutputService,
) -> ScoringReport:
    """Score ``media`` against ``insight`` and return a structured report."""
    raise NotImplementedError
