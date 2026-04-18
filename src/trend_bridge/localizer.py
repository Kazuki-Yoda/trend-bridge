"""L: produce a localization plan for a source video.

Consumes A's ``ScoringReport`` as prompt context so L can focus on concrete
remix actions without re-deriving fit reasoning. One Gemini call per
invocation. See DESIGN.md §5.
"""

from __future__ import annotations

import logging

from trend_bridge.api_clients.gemini import (
    GeminiStructuredOutputService,
    MediaPart,
)
from trend_bridge.schemas import LocalizationPlan, ScoringReport, VideoMetadata

log = logging.getLogger(__name__)


_SYSTEM_PROMPT = """\
You are a creator's remix-planning partner. A scoring pass has already \
analysed this SOURCE video against what's trending on the TARGET platform. \
Your job is to turn that analysis into a concrete, prioritized \
LocalizationPlan the creator can execute.

Be concrete:
- suggested_new_title and suggested_new_caption must be in the target \
language; mirror typical target-platform voice.
- suggested_hashtags = 3-7 entries that are actually in use on the target \
platform for similar content. No leading '#'.
- Each LocalizationAction.action must be a specific instruction a human can \
follow ("Replace the BGM with a 120+ BPM trending audio", not "fix the music"). \
Cite the source's existing element when useful.
- Priority: "must" = needed for the video to work at all in the target \
market; "should" = clear win; "nice" = polish.
- Drive advice from the ScoringReport's reasons, cultural flags, and hook \
analysis. Do not contradict the scoring or re-score."""


_USER_PROMPT_TEMPLATE = """\
# Source video metadata (from {source_platform})
Title: {title}
Caption: {caption}
Hashtags: {hashtags}

# Prior ScoringReport (A's analysis)

```json
{report_json}
```

# Task
Watch the attached source video again with the ScoringReport in mind and \
produce a LocalizationPlan. Target language: {target_language}."""


def plan_localization(
    *,
    media: MediaPart,
    metadata: VideoMetadata,
    report: ScoringReport,
    service: GeminiStructuredOutputService,
    target_language: str = "en-US",
) -> LocalizationPlan:
    """Produce a prioritized localization plan for ``media``."""
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        source_platform=metadata.source_platform,
        title=metadata.title,
        caption=metadata.caption or "(none)",
        hashtags=", ".join(metadata.hashtags) if metadata.hashtags else "(none)",
        report_json=report.model_dump_json(indent=2),
        target_language=target_language,
    )
    log.info("Planning localization for '%s' (target=%s)", metadata.title, target_language)
    return service.generate(
        schema=LocalizationPlan,
        prompt=user_prompt,
        system_prompt=_SYSTEM_PROMPT,
        media=[media],
    )
