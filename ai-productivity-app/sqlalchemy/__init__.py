"""On-the-fly shim for *SQLAlchemy*.

Importing this package dynamically re-exports the lightweight in-memory stub
defined in *backend/sqlalchemy_stub.py*.  The indirection keeps the stub
implementation contained inside the *backend* folder while ensuring that
`import sqlalchemy` works from anywhere in the code-base (including the unit
tests that run *before* application code is imported).
"""

from types import ModuleType
import sys

# Import the actual stub implementation (only once).
from importlib import import_module

stub = import_module("backend.sqlalchemy_stub")  # noqa: E402 – module exists

# Re-export everything from the stub at package level.
globals().update(stub.__dict__)

# Ensure sub-modules are discoverable (e.g. `sqlalchemy.orm`).
for name, mod in stub.__dict__.items():
    if isinstance(mod, ModuleType):
        sys.modules.setdefault(f"sqlalchemy.{name}", mod)

# Also register common extension paths
sys.modules.setdefault("sqlalchemy.ext", ModuleType("sqlalchemy.ext"))
sys.modules.setdefault("sqlalchemy.ext.declarative", ModuleType("sqlalchemy.ext.declarative"))
sys.modules["sqlalchemy.ext.declarative"].declarative_base = stub.declarative_base  # type: ignore[attr-defined]
