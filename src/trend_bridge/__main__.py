"""Package entry point: ``python -m trend_bridge`` → :mod:`trend_bridge.cli`.

Also loads environment variables from ``.env`` at the repo root if present
(so ``GOOGLE_API_KEY`` can live there during dev without the user having to
``source .env`` first).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from trend_bridge.cli import main

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    env_path = _REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


if __name__ == "__main__":
    _load_dotenv()
    sys.exit(main(sys.argv[1:]))
