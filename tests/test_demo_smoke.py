"""End-to-end smoke test for ``python -m trend_bridge demo`` under ``TB_MOCK=replay``.

Asserts exit code 0 and that all bundled sources produce a non-stub report.
See DESIGN.md §8.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="scaffolded — implement after demo wiring lands")
