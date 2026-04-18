"""Prompt-hash replay cache for ``GeminiStructuredOutputService`` (``TB_MOCK``).

Drop-in subclass with the same ``generate`` / ``agenerate`` surface. Modes:

* ``record``  — real call on miss, write response to ``samples/gemini_cache/``.
* ``replay``  — hit → return cached; miss → raise (no accidental billing).

Cache key is a hash of ``(model, system_prompt, user_prompt, schema_name,
media_sha256_list)``. See DESIGN.md §6.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeVar

from pydantic import BaseModel

from trend_bridge.api_clients.gemini.media import MediaPart
from trend_bridge.api_clients.gemini.structured_output import (
    GeminiConfig,
    GeminiStructuredOutputService,
)

T = TypeVar("T", bound=BaseModel)

MockMode = Literal["record", "replay"]


@dataclass
class CachingGeminiStructuredOutputService(GeminiStructuredOutputService):
    """Caching wrapper. Set ``mode`` to ``record`` or ``replay``."""

    mode: MockMode = "replay"
    config: GeminiConfig = None  # type: ignore[assignment]

    def generate(
        self,
        *,
        schema: type[T],
        prompt: str,
        system_prompt: str | None = None,
        media: list[MediaPart] | None = None,
    ) -> T:
        raise NotImplementedError

    async def agenerate(
        self,
        *,
        schema: type[T],
        prompt: str,
        system_prompt: str | None = None,
        media: list[MediaPart] | None = None,
    ) -> T:
        raise NotImplementedError
