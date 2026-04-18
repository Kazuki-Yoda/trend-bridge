"""Pydantic schemas shared across the cross-region viral predictor pipeline.

These are the load-bearing data contracts: runtime inputs (VideoMetadata), the
offline regional-insight corpus (RegionalInsight), and the two Gemini
``response_schema`` outputs (ScoringReport, LocalizationPlan). See
``docs/plans/cross-region-viral-predictor/DESIGN.md`` §4.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


# --- Input: metadata JSON bundled with each source video -------------------


class VideoMetadata(BaseModel):
    title: str
    caption: str | None = None
    hashtags: list[str] = []
    source_platform: Literal["douyin", "bilibili", "xiaohongshu"]
    original_url: str | None = None


# --- D: regional-insight corpus --------------------------------------------


class TrendingVideoSynth(BaseModel):
    title: str
    hook_style: str
    topic_category: str
    pacing: Literal["slow", "medium", "fast", "very_fast"]
    visual_signature: str
    audio_style: str
    language_register: Literal["casual", "slang", "formal", "meme"]
    length_sec: int
    emotional_tone: str
    format: Literal["talking-head", "tutorial", "skit", "pov", "list", "other"]
    creator_niche: str


class RegionalInsight(BaseModel):
    region: str
    platform: str
    generated_at: str
    videos: list[TrendingVideoSynth]


# --- A: scoring report -----------------------------------------------------


class TrendPatternMatch(BaseModel):
    trend_pattern_name: str
    match_strength: int
    rationale: str


class CulturalFlag(BaseModel):
    severity: Literal["info", "caution", "blocker"]
    category: Literal["taboo", "language", "visual_norm", "format", "legal_ip"]
    message: str


class HookAnalysis(BaseModel):
    source_hook: str
    target_audience_fit: Literal["strong", "weak", "needs_rework"]
    suggested_target_hook: str


class ScoringReport(BaseModel):
    fit_score: int
    confidence: Literal["low", "medium", "high"]
    one_line_verdict: str
    top_reasons_works: list[str]
    top_reasons_struggles: list[str]
    trend_pattern_matches: list[TrendPatternMatch]
    cultural_flags: list[CulturalFlag]
    hook_analysis: HookAnalysis
    notes: str | None = None


# --- L: localization plan --------------------------------------------------


class LocalizationAction(BaseModel):
    priority: Literal["must", "should", "nice"]
    area: Literal[
        "language", "captions", "music", "pacing", "length", "visuals", "cta", "hashtags"
    ]
    action: str
    rationale: str


class LocalizationPlan(BaseModel):
    summary: str
    target_language: str
    suggested_new_title: str
    suggested_new_caption: str
    suggested_hashtags: list[str]
    actions: list[LocalizationAction]
    estimated_effort: Literal["light", "moderate", "heavy"]
