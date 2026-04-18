from __future__ import annotations

"""Detect speaker gender from audio/video using Gemini multimodal."""
import os
import base64
from pathlib import Path
from google import genai
from google.genai import types


def detect_speaker_gender(video_path: str, *, api_key: str | None = None) -> str:
    """
    Detect the dominant speaker gender in a video.
    Returns 'male' or 'female'.
    """
    client = genai.Client(api_key=api_key or os.environ["GOOGLE_API_KEY"])
    video_bytes = Path(video_path).read_bytes()
    b64 = base64.b64encode(video_bytes).decode()

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part(inline_data=types.Blob(mime_type="video/mp4", data=b64)),
            "Listen to the speaker's voice in this video. "
            "Is the dominant speaker male or female? "
            "Reply with exactly one word: 'male' or 'female'.",
        ],
    )
    answer = response.text.strip().lower()
    return "female" if "female" in answer else "male"


def pick_voice(gender: str) -> str:
    """Pick a Gemini TTS voice matching the detected gender."""
    from trend_bridge.translation.services.tts import VOICES
    return VOICES[gender][0]
