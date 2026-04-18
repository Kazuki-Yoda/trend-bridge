"""Gemini API client surface + mock factory.

``make_gemini_service()`` is the single construction seam — business logic
never reads ``TB_MOCK`` directly. See DESIGN.md §6.
"""

from __future__ import annotations

import os

from trend_bridge.api_clients.gemini.media import MediaPart
from trend_bridge.api_clients.gemini.structured_output import (
    GeminiConfig,
    GeminiStructuredOutputService,
)

__all__ = [
    "GeminiConfig",
    "GeminiStructuredOutputService",
    "MediaPart",
    "make_gemini_service",
]


def make_gemini_service() -> GeminiStructuredOutputService:
    """Return a real service, or a caching one when ``TB_MOCK`` is set."""
    mode = os.getenv("TB_MOCK", "off")
    if mode == "off":
        return GeminiStructuredOutputService()
    if mode not in ("record", "replay"):
        raise ValueError(
            f"TB_MOCK must be 'off', 'record', or 'replay' (got {mode!r})"
        )
    from trend_bridge.api_clients.gemini.mock import (
        CachingGeminiStructuredOutputService,
    )
    return CachingGeminiStructuredOutputService(mode=mode)
