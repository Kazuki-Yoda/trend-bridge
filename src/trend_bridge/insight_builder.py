"""Offline builder for the regional-insight corpus (``D``).

Runs once, commits the output JSON under ``samples/insights/<slug>.json``.
Today the corpus is LLM-synthesized; a future iteration will ingest real
trending data into the same schema. See DESIGN.md §5.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from trend_bridge.api_clients.gemini import GeminiStructuredOutputService
from trend_bridge.schemas import RegionalInsight

log = logging.getLogger(__name__)


_SYSTEM_PROMPT = """\
You are a short-form-video trend analyst. When asked to synthesize a sample \
of currently-trending videos on a named platform in a named region, produce \
realistic, varied, specific entries that reflect actually-dominant patterns: \
recurring formats, creator niches, hook styles, pacing, audio conventions, \
and language register. Avoid placeholders. Output must validate against the \
provided Pydantic schema."""


_USER_PROMPT_TEMPLATE = """\
Generate {n} plausible trending short-form videos currently popular on \
{platform} in {region}.

Requirements:
- Every video must be specific: real-sounding title, caption-worthy hook, \
named creator niche. No "example video 1", no placeholder strings.
- Span a VARIETY of topics, niches, formats, and emotional tones; don't \
cluster everything into one genre.
- pacing, visual_signature, and audio_style should reflect what actually \
dominates the platform's feed.
- length_sec should match the platform's norm.
- language_register should be platform-appropriate.
- Titles should feel natural (emoji, question-bait, POV prefixes, list \
formats) where that matches the platform's voice.

Top-level fields:
- region: "{region}"
- platform: "{platform}"
- generated_at: "{generated_at}"
- videos: the list of {n} entries"""


def build_insight(
    *,
    region: str,
    platform: str,
    n: int,
    service: GeminiStructuredOutputService,
) -> RegionalInsight:
    """Generate a synthetic regional-insight corpus with ``n`` trending videos."""
    generated_at = datetime.now(timezone.utc).isoformat()
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        n=n, region=region, platform=platform, generated_at=generated_at
    )
    log.info(
        "Generating RegionalInsight (region=%s, platform=%s, n=%d)", region, platform, n
    )
    return service.generate(
        schema=RegionalInsight,
        prompt=user_prompt,
        system_prompt=_SYSTEM_PROMPT,
    )


def write_insight(insight: RegionalInsight, out_path: Path) -> None:
    """Serialize ``insight`` to ``out_path`` as pretty-printed JSON."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(insight.model_dump_json(indent=2), encoding="utf-8")
    log.info("Wrote RegionalInsight to %s", out_path)
