"""Arg-driven CLI — ``score``, ``build-insight``, and ``demo`` subcommands.

``demo.py`` calls ``run_score`` directly for each bundled sample so the
zero-arg demo reads as real arg-passing rather than hardcoded inline logic.
See DESIGN.md §5 and §9.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from trend_bridge.api_clients.gemini import MediaPart, make_gemini_service
from trend_bridge.insight_builder import build_insight, write_insight
from trend_bridge.localizer import plan_localization
from trend_bridge.schemas import RegionalInsight, ScoreOutcome, VideoMetadata
from trend_bridge.scorer import score_video

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_score(
    *,
    source: Path,
    metadata_path: Path,
    target: str,
) -> ScoreOutcome:
    """Execute A + L for one source video.

    Logs progress via ``logging``; returns the bundled outcome. Stdout
    rendering is the caller's responsibility (see ``renderer``).
    """
    insight_path = _resolve_insight_path(target)
    insight = RegionalInsight.model_validate_json(
        insight_path.read_text(encoding="utf-8")
    )
    metadata = VideoMetadata.model_validate_json(
        metadata_path.read_text(encoding="utf-8")
    )
    media = MediaPart(file_path=str(source), mime_type=_mime_for(source))

    service = make_gemini_service()
    log.info("run_score: source=%s target=%s", source.name, target)
    report = score_video(
        media=media, metadata=metadata, insight=insight, service=service
    )
    plan = plan_localization(
        media=media, metadata=metadata, report=report, service=service
    )
    return ScoreOutcome(metadata=metadata, report=report, plan=plan)


def run_build_insight(
    *,
    region: str,
    platform: str,
    n: int,
    out_path: Path,
) -> None:
    """Execute the offline regional-insight builder and write the JSON fixture."""
    service = make_gemini_service()
    insight = build_insight(region=region, platform=platform, n=n, service=service)
    write_insight(insight, out_path)


def main(argv: list[str] | None = None) -> int:
    """Entry point dispatched by ``python -m trend_bridge``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(prog="trend_bridge")
    sub = parser.add_subparsers(dest="command", required=True)

    p_score = sub.add_parser(
        "score", help="Score one source video against a target corpus"
    )
    p_score.add_argument("--source", type=Path, required=True)
    p_score.add_argument("--metadata", type=Path, required=True)
    p_score.add_argument("--target", required=True, help="e.g., us-tiktok")

    p_build = sub.add_parser("build-insight", help="Build a regional-insight corpus")
    p_build.add_argument("--region", required=True)
    p_build.add_argument("--platform", required=True)
    p_build.add_argument("--n", type=int, default=12)
    p_build.add_argument("--out", type=Path, required=True)

    sub.add_parser("demo", help="Run the zero-arg demo over bundled samples")

    p_serve = sub.add_parser("serve", help="Serve the FastAPI web UI (app.py)")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "score":
        from trend_bridge.renderer import render_pair

        outcome = run_score(
            source=args.source, metadata_path=args.metadata, target=args.target
        )
        render_pair(outcome)
        return 0

    if args.command == "build-insight":
        run_build_insight(
            region=args.region,
            platform=args.platform,
            n=args.n,
            out_path=args.out,
        )
        return 0

    if args.command == "demo":
        from trend_bridge.demo import run_demo
        from trend_bridge.renderer import render_demo

        outcomes = run_demo()
        render_demo(outcomes)
        return 0

    if args.command == "serve":
        import uvicorn

        uvicorn.run(
            "app:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
        return 0

    return 1


# ---- helpers ---------------------------------------------------------------


def _resolve_insight_path(target: str) -> Path:
    """Map a target slug like ``us-tiktok`` to its insight JSON path."""
    slug = target.lower().replace("-", "_")
    path = REPO_ROOT / "samples" / "insights" / f"{slug}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Insight corpus not found at {path}. Run: "
            f"python -m trend_bridge build-insight --region US --platform TikTok "
            f"--n 12 --out {path}"
        )
    return path


def _mime_for(p: Path) -> str:
    ext = p.suffix.lower()
    return {
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".m4v": "video/mp4",
    }.get(ext, "application/octet-stream")
