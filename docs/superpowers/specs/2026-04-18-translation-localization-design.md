# Translation & Localization Pipeline — Design Spec

**Date:** 2026-04-18
**Owner:** Part 2 (teammate owns Part 1: evaluation)
**Status:** Implemented and demo-verified

---

## Problem

Chinese social media content (Bilibili, Douyin, etc.) can go viral in China but never reaches Western audiences. The barrier isn't just language — it's cultural: idioms, platform references, and slang land wrong even when translated literally.

Goal: given any Chinese video URL, produce an English-dubbed version with burned subtitles that sounds natural to a US/YouTube viewer.

---

## Pipeline Overview

```
Chinese video URL
        │
        ▼
┌─────────────────┐
│  1. FETCH       │  yt-dlp: download video + ZH subtitles (if any)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. SEGMENTS    │  Has subtitles? → parse VTT
│                 │  No subtitles?  → Gemini multimodal transcription
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. GENDER      │  Gemini multimodal: listen to speaker → "male" / "female"
│   DETECT        │  → selects TTS voice automatically
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. TRANSLATE   │  Gemini (gemini-2.0-flash): literal ZH → EN
│   (literal)     │  JSON array in, JSON array out — one string per segment
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. LOCALIZE    │  Gemini (gemini-2.0-flash): cultural rewrite
│   (rewrite)     │  内卷 → "the grind", yyds → "GOAT", Bilibili → YouTube, etc.
│                 │  Max 15 words per segment
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  6. TTS         │  Two modes (see below):
│                 │  A) Gemini TTS — generic gender-matched voice
│                 │  B) XTTS-v2   — cross-lingual voice clone of original speaker
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  7. ASSEMBLE    │  Timestamp-aligned PCM track:
│                 │  silence canvas → paste each segment at original timestamp
│                 │  ffmpeg atempo if TTS > slot duration (max 2.5× speed)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  8. BURN + DUB  │  ffmpeg: replace audio + burn EN subtitles (libass)
│                 │  → dubbed_en_final.mp4
└─────────────────┘
```

---

## Service Modules

All under `src/trend_bridge/translation/services/`.

| File | Purpose | Key function |
|------|---------|--------------|
| `fetcher.py` | Download video + parse subtitles | `fetch_video()`, `parse_vtt()` |
| `transcriber.py` | Gemini multimodal transcription (no-subtitle path) | `transcribe_video()` |
| `gender_detect.py` | Gemini multimodal gender detection + voice selection | `detect_speaker_gender()`, `pick_voice()` |
| `translator.py` | Gemini literal ZH→EN translation | `translate_batch()`, `translate_segments()` |
| `localizer.py` | Gemini cultural rewrite for US/YouTube | `localize_segments()` |
| `tts.py` | TTS dispatch + timed audio assembly + ffmpeg burn | `build_timed_audio()`, `build_srt()`, `swap_audio_and_burn_subs()` |
| `voice_clone.py` | XTTS-v2 cross-lingual voice cloning | `extract_reference_clip()`, `synthesize_with_clone()` |
| `separator.py` | Demucs vocal separation (used inside voice_clone) | `separate_voice()` |

---

## Segment Data Shape

Each segment is a plain `dict[str, str]` that grows keys as it moves through the pipeline:

```python
{
    "start": "00:01.517",       # original timestamp (HH:MM:SS.mmm or MM:SS.mmm)
    "end":   "00:03.847",
    "text":  "嬛嬛，朕，emo啦。",        # original Chinese
    # added by translator:
    "text_en_literal": "Huan Huan, I, am emo.",
    # added by localizer:
    "text_en": "Huan Huan, I'm feeling down.",
}
```

---

## TTS Mode A — Gemini TTS (default)

- Model: `gemini-2.5-flash-preview-tts`
- Voices: female → Aoede / Kore, male → Charon / Puck / Fenrir
- Rate limit: 10 RPM → 7s sleep between segment calls
- Output: 24000 Hz mono 16-bit PCM wrapped in WAV header
- Trigger: `VOICE_CLONE=0` (default)

## TTS Mode B — XTTS-v2 Voice Clone

- Model: Coqui `tts_models/multilingual/multi-dataset/xtts_v2` (local, ~1.8 GB download once)
- Reference audio: first 8s of video vocals (Demucs-separated if available, else raw audio)
- Cross-lingual: reference audio can be Chinese — output is English in same voice
- No rate limits, no API cost after model download
- Output: 22050 Hz mono 16-bit WAV
- Known deps: `transformers==4.40.2` (newer versions remove `BeamSearchScorer`), PyTorch `weights_only=False` patch in TTS `io.py`
- Trigger: `VOICE_CLONE=1` env var

---

## Audio Assembly

Both TTS modes produce per-segment WAV bytes. Assembly:

1. Allocate a silence buffer: `total_duration × sample_rate × 2 bytes`
2. For each segment, strip the 44-byte WAV header → raw PCM
3. If TTS audio is longer than the subtitle slot → speed up with `ffmpeg atempo` (capped at 2.5×)
4. Paste PCM bytes at `start_timestamp × sample_rate × 2` offset in the buffer
5. Write buffer as a WAV file → `tts_timed.wav`

---

## Final Video

```bash
ffmpeg -i video.mp4 -i tts_timed.wav \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -vf "subtitles=en.srt" \
  -c:a aac -shortest \
  dubbed_en_final.mp4
```

Uses `/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg` (system ffmpeg lacks libass for subtitle burning).

---

## Demo

```bash
# Default: Gemini TTS, gender-matched voice
GOOGLE_API_KEY=... python3.11 demo.py [URL] [DURATION_SECONDS] [OUTPUT_DIR]

# Voice clone: XTTS-v2, sounds like the original speaker
GOOGLE_API_KEY=... VOICE_CLONE=1 python3.11 demo.py [URL] [DURATION_SECONDS] [OUTPUT_DIR]
```

Defaults: Bilibili `BV1BW4y1n7QQ`, 20 seconds, `tmp/demo/`.

---

## Verified Demo Results

| Video | Subtitles | Gender | Voice | Mode | Output |
|-------|-----------|--------|-------|------|--------|
| YouTube GDP video (`P-NmMX9rlYQ`) | ZH VTT ✓ | — | Aoede (female) | Gemini TTS | ✓ |
| Bilibili 妲妲快emo啦 (`BV1BW4y1n7QQ`) | None | Male (Gemini) | XTTS-v2 clone | Voice clone | ✓ |

---

## External API Dependencies

| Service | Model | Used for | Key env var |
|---------|-------|----------|-------------|
| Gemini | `gemini-2.0-flash` | Translation, localization, transcription, gender detection | `GOOGLE_API_KEY` |
| Gemini TTS | `gemini-2.5-flash-preview-tts` | Speech synthesis (Mode A) | `GOOGLE_API_KEY` |
| Coqui XTTS-v2 | local | Voice cloning (Mode B) | — |
| yt-dlp | CLI | Video + subtitle download | — |
| ffmpeg-full | CLI | Audio assembly, video mux, subtitle burn | — |

---

## What Was Tried and Abandoned

**Seedance 2.0 omni-reference dubbing (BytePlus):**
- Original plan: upload video + TTS audio → Seedance generates lip-synced dubbed video
- `api.seedance.ai` domain is no longer reachable
- BytePlus ARK (`ark.ap-southeast.bytepluses.com`) accepts video file uploads but:
  - No audio upload support
  - No CDN URL returned for uploaded files (can't reference them in generation tasks)
  - Bilibili CDN URLs get blocked server-side ("resource download failed")
- Consistent `InternalServiceError` on omni-reference in earlier testing
- **Decision:** XTTS-v2 local voice cloning gives good results without these dependencies

**Google Translate API:**
- 403 Forbidden — Translation API not enabled on the project
- Replaced by Gemini for all translation tasks

**BytePlus TTS:**
- Separate credentials required (not the same API key as video generation)
- Replaced by Gemini TTS

---

## Open Questions / Future Work

- **Lip sync:** XTTS-v2 replaces the audio but doesn't retime lip movements. For perfect lip sync, Seedance dubbing would be ideal if it becomes stable.
- **On-screen text (UI/graphics in video):** Not handled in v1. Option: Gemini OCR → overlay translation.
- **Demucs availability:** Demucs not installed in current env → falls back to raw audio for voice clone reference. Quality improves with clean vocals.
- **Segment granularity:** Very short segments (<0.5s) produce poor TTS. Could merge adjacent short segments.
- **Bilibili auth:** Some videos require login cookies for yt-dlp; currently only public videos work.
