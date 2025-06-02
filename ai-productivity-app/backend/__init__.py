"""Top-level *backend* package.

This file makes the *backend* directory a regular Python package so that
simple statements like ``import backend`` work independent of the current
working directory or a manually adjusted *PYTHONPATH*.

It also registers a lightweight *alias* so that importing ``app.*`` continues
to work when the application is executed from outside the *backend/* folder
(for instance in the production Docker image where the working directory is
``/app``).
"""

from __future__ import annotations

import importlib
import sys

# ---------------------------------------------------------------------------
# Ensure that ``import app.*`` resolves to the implementation that lives under
# ``backend/app`` even when the caller did **not** prepend the *backend/*
# directory to *PYTHONPATH* (which is the case in Docker).
# ---------------------------------------------------------------------------

if "app" not in sys.modules:
    # Import the real package (``backend.app``) first – this guarantees that
    # it is fully initialised before we expose it under the top-level name.
    _app_module = importlib.import_module("backend.app")

    # Register the alias.  From now on both ``import app`` and
    # ``import backend.app`` return the *same* module object.
    sys.modules["app"] = _app_module

    # Because we added a new entry to *sys.modules* we must also make sure that
    # further nested imports (e.g. ``app.main``) work as expected.  The
    # existing sub-modules of ``backend.app`` are already present in
    # *sys.modules* with their fully-qualified names (``backend.app.main``).  We
    # expose *aliases* for the immediate children so that Python's import
    # machinery can find them under the shortened ``app.<sub>`` path as well.
    prefix = "backend.app."
    for fullname, module in list(sys.modules.items()):
        if fullname.startswith(prefix):
            short_name = "app." + fullname[len(prefix) :]
            if short_name not in sys.modules:
                sys.modules[short_name] = module

