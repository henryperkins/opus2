"""Utility helpers for converting between snake_case and camelCase."""

import re


_FIRST_CAP_RE = re.compile("(.)([A-Z][a-z]+)")
_ALL_CAP_RE = re.compile("([a-z0-9])([A-Z])")


def to_camel(string: str) -> str:  # noqa: D401 – simple helper
    """Convert a *snake_case* identifier to *camelCase*.

    Pydantic's ``alias_generator`` expects a **deterministic** mapping from the
    original Python attribute name to the public JSON field.  We therefore keep
    the implementation minimal and free of side-effects (no caching required).
    """
    parts = string.split("_")
    if not parts:
        return string
    return parts[0] + "".join(word.capitalize() or "_" for word in parts[1:])


def to_snake(string: str) -> str:
    """Convert *camelCase* / *PascalCase* names to *snake_case*."""
    s1 = _FIRST_CAP_RE.sub(r"\1_\2", string)
    return _ALL_CAP_RE.sub(r"\1_\2", s1).lower()
