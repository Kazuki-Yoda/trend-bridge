from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from google.genai import types
from pydantic import BaseModel

from trend_bridge.api_clients.gemini.client import get_client
from trend_bridge.api_clients.gemini.media import MediaPart

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "gemini-3.1-pro-preview"

# Inline data limit for the Gemini API request body.
# Files larger than this are uploaded via the File API (up to 2 GB per file).
_INLINE_MAX_BYTES = 20 * 1024 * 1024  # 20 MB


@dataclass
class GeminiConfig:
    """Configuration for the Gemini structured output client."""

    model: str = DEFAULT_MODEL
    temperature: float = 0.2
    max_output_tokens: int | None = None
    top_p: float | None = None
    top_k: int | None = None


@dataclass
class GeminiStructuredOutputService:
    """Gemini client that returns structured Pydantic objects.

    Accepts multimodal inputs (text, images, video) and produces
    responses validated against a caller-supplied Pydantic schema.
    """

    config: GeminiConfig = field(default_factory=GeminiConfig)

    def generate(
        self,
        *,
        schema: type[T],
        prompt: str,
        system_prompt: str | None = None,
        media: list[MediaPart] | None = None,
    ) -> T:
        """Generate a structured response synchronously.

        Args:
            schema: Pydantic model class used as the response schema.
            prompt: User text prompt.
            system_prompt: Optional system instruction.
            media: Optional list of image/video inputs.

        Returns:
            A validated instance of ``schema``.
        """
        contents = self._build_contents(media, prompt)
        gen_config = self._build_gen_config(schema, system_prompt)

        response = get_client().models.generate_content(
            model=self.config.model,
            contents=contents,
            config=gen_config,
        )

        if response.parsed is not None:
            return response.parsed  # type: ignore[return-value]
        if response.text is None:
            raise ValueError("Gemini returned an empty response")
        return schema.model_validate_json(response.text)

    async def agenerate(
        self,
        *,
        schema: type[T],
        prompt: str,
        system_prompt: str | None = None,
        media: list[MediaPart] | None = None,
    ) -> T:
        """Generate a structured response asynchronously."""
        contents = self._build_contents(media, prompt)
        gen_config = self._build_gen_config(schema, system_prompt)

        response = await get_client().aio.models.generate_content(
            model=self.config.model,
            contents=contents,
            config=gen_config,
        )

        if response.parsed is not None:
            return response.parsed  # type: ignore[return-value]
        if response.text is None:
            raise ValueError("Gemini returned an empty response")
        return schema.model_validate_json(response.text)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_contents(
        self,
        media: list[MediaPart] | None,
        prompt: str,
    ) -> list[str | types.Part]:
        client = get_client()
        parts: list[str | types.Part] = []
        if media:
            for m in media:
                raw = self._resolve_bytes(m)
                if len(raw) <= _INLINE_MAX_BYTES:
                    parts.append(types.Part.from_bytes(data=raw, mime_type=m.mime_type))
                else:
                    uploaded = client.files.upload(
                        file=io.BytesIO(raw),
                        config=types.UploadFileConfig(mime_type=m.mime_type),
                    )
                    if uploaded.uri is None:
                        raise ValueError("File upload succeeded but returned no URI")
                    parts.append(
                        types.Part.from_uri(file_uri=uploaded.uri, mime_type=m.mime_type)
                    )
        parts.append(prompt)
        return parts

    @staticmethod
    def _resolve_bytes(media: MediaPart) -> bytes:
        if media.data is not None:
            return media.data
        if media.file_path is not None:
            return Path(media.file_path).read_bytes()
        raise ValueError("MediaPart requires data or file_path")

    def _build_gen_config(
        self,
        schema: type[T],
        system_prompt: str | None,
    ) -> types.GenerateContentConfig:
        kwargs: dict = {
            "response_mime_type": "application/json",
            "response_schema": schema,
            "temperature": self.config.temperature,
        }
        if system_prompt is not None:
            kwargs["system_instruction"] = system_prompt
        if self.config.max_output_tokens is not None:
            kwargs["max_output_tokens"] = self.config.max_output_tokens
        if self.config.top_p is not None:
            kwargs["top_p"] = self.config.top_p
        if self.config.top_k is not None:
            kwargs["top_k"] = self.config.top_k
        return types.GenerateContentConfig(**kwargs)
