from __future__ import annotations

"""TTS: convert English segments to timed speech, then swap into video."""
import io
import os
import struct
import subprocess
import time
from google import genai
from google.genai import types


VOICES: dict[str, list[str]] = {
    "male":   ["Charon", "Puck", "Fenrir"],
    "female": ["Aoede", "Kore"],
}


def synthesize_segment(text: str, *, api_key: str | None = None, voice: str = "Aoede") -> bytes:
    """Generate WAV bytes for a single text segment."""
    client = genai.Client(api_key=api_key or os.environ["GOOGLE_API_KEY"])
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        ),
    )
    pcm = response.candidates[0].content.parts[0].inline_data.data
    return _pcm_to_wav(pcm, sample_rate=24000)


def _pcm_to_wav(pcm_data: bytes, *, sample_rate: int = 24000, channels: int = 1, bits: int = 16) -> bytes:
    buf = io.BytesIO()
    data_size = len(pcm_data)
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", data_size + 36))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, channels, sample_rate,
        sample_rate * channels * bits // 8, channels * bits // 8, bits))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(pcm_data)
    return buf.getvalue()


def _ts_to_sec(ts: str) -> float:
    """Convert HH:MM:SS.mmm or MM:SS.mmm to seconds."""
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return int(parts[0]) * 60 + float(parts[1])


def build_timed_audio(
    segments: list[dict[str, str]],
    *,
    api_key: str | None = None,
    voice: str = "Aoede",
    reference_wav: str | None = None,
    total_duration: float | None = None,
    work_dir: str = "/tmp",
) -> str:
    """
    Generate per-segment TTS and assemble into one audio track
    aligned to the original subtitle timestamps.

    If reference_wav is provided, uses XTTS-v2 voice cloning (cross-lingual).
    Otherwise uses Gemini TTS with the selected voice.
    Returns path to the assembled WAV file.
    """
    use_clone = reference_wav is not None
    if use_clone:
        from trend_bridge.translation.services.voice_clone import synthesize_with_clone
        # XTTS-v2 outputs 22050 Hz; adjust sample_rate accordingly
        sample_rate = 22050
        print(f"  Mode: XTTS-v2 voice clone (reference: {reference_wav})")
    else:
        sample_rate = 24000
        print(f"  Mode: Gemini TTS (voice: {voice})")

    channels = 1
    bits = 16
    bytes_per_sample = channels * bits // 8

    if total_duration is None:
        last = segments[-1]
        total_duration = _ts_to_sec(last["end"]) + 1.0

    total_samples = int(total_duration * sample_rate)
    pcm_track = bytearray(total_samples * bytes_per_sample)

    for i, seg in enumerate(segments):
        print(f"  TTS segment {i+1}/{len(segments)}: {seg['text_en']}")
        if use_clone:
            assert reference_wav is not None
            wav_bytes = synthesize_with_clone(seg["text_en"], reference_wav)
        else:
            if i > 0:
                time.sleep(7)  # stay under Gemini 10 RPM limit
            wav_bytes = synthesize_segment(seg["text_en"], api_key=api_key, voice=voice)
        pcm = wav_bytes[44:]  # strip WAV header

        start_sec = _ts_to_sec(seg["start"])
        end_sec = _ts_to_sec(seg["end"])
        seg_samples = int((end_sec - start_sec) * sample_rate)

        tts_samples = len(pcm) // bytes_per_sample
        if tts_samples > seg_samples > 0:
            ratio = min(tts_samples / seg_samples, 2.5)
            tmp_in = os.path.join(work_dir, f"seg_{i}_in.wav")
            tmp_out = os.path.join(work_dir, f"seg_{i}_out.wav")
            with open(tmp_in, "wb") as f:
                f.write(wav_bytes)
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_in, "-filter:a", f"atempo={ratio:.3f}", tmp_out],
                capture_output=True, check=True,
            )
            with open(tmp_out, "rb") as f:
                pcm = f.read()[44:]

        start_byte = int(start_sec * sample_rate) * bytes_per_sample
        end_byte = start_byte + len(pcm)
        if end_byte > len(pcm_track):
            end_byte = len(pcm_track)
            pcm = pcm[:end_byte - start_byte]
        pcm_track[start_byte:end_byte] = pcm

    out_path = os.path.join(work_dir, "tts_timed.wav")
    with open(out_path, "wb") as f:
        f.write(_pcm_to_wav(bytes(pcm_track), sample_rate=sample_rate))
    return out_path


def build_srt(segments: list[dict[str, str]]) -> str:
    """Generate SRT string from translated segments."""
    def ensure_hms(ts: str) -> str:
        parts = ts.replace(",", ".").split(":")
        if len(parts) == 2:
            ts = "00:" + ts
        return ts.replace(".", ",")

    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(f"{i}\n{ensure_hms(seg['start'])} --> {ensure_hms(seg['end'])}\n{seg['text_en']}\n")
    return "\n".join(lines)


def swap_audio_and_burn_subs(
    video_path: str,
    audio_path: str,
    srt_path: str,
    output_path: str,
) -> str:
    """Replace audio + burn English subtitles into video using ffmpeg."""
    srt_escaped = os.path.abspath(srt_path).replace("'", "\\'")
    ffmpeg_bin = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
    result = subprocess.run([
        ffmpeg_bin, "-y",
        "-i", os.path.abspath(video_path),
        "-i", os.path.abspath(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-vf", f"subtitles={srt_escaped}",
        "-c:a", "aac",
        "-shortest",
        os.path.abspath(output_path),
    ], capture_output=True)
    if result.returncode != 0:
        print("ffmpeg stderr:", result.stderr.decode()[-500:])
        result.check_returncode()
    return output_path
