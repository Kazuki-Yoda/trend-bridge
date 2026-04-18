"""Zero-arg demo: run A + L on every bundled sample, sort, return outcomes.

Internally dispatches ``cli.run_score`` for each sample so the demo reads
as real arg-passing rather than hardcoded inline logic. See DESIGN.md §5, §9.
"""

from __future__ import annotations

import logging
from pathlib import Path

from trend_bridge.schemas import (
    HookAnalysis,
    LocalizationPlan,
    ScoreOutcome,
    ScoringReport,
    VideoMetadata,
)

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
_SOURCE_DIR = REPO_ROOT / "samples" / "source_videos"
_DEFAULT_TARGET = "us-tiktok"


def run_demo() -> list[ScoreOutcome]:
    """Run ``run_score`` over every bundled sample and return sorted outcomes."""
    from trend_bridge.cli import run_score  # avoid import cycle at module load

    pairs = _discover_pairs()
    if not pairs:
        log.warning("No bundled source videos found under %s", _SOURCE_DIR)
        return []

    outcomes: list[ScoreOutcome] = []
    for mp4, meta in pairs:
        log.info("--- Processing %s ---", mp4.name)
        try:
            outcomes.append(
                run_score(source=mp4, metadata_path=meta, target=_DEFAULT_TARGET)
            )
        except Exception as exc:  # noqa: BLE001 — demo must not crash
            log.error("Failed on %s: %s", mp4.name, exc, exc_info=True)
            outcomes.append(_stub_outcome(mp4, meta, exc))

    outcomes.sort(key=lambda o: o.report.fit_score, reverse=True)
    return outcomes


def _discover_pairs() -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for mp4 in sorted(_SOURCE_DIR.glob("*.mp4")):
        meta = mp4.with_suffix(".json")
        if meta.exists():
            pairs.append((mp4, meta))
    return pairs


def _stub_outcome(mp4: Path, meta: Path, exc: Exception) -> ScoreOutcome:
    try:
        metadata = VideoMetadata.model_validate_json(meta.read_text(encoding="utf-8"))
    except Exception:
        metadata = VideoMetadata(title=mp4.stem, source_platform="bilibili")
    report = ScoringReport(
        fit_score=0,
        confidence="low",
        one_line_verdict="(analysis failed)",
        top_reasons_works=[],
        top_reasons_struggles=[],
        trend_pattern_matches=[],
        cultural_flags=[],
        hook_analysis=HookAnalysis(
            source_hook="(unavailable)",
            target_audience_fit="needs_rework",
            suggested_target_hook="(unavailable)",
        ),
        notes=str(exc),
    )
    plan = LocalizationPlan(
        summary="(analysis failed)",
        target_language="en-US",
        suggested_new_title=metadata.title,
        suggested_new_caption="",
        suggested_hashtags=[],
        actions=[],
        estimated_effort="light",
    )
    return ScoreOutcome(metadata=metadata, report=report, plan=plan)
