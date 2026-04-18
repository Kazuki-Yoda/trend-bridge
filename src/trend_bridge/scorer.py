"""A: score a single source video against a regional-insight corpus.

One Gemini call per invocation. See DESIGN.md §5 (data flow) and §4 (schema).
"""

from __future__ import annotations

import logging

from trend_bridge.api_clients.gemini import (
    GeminiStructuredOutputService,
    MediaPart,
)
from trend_bridge.schemas import RegionalInsight, ScoringReport, VideoMetadata

log = logging.getLogger(__name__)


_SYSTEM_PROMPT = """\
You are a cross-region short-form-video strategist. Given a SOURCE video \
(from a Chinese SNS platform) and a CORPUS of videos currently trending on \
a TARGET platform, produce a structured ScoringReport telling the creator \
how well this video would land with the target audience.

Be specific and honest:
- Coin 2-4 recurring TREND PATTERNS you observe in the provided corpus \
(e.g. "POV-transformation reveals", "slow-build storytime"). Don't just \
echo corpus titles. Score the source against these coined patterns.
- Score fit on 0-100. 50 = "could go either way". Don't inflate.
- top_reasons_works and top_reasons_struggles must cite OBSERVABLE features \
of the source (hook, pacing, visual signature, audio, language register, \
creator niche, format) — not generic advice.
- CulturalFlag.severity="blocker" is reserved for things that would genuinely \
tank the video: taboos, legal/IP issues, format incompatibilities. "caution" \
is the default for soft risks.
- hook_analysis.source_hook should paraphrase the first 2-3 seconds of the \
source. suggested_target_hook should be a concrete rewrite a creator could \
actually record.
- confidence="high" only when the corpus clearly covers the source's territory."""


_USER_PROMPT_TEMPLATE = """\
# Source video (from {source_platform})
Title: {title}
Caption: {caption}
Hashtags: {hashtags}
Original URL: {original_url}

# Target platform + region
Platform: {platform}
Region: {region}

# Corpus of currently-trending videos on the target platform
(Use this to coin TREND PATTERNS and score the source against them.)

```json
{insight_json}
```

# Task
Watch the attached source video, cross-reference with the trending corpus \
above, and produce a ScoringReport per the schema."""


def score_video(
    *,
    media: MediaPart,
    metadata: VideoMetadata,
    insight: RegionalInsight,
    service: GeminiStructuredOutputService,
) -> ScoringReport:
    """Score ``media`` against ``insight`` and return a structured report."""
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        source_platform=metadata.source_platform,
        title=metadata.title,
        caption=metadata.caption or "(none)",
        hashtags=", ".join(metadata.hashtags) if metadata.hashtags else "(none)",
        original_url=metadata.original_url or "(none)",
        platform=insight.platform,
        region=insight.region,
        insight_json=insight.model_dump_json(indent=2),
    )
    log.info(
        "Scoring '%s' against %s/%s insight (n=%d)",
        metadata.title,
        insight.region,
        insight.platform,
        len(insight.videos),
    )
    return service.generate(
        schema=ScoringReport,
        prompt=user_prompt,
        system_prompt=_SYSTEM_PROMPT,
        media=[media],
    )
