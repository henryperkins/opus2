"""Delegate *backend* shadow package to the canonical FastAPI stub.

When the working directory is ``backend/`` the interpreter discovers the empty
``backend/fastapi`` directory *before* it can reach the fully-featured stub at
project root.  An empty directory without ``__init__.py`` is treated as a
*namespace package* (PEP 420) which lacks all the attributes that the
application and test-suite expect.

To avoid import order pitfalls we turn the namespace package into a regular
module that immediately initialises the canonical stub contained in
``../fastapi`` and then re-exports every public symbol.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

# ---------------------------------------------------------------------------
# 1.  Ensure the project root is on *sys.path* so that we can reach the actual
#     stub implementation and the rest of the application (``import app.*``).
# ---------------------------------------------------------------------------

_backend_dir = Path(__file__).resolve().parent  # …/backend/fastapi
_repo_root = _backend_dir.parent.parent         # project root

if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# ---------------------------------------------------------------------------
# 2.  Import the canonical stub (this sets up ``fastapi.testclient`` & friends)
# ---------------------------------------------------------------------------

# Importing *app.auth.security* attaches the minimal FastAPI replacement to
# the **already existing** module object (this file) and registers helpful
# sub-modules such as ``fastapi.testclient``.

import app.auth.security  # noqa: F401  – side-effects only

# After the import the current module instance (*backend.fastapi*) contains
# all the public symbols.  We still expose the module via the canonical name
# so that identity comparisons (`sys.modules['fastapi'] is sys.modules['backend.fastapi']`)
# hold true.

stub = sys.modules.setdefault("fastapi", sys.modules[__name__])

# ---------------------------------------------------------------------------
# 3.  Re-export public names so that ``from fastapi import X`` works
# ---------------------------------------------------------------------------

current: ModuleType = sys.modules[__name__]

for _name in dir(stub):
    if _name.startswith("__"):
        continue
    setattr(current, _name, getattr(stub, _name))

# ---------------------------------------------------------------------------
# 4.  Mirror sub-modules under the *backend.fastapi* namespace to avoid module
#     duplication (important for identity checks like ``is`` in the tests).
# ---------------------------------------------------------------------------

prefix = f"{__name__}."

for _mod_name, _mod in list(sys.modules.items()):
    if _mod_name.startswith("fastapi.") and not _mod_name.startswith(prefix):
        sys.modules[prefix + _mod_name.split(".", 1)[1]] = _mod
