"""Global pytest configuration for the repository.

Adds the project root to *sys.path* so that helper stubs (e.g. the
light-weight ``fsspec`` replacement located at ``/fsspec``) are
importable regardless of the directory from which pytest collects
tests.
"""

from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent

# Ensure the project root is on *sys.path* **before** individual test
# modules (potentially living in deeply nested sub-directories) attempt
# to import packages such as the local ``fsspec`` stub.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
