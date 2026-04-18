from __future__ import annotations

"""
Detect Chinese on-screen text in video frames using Gemini vision,
then overlay English translations via ffmpeg drawtext.

Pipeline:
  1. extract_frames()       — sample one frame per second as JPEG
  2. detect_text_in_frames()— Gemini vision: detect ZH text + translate
  3. build_overlay_timeline()— merge adjacent identical frames into timed spans
  4. apply_text_overlays()  — ffmpeg complex drawtext filter → final video
"""
import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path
from google import genai
from google.genai import types


# ── Frame extraction ──────────────────────────────────────────

def extract_frames(
    video_path: str,
    work_dir: str,
    *,
    interval: float = 1.0,
) -> list[tuple[float, str]]:
    """
    Extract one frame every `interval` seconds as JPEG.
    Returns list of (timestamp_sec, frame_path).
    """
    out = Path(work_dir) / "frames"
    out.mkdir(parents=True, exist_ok=True)

    # ffmpeg: output frame_%04d.jpg at 1/interval fps
    fps = 1.0 / interval
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path,
         "-vf", f"fps={fps}",
         "-q:v", "3",
         str(out / "frame_%04d.jpg")],
        capture_output=True, check=True,
    )

    frames = sorted(out.glob("frame_*.jpg"))
    return [(i * interval, str(f)) for i, f in enumerate(frames)]


# ── Gemini vision: detect ZH text in a single frame ──────────

_DETECT_PROMPT = (
    "Look at this video frame. Find all visible Chinese text (characters, words, labels, titles, captions).\n"
    "For each piece of Chinese text, return a JSON object with:\n"
    '  "zh": the original Chinese text\n'
    '  "en": natural English translation\n'
    '  "x_pct": horizontal center of the text as % of frame width (0=left, 100=right)\n'
    '  "y_pct": vertical center of the text as % of frame height (0=top, 100=bottom)\n'
    "Return ONLY a JSON array. If no Chinese text is visible, return [].\n"
    "Ignore subtitles at the very bottom (those are handled separately)."
)


def detect_text_in_frame(
    frame_path: str,
    *,
    api_key: str | None = None,
) -> list[dict]:
    """
    Use Gemini vision to detect and translate Chinese text in a frame.
    Returns list of {zh, en, x_pct, y_pct}.
    """
    client = genai.Client(api_key=api_key or os.environ["GOOGLE_API_KEY"])
    img_bytes = Path(frame_path).read_bytes()
    b64 = base64.b64encode(img_bytes).decode()

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=b64)),
            _DETECT_PROMPT,
        ],
    )
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        return json.loads(raw)  # type: ignore[return-value]
    except json.JSONDecodeError:
        return []


# ── Build overlay timeline ────────────────────────────────────

def build_overlay_timeline(
    frame_results: list[tuple[float, list[dict]]],
    *,
    interval: float = 1.0,
) -> list[dict]:
    """
    Merge consecutive frames that have the same on-screen text into timed spans.
    Returns list of {zh, en, x_pct, y_pct, t_start, t_end}.
    """
    # Flatten all (timestamp, text_item) pairs
    # Group by text content; track first/last appearance
    seen: dict[str, dict] = {}  # key = zh text

    for ts, items in frame_results:
        for item in items:
            key = item["zh"]
            if key not in seen:
                seen[key] = {**item, "t_start": ts, "t_end": ts + interval}
            else:
                seen[key]["t_end"] = ts + interval

    return list(seen.values())


# ── ffmpeg drawtext filter ────────────────────────────────────

def _escape(s: str) -> str:
    """Escape special characters for ffmpeg drawtext."""
    return s.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")


def apply_text_overlays(
    video_path: str,
    audio_path: str,
    srt_path: str,
    overlays: list[dict],
    output_path: str,
    *,
    video_width: int = 1280,
    video_height: int = 720,
    font_size: int = 28,
    font_color: str = "yellow",
    box_color: str = "black@0.5",
) -> str:
    """
    Combine:
      - audio swap (dubbed TTS)
      - EN subtitle burn (from SRT)
      - EN text overlays replacing ZH on-screen text
    into a single ffmpeg pass.
    """
    ffmpeg_bin = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
    srt_escaped = os.path.abspath(srt_path).replace("'", "\\'")

    # Build subtitle + drawtext filter chain
    filters: list[str] = [f"subtitles={srt_escaped}"]

    for ov in overlays:
        x = int(ov["x_pct"] / 100 * video_width)
        y = int(ov["y_pct"] / 100 * video_height)
        # Centre the text box on the detected position
        t_start = ov["t_start"]
        t_end   = ov["t_end"]
        en_text = _escape(ov["en"])

        filters.append(
            f"drawtext=text='{en_text}'"
            f":fontsize={font_size}"
            f":fontcolor={font_color}"
            f":box=1:boxcolor={box_color}:boxborderw=6"
            f":x={x}-text_w/2:y={y}-text_h/2"
            f":enable='between(t,{t_start},{t_end})'"
        )

    vf = ",".join(filters)

    result = subprocess.run([
        ffmpeg_bin, "-y",
        "-i", os.path.abspath(video_path),
        "-i", os.path.abspath(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-vf", vf,
        "-c:a", "aac",
        "-shortest",
        os.path.abspath(output_path),
    ], capture_output=True)

    if result.returncode != 0:
        print("ffmpeg stderr:", result.stderr.decode()[-800:])
        result.check_returncode()
    return output_path


# ── High-level entry point ────────────────────────────────────

def translate_onscreen_text(
    video_path: str,
    work_dir: str,
    *,
    api_key: str | None = None,
    interval: float = 1.0,
) -> list[dict]:
    """
    Full detection pass: extract frames → Gemini vision → overlay timeline.
    Returns the overlay list (pass to apply_text_overlays).
    """
    print(f"  Extracting frames (every {interval}s)...")
    frames = extract_frames(video_path, work_dir, interval=interval)
    print(f"  Analysing {len(frames)} frames with Gemini vision...")

    frame_results: list[tuple[float, list[dict]]] = []
    for ts, frame_path in frames:
        items = detect_text_in_frame(frame_path, api_key=api_key)
        if items:
            print(f"    t={ts:.1f}s → {[i['zh'] for i in items]}")
        frame_results.append((ts, items))

    overlays = build_overlay_timeline(frame_results, interval=interval)
    print(f"  Found {len(overlays)} unique on-screen text items.")
    return overlays
