from __future__ import annotations

import os

from google import genai

_client: genai.Client | None = None


def get_client() -> genai.Client:
    """Return a module-level singleton Gemini API client."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return _client
