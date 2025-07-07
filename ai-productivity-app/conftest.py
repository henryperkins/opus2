"""Pytest root configuration helpers.

We instruct the test collector to *ignore* the repository mirror located under
``backend/data/uploads`` to prevent *import file mismatch* errors when the same
test module appears in two different paths.  Only the primary copy at the
repository root should be executed.
"""

import pathlib


def pytest_ignore_collect(path, _config):  # noqa: D401
    """Skip duplicate files inside *backend/data/uploads*.

    The upload folder contains an embedded snapshot of the whole repository
    including the test-suite.  When pytest traverses this directory it tries to
    import test modules that have **already** been collected from the top-level
    location which results in *import file mismatch* errors.  Returning *True*
    here tells pytest to ignore anything below that path.
    """

    return "backend/data/uploads" in str(path)
