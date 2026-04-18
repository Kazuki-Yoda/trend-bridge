"""Prompt-hash replay cache for ``GeminiStructuredOutputService`` (``TB_MOCK``).

Subclass with the same ``generate`` / ``agenerate`` surface. Modes:

* ``record`` — real call on miss, write response to ``samples/gemini_cache/``.
* ``replay`` — hit → return cached; miss → raise (no accidental billing).

Cache key is a SHA-256 over a sorted-key JSON payload of
``(model, system_prompt, user_prompt, schema, media_sha256_list)``. See
DESIGN.md §6.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel

from trend_bridge.api_clients.gemini.media import MediaPart
from trend_bridge.api_clients.gemini.structured_output import (
    GeminiStructuredOutputService,
)

T = TypeVar("T", bound=BaseModel)

MockMode = Literal["record", "replay"]

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CACHE_DIR = _REPO_ROOT / "samples" / "gemini_cache"

log = logging.getLogger(__name__)


@dataclass
class CachingGeminiStructuredOutputService(GeminiStructuredOutputService):
    """Caching wrapper around ``GeminiStructuredOutputService``."""

    mode: MockMode = "replay"

    def generate(
        self,
        *,
        schema: type[T],
        prompt: str,
        system_prompt: str | None = None,
        media: list[MediaPart] | None = None,
    ) -> T:
        key = self._cache_key(schema, prompt, system_prompt, media)
        cached = self._load_cache(key, schema)
        if cached is not None:
            log.info("TB_MOCK=%s cache HIT %s", self.mode, key[:12])
            return cached
        if self.mode == "replay":
            raise FileNotFoundError(
                f"TB_MOCK=replay cache MISS for {key[:12]}... "
                f"(schema={schema.__qualname__}). Re-run with TB_MOCK=record."
            )
        log.info("TB_MOCK=record cache MISS %s — calling Gemini", key[:12])
        result = super().generate(
            schema=schema,
            prompt=prompt,
            system_prompt=system_prompt,
            media=media,
        )
        self._write_cache(key, schema, prompt, system_prompt, result)
        return result

    async def agenerate(
        self,
        *,
        schema: type[T],
        prompt: str,
        system_prompt: str | None = None,
        media: list[MediaPart] | None = None,
    ) -> T:
        key = self._cache_key(schema, prompt, system_prompt, media)
        cached = self._load_cache(key, schema)
        if cached is not None:
            log.info("TB_MOCK=%s cache HIT %s", self.mode, key[:12])
            return cached
        if self.mode == "replay":
            raise FileNotFoundError(
                f"TB_MOCK=replay cache MISS for {key[:12]}... "
                f"(schema={schema.__qualname__}). Re-run with TB_MOCK=record."
            )
        log.info("TB_MOCK=record cache MISS %s — calling Gemini", key[:12])
        result = await super().agenerate(
            schema=schema,
            prompt=prompt,
            system_prompt=system_prompt,
            media=media,
        )
        self._write_cache(key, schema, prompt, system_prompt, result)
        return result

    # ---- helpers -------------------------------------------------------

    def _cache_key(
        self,
        schema: type[BaseModel],
        prompt: str,
        system_prompt: str | None,
        media: list[MediaPart] | None,
    ) -> str:
        payload = {
            "model": self.config.model,
            "system_prompt": system_prompt,
            "user_prompt": prompt,
            "schema": f"{schema.__module__}.{schema.__qualname__}",
            "media_sha256": [_sha256_media(m) for m in (media or [])],
        }
        canonical = json.dumps(
            payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _load_cache(self, key: str, schema: type[T]) -> T | None:
        path = _CACHE_DIR / f"{key}.json"
        if not path.exists():
            return None
        return schema.model_validate_json(path.read_text(encoding="utf-8"))

    def _write_cache(
        self,
        key: str,
        schema: type[BaseModel],
        prompt: str,
        system_prompt: str | None,
        result: BaseModel,
    ) -> None:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (_CACHE_DIR / f"{key}.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
        meta = {
            "model": self.config.model,
            "schema": f"{schema.__module__}.{schema.__qualname__}",
            "prompt_hash": key,
            "prompt_excerpt": prompt[:200],
            "system_prompt_excerpt": (system_prompt or "")[:200],
        }
        (_CACHE_DIR / f"{key}.meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def _sha256_media(m: MediaPart) -> str:
    if m.data is not None:
        return hashlib.sha256(m.data).hexdigest()
    if m.file_path is not None:
        return hashlib.sha256(Path(m.file_path).read_bytes()).hexdigest()
    raise ValueError("MediaPart requires data or file_path")
