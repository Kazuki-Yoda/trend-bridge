"""Minimal smoke test for GeminiStructuredOutputService.

Requires GOOGLE_API_KEY in .env or environment.
Run: pytest tests/test_gemini_structured_output.py -v
"""

from __future__ import annotations

import os

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
    from trend_bridge.api_clients.vertexai.structured_output import (
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
