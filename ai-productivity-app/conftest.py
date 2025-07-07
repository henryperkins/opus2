"""Pytest root configuration helpers.

We instruct the test collector to *ignore* the repository mirror located under
``backend/data/uploads`` to prevent *import file mismatch* errors when the same
test module appears in two different paths.  Only the primary copy at the
repository root should be executed.
"""

import pathlib


# NOTE: The hook signature changed in pytest ≥8 where the second parameter was
# renamed from ``_config`` to ``config``.  Using the outdated name leads to a
# PluginValidationError during test collection.  Accept both names by keeping
# the parameter but aligning with the new spec – pytest will still pass the
# argument positionally, so this change remains backward-compatible with older
# versions.


def pytest_ignore_collect(path, config):  # noqa: D401
    """Skip duplicate files inside *backend/data/uploads*.

    The upload folder contains an embedded snapshot of the whole repository
    including the test-suite.  When pytest traverses this directory it tries to
    import test modules that have **already** been collected from the top-level
    location which results in *import file mismatch* errors.  Returning *True*
    here tells pytest to ignore anything below that path.
    """

    p_str = str(path)

    # Ignore duplicate repository snapshot as well as vendored virtual envs
    if "backend/data/uploads" in p_str:
        return True

    # Skip bundled *venv* directories to avoid importing third-party test
    # suites (e.g. SciPy, NetworkX) which pull heavy native dependencies like
    # NumPy that are not present in the sandbox.
    if "/backend/venv/" in p_str or "/.venv/" in p_str:
        return True

    return False
