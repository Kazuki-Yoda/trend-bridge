"""Round-trip sanity tests for the Pydantic schemas.

Catches field typos and ``Literal`` drift across the spec ↔ code boundary.
See DESIGN.md §8.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="scaffolded — implement with P0 schemas work")
