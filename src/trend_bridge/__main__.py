"""Package entry point: ``python -m trend_bridge`` → :mod:`trend_bridge.cli`."""

from __future__ import annotations

import sys

from trend_bridge.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
