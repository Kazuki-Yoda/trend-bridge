"""Runs A against one bundled sample source under ``TB_MOCK=replay``.

Asserts the returned ``ScoringReport`` is non-trivial (``0 ≤ fit_score ≤ 100``,
at least one trend-pattern match, etc.). See DESIGN.md §8.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="scaffolded — implement after scorer + mock land")
