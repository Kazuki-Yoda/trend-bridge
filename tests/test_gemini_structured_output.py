"""Minimal smoke test for GeminiStructuredOutputService.

Requires GOOGLE_API_KEY in .env or environment.
Run: pytest tests/test_gemini_structured_output.py -m api -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

pytestmark = [
    pytest.mark.api,
    pytest.mark.skipif(
        not os.environ.get("GOOGLE_API_KEY"),
        reason="GOOGLE_API_KEY not set",
    ),
]


class Country(BaseModel):
    name: str
    capital: str
    population: int


def test_generate_text_only():
    from trend_bridge.api_clients.gemini.structured_output import (
        GeminiStructuredOutputService,
    )

    service = GeminiStructuredOutputService()
    result = service.generate(
        schema=Country,
        prompt="Give me info about Japan.",
    )

    assert isinstance(result, Country)
    assert result.name == "Japan"
    assert isinstance(result.capital, str)
    assert result.population > 0


SAMPLE_VIDEO = Path(__file__).resolve().parent.parent / ".inputs" / "videos" / "test_oreo_children.mp4"


class VideoSummary(BaseModel):
    description: str
    duration_estimate: str
    key_objects: list[str]


def test_generate_with_video():
    from trend_bridge.api_clients.gemini.media import MediaPart
    from trend_bridge.api_clients.gemini.structured_output import (
        GeminiStructuredOutputService,
    )

    service = GeminiStructuredOutputService()
    result = service.generate(
        schema=VideoSummary,
        prompt="Describe what happens in this video.",
        media=[MediaPart(file_path=str(SAMPLE_VIDEO), mime_type="video/mp4")],
    )

    assert isinstance(result, VideoSummary)
    assert len(result.description) > 0
    assert len(result.key_objects) > 0
