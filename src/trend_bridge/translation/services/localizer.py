from __future__ import annotations

"""Culturally rewrite translated text for US/YouTube audience using Gemini."""
import json
import os
from google import genai


_SYSTEM_PROMPT = (
    "You are a cultural localization expert who adapts Chinese video content for English-speaking YouTube audiences. "
    "Given a list of literally-translated English subtitles, rewrite them so they: "
    "- Sound natural to a US/YouTube audience "
    "- Replace Chinese slang/idioms with English equivalents (e.g., 内卷 → 'the grind', yyds → 'GOAT') "
    "- Replace Chinese platform/culture references with familiar equivalents "
    "- Keep the same meaning and tone "
    "- Keep each subtitle short (max 15 words per segment) "
    "Return ONLY a JSON array of strings, one per input segment, in the same order."
)


def localize_segments(
    segments: list[dict[str, str]],
    *,
    api_key: str | None = None,
) -> list[dict[str, str]]:
    """Rewrite literally-translated subtitles for a US/YouTube audience."""
    client = genai.Client(api_key=api_key or os.environ["GOOGLE_API_KEY"])
    texts = [s["text_en_literal"] for s in segments]
    prompt = f"{_SYSTEM_PROMPT}\n\nInput:\n{json.dumps(texts, ensure_ascii=False)}"
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    localized: list[str] = json.loads(raw)
    return [{**seg, "text_en": localized[i]} for i, seg in enumerate(segments)]
