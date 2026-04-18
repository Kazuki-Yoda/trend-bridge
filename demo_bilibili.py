from __future__ import annotations

"""
Pipeline demo: translate a Bilibili video (no subtitles) to English with dubbed audio.
Auto-detects speaker gender and selects matching TTS voice.

Usage:
    GOOGLE_API_KEY=... python3 demo_bilibili.py
"""
import os
import sys

sys.path.insert(0, "src")

from trend_bridge.translation.services.fetcher import fetch_video
from trend_bridge.translation.services.transcriber import transcribe_video
from trend_bridge.translation.services.translator import translate_batch
from trend_bridge.translation.services.localizer import localize_segments
from trend_bridge.translation.services.gender_detect import detect_speaker_gender, pick_voice
from trend_bridge.translation.services.tts import build_timed_audio, build_srt, swap_audio_and_burn_subs

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyByXXl3lqJ_Avqw7k_YWlZzu_IrLPQmeeU")
BILIBILI_URL = "https://www.bilibili.com/video/BV1BW4y1n7QQ"
TMP_DIR = "tmp/bilibili"
DURATION = 20  # seconds


def step(n: int, label: str) -> None:
    print(f"\n{'='*60}")
    print(f"  STEP {n}: {label}")
    print(f"{'='*60}")


def ts_to_sec(ts: str) -> float:
    parts = ts.replace(",", ".").split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(parts[0])


# ── STEP 1: Download Bilibili video ───────────────────────────
step(1, "Download Bilibili video (first 20s)")
paths = fetch_video(BILIBILI_URL, TMP_DIR, duration_seconds=DURATION)
print(f"  Video: {paths['video']}")
print(f"  Subtitle: {paths['subtitle_vtt']} (expected None for this video)")

# ── STEP 2: Detect speaker gender ─────────────────────────────
step(2, "Detect speaker gender via Gemini")
video_path = paths["video"]
assert video_path, "Video download failed"
gender = detect_speaker_gender(video_path, api_key=GOOGLE_API_KEY)
voice = pick_voice(gender)
print(f"  Detected gender: {gender} → voice: {voice}")

# ── STEP 3: Transcribe audio with Gemini ──────────────────────
step(3, "Transcribe Chinese speech via Gemini")
segments = transcribe_video(video_path, api_key=GOOGLE_API_KEY, duration_hint=float(DURATION))
segments = [s for s in segments if ts_to_sec(s["start"]) <= DURATION]
for s in segments:
    print(f"  [{s['start']} → {s['end']}] {s['text']}")

# ── STEP 4: Translate ZH → EN (literal) ───────────────────────
step(4, "Translate ZH → EN (literal)")
texts_zh = [s["text"] for s in segments]
texts_en_literal = translate_batch(texts_zh, api_key=GOOGLE_API_KEY)
for i, seg in enumerate(segments):
    seg["text_en_literal"] = texts_en_literal[i]
    print(f"  ZH: {seg['text']}")
    print(f"  EN: {texts_en_literal[i]}")
    print()

# ── STEP 5: Cultural rewrite with Gemini ──────────────────────
step(5, "Gemini: Cultural rewrite for YouTube/US audience")
segments = localize_segments(segments, api_key=GOOGLE_API_KEY)
for s in segments:
    print(f"  Literal: {s['text_en_literal']}")
    print(f"  Rewrite: {s['text_en']}")
    print()

# ── STEP 6: TTS (gender-matched voice) ────────────────────────
step(6, f"Gemini TTS ({gender} voice: {voice}): generate timed English audio")
audio_path = build_timed_audio(segments, api_key=GOOGLE_API_KEY, voice=voice, work_dir=TMP_DIR)
print(f"  Timed audio: {audio_path}")

# ── STEP 7: Generate English SRT ──────────────────────────────
step(7, "Generate English SRT subtitles")
srt_content = build_srt(segments)
srt_path = f"{TMP_DIR}/en.srt"
os.makedirs(TMP_DIR, exist_ok=True)
with open(srt_path, "w") as f:
    f.write(srt_content)
print(srt_content)

# ── STEP 8: Swap audio + burn subtitles ───────────────────────
step(8, "ffmpeg: swap audio + burn EN subtitles into video")
output_path = f"{TMP_DIR}/dubbed_en_final.mp4"
swap_audio_and_burn_subs(video_path, audio_path, srt_path, output_path)
size = os.path.getsize(output_path)
print(f"  Output: {output_path} ({size/1024:.0f} KB)")
print("\nDone! English-dubbed video with subtitles saved.")
