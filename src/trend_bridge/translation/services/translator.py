from __future__ import annotations

"""Translate text ZH → EN using Gemini API."""
import json
import os
from google import genai


def translate_batch(
    texts: list[str],
    *,
    api_key: str | None = None,
    target_lang: str = "English",
    source_lang: str = "Chinese",
) -> list[str]:
    """Literally translate a list of texts using Gemini."""
    client = genai.Client(api_key=api_key or os.environ["GOOGLE_API_KEY"])
    prompt = (
        f"Translate the following {source_lang} texts to {target_lang} literally and accurately. "
        f"Return ONLY a JSON array of strings, one per input, in the same order. "
        f"No explanations.\n\nInput:\n{json.dumps(texts, ensure_ascii=False)}"
    )
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)  # type: ignore[return-value]


def translate_segments(
    segments: list[dict[str, str]],
    *,
    api_key: str | None = None,
    target_lang: str = "English",
) -> list[dict[str, str]]:
    """Translate segment texts and add text_en_literal key."""
    texts = [s["text"] for s in segments]
    translated = translate_batch(texts, api_key=api_key, target_lang=target_lang)
    return [{**seg, "text_en_literal": translated[i]} for i, seg in enumerate(segments)]
