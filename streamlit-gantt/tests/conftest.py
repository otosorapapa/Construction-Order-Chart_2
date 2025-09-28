"""Pytest configuration for path resolution."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the application package root (containing ``utils`` and other modules)
# is importable when running tests from the repository root. This mirrors the
# path configuration that ``streamlit run`` performs automatically when
# launching the app from the ``streamlit-gantt`` directory.
APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
