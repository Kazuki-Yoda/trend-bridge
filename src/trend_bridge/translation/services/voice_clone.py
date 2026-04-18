from __future__ import annotations

"""
Cross-lingual voice cloning using XTTS-v2.

Workflow:
1. extract_reference_clip() — strip music with Demucs, take first N seconds of clean vocals.
2. synthesize_with_clone() — XTTS-v2 zero-shot: reference Chinese audio → English speech,
   same voice characteristics.

XTTS-v2 is multilingual: reference audio can be in any language; output language is set
separately. This is what makes zero-shot cross-lingual cloning work.
"""
import os
import subprocess
import tempfile
from pathlib import Path


_XTTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
_tts_instance = None  # lazy singleton — model load is slow (~10s)


def _get_tts():  # type: ignore[return]
    global _tts_instance
    if _tts_instance is None:
        from TTS.api import TTS  # type: ignore[import]
        os.environ.setdefault("COQUI_TOS_AGREED", "1")
        _tts_instance = TTS(model_name=_XTTS_MODEL, progress_bar=False)
    return _tts_instance


def extract_reference_clip(
    video_path: str,
    work_dir: str,
    *,
    duration: float = 8.0,
) -> str:
    """
    Extract a clean vocal reference clip from the video.
    Tries Demucs vocal separation first; falls back to raw audio if Demucs fails.
    Returns path to a mono 22050 Hz WAV clip suitable for XTTS-v2.
    """
    out = Path(work_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw_audio = out / "ref_raw.wav"
    ref_clip   = out / "ref_clip.wav"

    # 1. Extract audio from video
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-ar", "44100", "-ac", "1", str(raw_audio)],
        capture_output=True, check=True,
    )

    # 2. Try Demucs vocal separation
    vocals_path: Path | None = None
    try:
        demucs_out = out / "demucs"
        subprocess.run(
            ["python3.11", "-m", "demucs", "--two-stems", "vocals",
             "--out", str(demucs_out), str(raw_audio)],
            capture_output=True, check=True, timeout=120,
        )
        found = list(demucs_out.glob("**/vocals.wav"))
        if found:
            vocals_path = found[0]
    except Exception:
        pass  # fall back to raw audio

    source = str(vocals_path) if vocals_path else str(raw_audio)

    # 3. Trim to `duration` seconds and normalise to 22050 Hz mono (XTTS-v2 requirement)
    subprocess.run(
        ["ffmpeg", "-y", "-i", source, "-t", str(duration),
         "-ar", "22050", "-ac", "1", str(ref_clip)],
        capture_output=True, check=True,
    )
    print(f"  Reference clip: {ref_clip} ({'demucs vocals' if vocals_path else 'raw audio'})")
    return str(ref_clip)


def synthesize_with_clone(
    text: str,
    reference_wav: str,
    *,
    language: str = "en",
) -> bytes:
    """
    Synthesise `text` in the voice of `reference_wav` using XTTS-v2.
    Returns WAV bytes (22050 Hz mono 16-bit).
    reference_wav may be in any language — XTTS-v2 handles cross-lingual cloning.
    """
    tts = _get_tts()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out_path = f.name
    try:
        tts.tts_to_file(
            text=text,
            speaker_wav=reference_wav,
            language=language,
            file_path=out_path,
        )
        return Path(out_path).read_bytes()
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass
