"""Minimal stub replacement for the `httpx` library used in the test suite.

This sandbox environment does not have third-party Python packages installed.
The real `httpx` library is only used in the test suite for issuing HTTP
requests against a FastAPI application instance.  For the purposes of the
included tests we can emulate just enough of the public `httpx.Client` API by
delegating to FastAPI's built-in `TestClient` (which relies on `requests`, a
dependency already shipped with FastAPI).

The implementation purposefully limits itself to the small surface area
required by *test_real_options.py* – namely:

    with httpx.Client(app=app, base_url="http://test") as client:
        response = client.request("OPTIONS", "/path")
        response.status_code
        response.headers
        response.content

If additional functionality is needed in the future tests can extend this
shim.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Dict, Mapping


try:
    # FastAPI makes `TestClient` available via its public API which internally
    # wraps `starlette.testclient.TestClient`.
    from fastapi.testclient import TestClient  # type: ignore

except ModuleNotFoundError as exc:  # pragma: no cover – should never happen
    raise ImportError(
        "`fastapi` must be installed for the httpx test shim to operate"
    ) from exc


class _Response:  # pylint: disable=too-few-public-methods
    """Wrapper that provides the subset of the httpx.Response interface used
    by the tests.
    """

    def __init__(self, response):
        self._response = response

    def __getattr__(self, item):
        return getattr(self._response, item)

    # Explicitly expose the three attributes referenced in the tests for type
    # clarity.
    @property
    def status_code(self) -> int:  # noqa: D401 – simple property
        return self._response.status_code

    @property
    def headers(self) -> Mapping[str, str]:  # noqa: D401
        return self._response.headers

    @property
    def content(self) -> bytes:  # noqa: D401
        return self._response.content


class Client(AbstractContextManager):
    """Drop-in stand-in for `httpx.Client` that delegates to FastAPI's
    synchronous TestClient under the hood.
    """

    def __init__(self, *, app=None, base_url: str | None = None, **kwargs: Any):  # noqa: D401, WPS110
        if app is None:
            raise TypeError("The 'app' keyword-argument is required for this stubbed Client")
        # FastAPI's TestClient does not expose a `base_url` argument in older
        # versions that may be present in the execution environment.  The test
        # suite only cares about path-based requests ("/api/..."), so we can
        # safely ignore the provided `base_url`.
        self._client = TestClient(app)

    # ---------------------------------------------------------------------
    # Context management
    # ---------------------------------------------------------------------
    def __enter__(self):  # noqa: D401, WPS110
        self._client.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: D401, WPS110
        return self._client.__exit__(exc_type, exc, tb)

    # ---------------------------------------------------------------------
    # HTTP interface
    # ---------------------------------------------------------------------
    def request(self, method: str, url: str, **kwargs: Any):  # noqa: D401
        """Perform an HTTP request via the underlying TestClient."""

        response = self._client.request(method, url, **kwargs)
        return _Response(response)


# Convenience aliases used by some libraries -----------------------------------

class Response:  # type: ignore
    pass  # The tests never instantiate httpx.Response directly.
