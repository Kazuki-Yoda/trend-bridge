"""FastAPI web UI for Trend Bridge — serves ``frontend/index.html`` + JSON API.

Reuses ``demo.run_demo`` directly. Set ``TB_MOCK=replay`` before starting the
server to hit the committed Gemini cache under ``samples/gemini_cache/``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from trend_bridge.demo import run_demo
from trend_bridge.schemas import ScoreOutcome, VideoMetadata

REPO_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = REPO_ROOT / "frontend"
VIDEOS_DIR = REPO_ROOT / "samples" / "source_videos"

app = FastAPI(title="Trend Bridge")

app.mount("/videos", StaticFiles(directory=VIDEOS_DIR), name="videos")
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


class OutcomeView(BaseModel):
    outcome: ScoreOutcome
    video_url: str


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/outcomes")
def outcomes() -> list[OutcomeView]:
    """Return all demo outcomes, each paired with its source video URL."""
    scored = run_demo()
    by_title: dict[str, ScoreOutcome] = {o.metadata.title: o for o in scored}

    views: list[OutcomeView] = []
    for mp4 in sorted(VIDEOS_DIR.glob("*.mp4")):
        meta_path = mp4.with_suffix(".json")
        if not meta_path.exists():
            continue
        meta = VideoMetadata.model_validate_json(meta_path.read_text(encoding="utf-8"))
        outcome = by_title.get(meta.title)
        if outcome is None:
            continue
        views.append(OutcomeView(outcome=outcome, video_url=f"/videos/{mp4.name}"))

    views.sort(key=lambda v: v.outcome.report.fit_score, reverse=True)
    return views
