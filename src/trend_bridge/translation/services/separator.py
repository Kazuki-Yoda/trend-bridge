from __future__ import annotations

"""Separate voice from background music using Demucs."""
import subprocess
from pathlib import Path


def separate_voice(video_path: str, output_dir: str) -> str:
    """Extract vocals from video audio using Demucs. Returns path to vocals WAV."""
    out = Path(output_dir)
    audio_path = out / "audio.wav"

    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-ar", "44100", "-ac", "2", str(audio_path)],
        capture_output=True, check=True,
    )
    subprocess.run(
        ["python3", "-m", "demucs", "--two-stems", "vocals", "--out", str(out / "demucs"), str(audio_path)],
        capture_output=True, check=True,
    )

    vocals = list(out.glob("demucs/**/vocals.wav"))
    if not vocals:
        raise FileNotFoundError("Demucs did not produce vocals.wav")
    return str(vocals[0])
