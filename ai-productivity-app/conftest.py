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


    # ------------------------------------------------------------------
    # 1. Ignore duplicate repository snapshot inside *backend/data/uploads*
    # ------------------------------------------------------------------
    if "backend/data/uploads" in p_str:
        return True

    # ------------------------------------------------------------------
    # 2. Skip vendored virtual-env directories to avoid importing heavy
    #    third-party test-suites (e.g. SciPy) that are not relevant for the
    #    project and would pull missing native dependencies.
    # ------------------------------------------------------------------
    if "/backend/venv/" in p_str or "/.venv/" in p_str:
        return True

    # ------------------------------------------------------------------
    # 3. Exclude *tree-sitter* upstream tests that ship with the vendored
    #    grammar sources under ``backend/build/tree-sitter``.  These tests
    #    require the native *tree_sitter* Python bindings which are **not**
    #    available inside the CI sandbox and are unrelated to the
    #    application code under test.
    # ------------------------------------------------------------------
    if "backend/build/tree-sitter" in p_str:
        return True

    return False
