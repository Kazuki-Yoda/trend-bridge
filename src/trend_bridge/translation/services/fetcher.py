from __future__ import annotations

"""Download video + subtitles from YouTube/Bilibili using yt-dlp."""
import subprocess
from pathlib import Path


def fetch_video(url: str, output_dir: str, *, duration_seconds: int | None = None) -> dict[str, str | None]:
    """Download video and ZH subtitles. Returns paths to video and subtitle files."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    cmd = [
        "yt-dlp",
        "--write-subs",
        "--sub-langs", "zh,zh-Hans,zh-Hant",
        "--convert-subs", "vtt",
        "--format", "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--output", str(out / "video.%(ext)s"),
        "--no-playlist",
    ]

    if duration_seconds:
        cmd += ["--download-sections", f"*0-{duration_seconds}"]

    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr[:500]}")

    video_files = list(out.glob("video.mp4"))
    sub_files = list(out.glob("video.*.vtt"))

    return {
        "video": str(video_files[0]) if video_files else None,
        "subtitle_vtt": str(sub_files[0]) if sub_files else None,
    }


def parse_vtt(vtt_path: str) -> list[dict[str, str]]:
    """Parse VTT subtitle file into list of {start, end, text} dicts."""
    segments: list[dict[str, str]] = []
    with open(vtt_path, encoding="utf-8") as f:
        content = f.read()

    for block in content.strip().split("\n\n"):
        lines = block.strip().splitlines()
        time_line: int | None = None
        for i, line in enumerate(lines):
            if "-->" in line:
                time_line = i
                break
        if time_line is None:
            continue
        times = lines[time_line].split("-->")
        text = " ".join(
            t.strip() for t in lines[time_line + 1:]
            if t.strip() and not t.strip().startswith("<")
        )
        if text:
            segments.append({
                "start": times[0].strip(),
                "end": times[1].strip().split()[0],
                "text": text,
            })
    return segments
