"""Entrypoint estável para smoke de release do frontend em :8080."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from check_frontend_parity import main

if __name__ == "__main__":
    raise SystemExit(main())
