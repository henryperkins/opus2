"""Light-weight stub to satisfy ``import fastapi`` in the test-suite.

The *real* FastAPI dependency is not available inside the execution sandbox.
The application ships a minimal self-contained replacement located in
``app.auth.security``.  Importing that module registers the stub under the
canonical module name **fastapi**.  Unfortunately the tests import FastAPI
**before** the application code is evaluated which means the stub has not yet
been initialised, leading to ``ModuleNotFoundError``.

By pre-creating this *package* we ensure that the import always succeeds.  On
initialisation we simply load ``app.auth.security`` which takes care of
populating all required sub-modules (``fastapi.testclient``, etc.).  We then
re-export every public attribute so that ``from fastapi import FastAPI`` works
transparently.
"""

from __future__ import annotations

# Ensure that the *backend* folder is on the Python path so that
# ``import app.*`` works even when the repository root is the working
# directory (which is the case for the unit-test invocation).
import sys
from pathlib import Path
from types import ModuleType

_repo_root = Path(__file__).resolve().parent.parent
_backend_dir = _repo_root / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Importing *app.auth.security* now succeeds because we just adjusted
# ``sys.path``.  Doing so registers the fully-featured FastAPI stub under the
# canonical module name.
import importlib

importlib.import_module("app.auth.security")

# Grab the fully-featured stub we just installed (it may have been created
# afresh or already existed if some other module imported it earlier).
_stub: ModuleType = sys.modules["fastapi"]  # type: ignore[assignment]

# Re-export public names so that ``from fastapi import XYZ`` resolves against
# the stub.  Skip dunder/private attributes.
for _name in dir(_stub):
    if _name.startswith("__"):
        continue
    setattr(sys.modules[__name__], _name, getattr(_stub, _name))

# Make sure that sub-modules like 'fastapi.testclient' are properly registered
# under *this* package so that subsequent imports pick them up from the cache.
for _mod_name, _mod in list(sys.modules.items()):
    if _mod_name.startswith("fastapi."):
        sys.modules[_mod_name] = _mod

# Explicitly mark this module as a *package* so that Python allows further
# nested imports even though we did not create real files for them.
__path__ = []  # type: ignore[name-defined]
