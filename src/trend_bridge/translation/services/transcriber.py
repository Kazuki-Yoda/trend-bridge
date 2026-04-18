from __future__ import annotations

"""Transcribe video audio using Gemini multimodal (for videos without subtitles)."""
import base64
import json
import os
from pathlib import Path
from google import genai
from google.genai import types


def transcribe_video(
    video_path: str,
    *,
    api_key: str | None = None,
    source_lang: str = "Chinese",
    duration_hint: float | None = None,
) -> list[dict[str, str]]:
    """
    Transcribe video audio into timed segments using Gemini.
    Returns list of {start, end, text} dicts (timestamps in HH:MM:SS.mmm format).
    """
    client = genai.Client(api_key=api_key or os.environ["GOOGLE_API_KEY"])
    video_bytes = Path(video_path).read_bytes()
    b64 = base64.b64encode(video_bytes).decode()

    duration_note = f" The video is approximately {duration_hint:.1f} seconds long." if duration_hint else ""
    prompt = (
        f"Transcribe all spoken {source_lang} dialogue in this video into timed segments.{duration_note} "
        "Return ONLY a JSON array where each element has: "
        '"start" (HH:MM:SS.mmm), "end" (HH:MM:SS.mmm), "text" (spoken text). '
        "Cover every spoken word. No explanations."
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part(inline_data=types.Blob(mime_type="video/mp4", data=b64)),
            prompt,
        ],
    )
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)  # type: ignore[return-value]
