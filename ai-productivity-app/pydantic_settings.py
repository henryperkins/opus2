"""Very small stub replicating the public API used by the codebase.

Only the *BaseSettings* class is required.  The real implementation provided
by *pydantic-settings* loads environment variables and performs validation.
For the purposes of the unit-tests we can get away with a trivial subclass of
``dict`` that copies attributes defined on the subclass itself.
"""

from __future__ import annotations


class BaseSettings:  # noqa: D401 – placeholder implementation
    def __init__(self, **values):  # noqa: D401
        # Copy class attributes to instance dict first (defaults)
        for name in dir(self.__class__):
            if name.startswith("__"):
                continue
            attr = getattr(self.__class__, name)
            if callable(attr) or isinstance(attr, property):
                continue
            setattr(self, name, attr)

        # Override with explicit constructor values (mirrors pydantic)
        for key, val in values.items():
            setattr(self, key, val)

    def dict(self):  # noqa: D401 – helper mirroring pydantic API
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


# Nothing else from the real library is required by the application/tests.
