"""Runs L against a cached ``ScoringReport`` under ``TB_MOCK=replay``.

Asserts the returned ``LocalizationPlan`` has at least one action and
``target_language`` set. See DESIGN.md §8.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="scaffolded — implement after localizer + mock land")
