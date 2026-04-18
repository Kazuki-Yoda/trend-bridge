"""Offline builder for the regional-insight corpus (``D``).

Runs once, commits the output JSON under ``samples/insights/<region>_<platform>.json``.
Today the corpus is LLM-synthesized; a future iteration will ingest real
trending data into the same schema. See DESIGN.md §5.
"""

from __future__ import annotations

from pathlib import Path

from trend_bridge.api_clients.gemini import GeminiStructuredOutputService
from trend_bridge.schemas import RegionalInsight


def build_insight(
    *,
    region: str,
    platform: str,
    n: int,
    service: GeminiStructuredOutputService,
) -> RegionalInsight:
    """Generate a synthetic regional-insight corpus with ``n`` trending videos."""
    raise NotImplementedError


def write_insight(insight: RegionalInsight, out_path: Path) -> None:
    """Serialize ``insight`` to ``out_path`` as pretty-printed JSON."""
    raise NotImplementedError
