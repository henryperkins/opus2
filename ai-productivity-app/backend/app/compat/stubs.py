"""
Pure-python stand-ins for heavy third-party libraries.

Loaded only when ``APP_CI_SANDBOX=1``. All installer functions below
are minimal stubs. Registered as sys.modules only when libs are missing.
"""

import importlib


def _install_fastapi_stub():
    """Register a stubbed FastAPI API surface for test code."""
    import types
    import inspect
    import asyncio
    import sys as _sys
    from typing import Callable, Any

    module = types.ModuleType("fastapi")

    class _Status(int):
        def __getattr__(self, name):
            mapping = {
                "HTTP_200_OK": 200,
                "HTTP_201_CREATED": 201,
                "HTTP_202_ACCEPTED": 202,
                "HTTP_204_NO_CONTENT": 204,
                "HTTP_400_BAD_REQUEST": 400,
                "HTTP_401_UNAUTHORIZED": 401,
                "HTTP_403_FORBIDDEN": 403,
                "HTTP_404_NOT_FOUND": 404,
                "HTTP_409_CONFLICT": 409,
                "HTTP_422_UNPROCESSABLE_ENTITY": 422,
                "HTTP_429_TOO_MANY_REQUESTS": 429,
                "HTTP_500_INTERNAL_SERVER_ERROR": 500,
            }
            return mapping.get(name, 500)

    module.status = _Status()

    class Response:
        """Stub FastAPI Response."""

        def __init__(self):
            self.headers = {}
            self._cookies = {}
            self.status_code = 200

        def set_cookie(self, name, value, **_):
            """Stub set_cookie."""
            self._cookies[name] = value

        @property
        def cookies(self):
            """Return stub cookies."""
            return self._cookies

    module.Response = Response

    class Request:
        """Stub FastAPI Request."""

        def __init__(self):
            self.cookies = {}
            self.headers = {}
            self.client = types.SimpleNamespace(host="testclient")

    module.Request = Request

    class HTTPException(Exception):
        """Stub FastAPI HTTPException with optional headers field."""

        def __init__(self, status_code, detail: str = "", headers: dict | None = None):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail
            self.headers = headers or {}

    module.HTTPException = HTTPException

    def _identity(*_a, **_k):
        """Stub dependency/field identity function."""
        return None

    for _name in ["Body", "Query", "Header", "Path", "Cookie", "Depends", "File"]:
        setattr(module, _name, _identity)

    class UploadFile:
        """Stub FastAPI UploadFile."""

        def __init__(self, filename, content=None):
            self.filename = filename
            self._content = content or b""

        async def read(self):
            """Read content."""
            return self._content

    module.UploadFile = UploadFile

    class BackgroundTasks(list):
        """Stub FastAPI BackgroundTasks."""

        def add_task(self, func: Callable, *args: Any, **kwargs: Any) -> None:
            """Add task to background queue."""
            self.append((func, args, kwargs))

    module.BackgroundTasks = BackgroundTasks

    class WebSocket:
        """Stub FastAPI WebSocket."""

        async def accept(self):
            """Accept the websocket."""
            return None

        async def receive_text(self):
            """Stub receive text."""
            await asyncio.sleep(3600)

        async def send_json(self, _):
            """Stub send JSON."""
            return None

        async def close(self):
            """Stub close."""
            return None

    module.WebSocket = WebSocket

    class WebSocketDisconnect(Exception):
        """Stub FastAPI WebSocketDisconnect."""

    module.WebSocketDisconnect = WebSocketDisconnect

    class _Router:
        """Stub FastAPI APIRouter."""

        def __init__(self, prefix="", **_):
            self.prefix = prefix.rstrip("/")
            self.routes = {}

        def _add(self, method, path, handler, status_code=200):
            self.routes[(method, self.prefix + path)] = (handler, status_code)
            return handler

        # --------------------------------------------------------------
        # FastAPI uses the *on_event* decorator on an *APIRouter* (and the
        # application instance) to register startup/shutdown callbacks like
        # ``@router.on_event("startup")``.  The handler is *not* supposed to
        # be executed immediately – FastAPI just stores the reference.
        #
        # For unit-tests that import the module we simply need to *accept*
        # the decorator and return the original function unchanged so the
        # import machinery can proceed.
        # --------------------------------------------------------------

        def on_event(self, _event_name):  # noqa: D401, WPS110 – keep API
            """No-op decorator for startup/shutdown events."""

            def decorator(fn):
                # Record for introspection if needed by tests
                self.routes[("event", _event_name, fn.__name__)] = (fn, 200)
                return fn

            return decorator

        def get(self, p, **kw):
            """Stub GET route."""
            return lambda fn: self._add("GET", p, fn, kw.get("status_code", 200))

        def post(self, p, **kw):
            """Stub POST route."""
            return lambda fn: self._add("POST", p, fn, kw.get("status_code", 200))

        def put(self, p, **kw):
            """Stub PUT route."""
            return lambda fn: self._add("PUT", p, fn, kw.get("status_code", 200))

        def patch(self, p, **kw):
            """Stub PATCH route."""
            return lambda fn: self._add("PATCH", p, fn, kw.get("status_code", 200))

        def delete(self, p, **kw):
            """Stub DELETE route."""
            return lambda fn: self._add("DELETE", p, fn, kw.get("status_code", 200))

        def websocket(self, p, **_):
            """Stub WebSocket route."""
            return lambda fn: self._add("WS", p, fn)

    module.APIRouter = _Router

    class _FastAPI(_Router):
        """Stub FastAPI main app."""

        def __init__(self, **_):
            super().__init__(prefix="")
            self.middleware = []
            self.state = types.SimpleNamespace()
            self.dependency_overrides = {}

        def add_middleware(self, mw_cls, **kwargs):
            """Stub add_middleware."""
            self.middleware.append((mw_cls, kwargs))

        def include_router(self, router, **_):  # noqa: D401 – ignore extra args
            """Attach *router* routes, silently ignoring FastAPI kwargs."""
            self.routes.update(getattr(router, "routes", {}))

        def add_exception_handler(self, *_):
            """Stub add_exception_handler."""
            return None

    module.FastAPI = _FastAPI

    class _TestClient:
        """Stub FastAPI TestClient."""

        def __init__(self, app):
            self.app = app
            self.cookies = {}

        def _call(self, method, path, **req_kwargs):
            route_info = self.app.routes.get((method, path))
            if isinstance(route_info, tuple):
                handler, default_status = route_info
            else:
                handler, default_status = route_info if route_info else (None, 404)
            if not handler:
                return types.SimpleNamespace(
                    status_code=404,
                    json=lambda: {"detail": "Not Found"},
                    headers={},
                    cookies={},
                )
            body = req_kwargs.get("json", {})
            sig = inspect.signature(handler)
            req_obj = Request()
            resp_obj = Response()
            kwargs = {}
            for name, _param in sig.parameters.items():
                if name in ("payload", "data", "json_body"):
                    param = sig.parameters[name]
                    anno = param.annotation
                    created = None
                    try:
                        from pydantic import BaseModel as _BM

                        if isinstance(anno, type) and issubclass(anno, _BM):
                            created = anno(**body)
                    except (ImportError, TypeError, AttributeError):
                        created = None
                    kwargs[name] = created or body
                elif name == "background_tasks":
                    kwargs[name] = BackgroundTasks()
                elif name in ("current_user", "current_user_required"):
                    kwargs[name] = types.SimpleNamespace(id=1, username="stub")
                elif name == "db":
                    override_dep = None
                    for dep_fn, override_fn in getattr(
                        self.app, "dependency_overrides", {}
                    ).items():
                        if getattr(dep_fn, "__name__", "") == "get_db":
                            override_dep = override_fn
                            break
                    if override_dep is not None:
                        override_gen = override_dep()
                        if hasattr(override_gen, "__next__"):
                            kwargs[name] = next(override_gen)
                        else:
                            kwargs[name] = override_gen
                    else:
                        # If app.database.SessionLocal does not exist,
                        # just give back a dummy.
                        try:
                            from app.database import SessionLocal

                            kwargs[name] = SessionLocal()
                        except ImportError:
                            kwargs[name] = object()
                elif name == "response":
                    kwargs[name] = resp_obj
                elif name == "request":
                    kwargs[name] = req_obj
                else:
                    kwargs[name] = None
            import types as _types

            HTTPException = module.HTTPException  # type: ignore

            try:
                if inspect.iscoroutinefunction(handler):
                    import asyncio as _asyncio

                    response_val = _asyncio.run(handler(**kwargs))
                else:
                    response_val = handler(**kwargs)
            except HTTPException as exc:
                detail_text = exc.detail
                hdrs = exc.headers
                return _types.SimpleNamespace(
                    status_code=exc.status_code,
                    json=lambda: {"detail": detail_text},
                    headers=hdrs,
                    cookies={},
                )
            if isinstance(response_val, tuple):
                payload, status_code = response_val
            elif hasattr(response_val, "dict"):
                try:
                    payload_dict = response_val.dict()
                except AttributeError:
                    payload_dict = response_val.__dict__.copy()
                payload, status_code = payload_dict, default_status
            elif isinstance(response_val, dict):
                payload, status_code = response_val, default_status
            else:
                payload, status_code = {}, 204
            # Use status code from Response object if explicitly set
            if status_code == default_status and resp_obj.status_code != default_status:
                status_code = resp_obj.status_code

            if status_code == 200:
                status_code = default_status

            return types.SimpleNamespace(
                status_code=status_code,
                json=lambda: payload,
                headers=resp_obj.headers,
                cookies=resp_obj.cookies,
            )

        def get(self, p, **kw):
            """Stub GET request."""
            return self._call("GET", p, **kw)

        def post(self, p, **kw):
            """Stub POST request."""
            return self._call("POST", p, **kw)

        def put(self, p, **kw):
            """Stub PUT request."""
            return self._call("PUT", p, **kw)

        def delete(self, p, **kw):
            """Stub DELETE request."""
            return self._call("DELETE", p, **kw)

        def patch(self, p, **kw):
            """Stub PATCH request."""
            return self._call("PATCH", p, **kw)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    testclient_module = types.ModuleType("fastapi.testclient")
    testclient_module.TestClient = _TestClient
    _sys.modules["fastapi.testclient"] = testclient_module
    module.testclient = testclient_module

    middleware_pkg = types.ModuleType("fastapi.middleware")
    cors_submodule = types.ModuleType("fastapi.middleware.cors")

    class CORSMiddleware:
        """Stub CORS middleware."""

        def __init__(self, *_, **__):
            pass

    cors_submodule.CORSMiddleware = CORSMiddleware
    middleware_pkg.cors = cors_submodule
    _sys.modules["fastapi.middleware"] = middleware_pkg
    _sys.modules["fastapi.middleware.cors"] = cors_submodule
    module.middleware = middleware_pkg

    _sys.modules["fastapi"] = module


def _install_pydantic_stub():
    """Register a stubbed Pydantic and pydantic_settings."""
    import types as _types
    import os as _os
    import sys as _sys

    class _BaseModel:
        """Stub Pydantic BaseModel."""

        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def dict(self, *_, **__):
            """Return model as dict."""
            return self.__dict__.copy()

        # FastAPI code-paths and tests frequently rely on the original
        # Pydantic ``from_orm`` helper which builds a model from an arbitrary
        # object exposing attribute access (e.g. SQLAlchemy instance).  The
        # minimal stub implements it by delegating to the plain constructor
        # after converting ``obj.__dict__`` into a regular *dict*.

        @classmethod
        def from_orm(cls, obj):  # noqa: D401 – keep signature minimal
            return cls(**getattr(obj, "__dict__", {}))

        model_dump = dict

        @classmethod
        def model_validate(cls, data, *_, **__):
            """Validate and return a new model instance."""
            if isinstance(data, cls):
                return data
            if isinstance(data, dict):
                return cls(**data)
            raise TypeError("Unsupported")

    _ConfigDict = dict

    def _Field(*_a, default=None, **_k):
        """Stub Pydantic Field."""
        return default

    def _validator(*_f, **_k):
        """Stub Pydantic validator."""

        def dec(fn):
            return fn

        return dec

    class _EmailStr(str):
        """Stub EmailStr."""

    class _BaseSettings(_BaseModel):
        """Stub BaseSettings."""

        def __init__(self, **data):
            merged = {}
            for key in dir(self.__class__):
                if key.startswith("__"):
                    continue
                attr_val = getattr(self.__class__, key)
                if callable(attr_val) or isinstance(attr_val, property):
                    continue
                env_val = _os.getenv(key.upper())
                if env_val is not None:
                    if isinstance(attr_val, bool):
                        merged[key] = env_val.lower() in {"1", "true", "yes", "on"}
                    elif isinstance(attr_val, int) and env_val.isdigit():
                        merged[key] = int(env_val)
                    else:
                        merged[key] = env_val
                else:
                    merged[key] = attr_val
            merged.update(data)
            super().__init__(**merged)

    _pydantic_mod = _types.ModuleType("pydantic")
    _pydantic_mod.BaseModel = _BaseModel
    _pydantic_mod.ConfigDict = _ConfigDict
    _pydantic_mod.Field = _Field
    _pydantic_mod.validator = _validator
    _pydantic_mod.EmailStr = _EmailStr
    _pydantic_mod.NonNegativeInt = int

    def _identity_factory(rt):
        def _factory(*_a, **_k):
            return rt

        return _factory

    _pydantic_mod.confloat = _identity_factory(float)
    _pydantic_mod.conint = _identity_factory(int)
    from typing import List as _List  # local import to avoid top-level dependency

    def _conlist_factory(
        item_type, *, min_length=0, max_length=None
    ):  # noqa: D401 – mimic API
        def _factory(seq: _List[item_type] | None = None):  # type: ignore[var-annotated]
            return seq or []

        return _factory

    _pydantic_mod.conlist = _conlist_factory  # type: ignore[attr-defined]
    _pydantic_mod.field_validator = _validator

    _pydantic_dc = _types.ModuleType("pydantic.dataclasses")
    _pydantic_dc.dataclass = lambda cls=None, **__: cls
    _pydantic_mod.dataclasses = _pydantic_dc

    _pydantic_settings_mod = _types.ModuleType("pydantic_settings")
    _pydantic_settings_mod.BaseSettings = _BaseSettings

    _sys.modules["pydantic"] = _pydantic_mod
    _sys.modules["pydantic.dataclasses"] = _pydantic_dc
    _sys.modules["pydantic_settings"] = _pydantic_settings_mod


def _install_passlib_stub():
    """Register a stubbed passlib CryptContext."""
    import types as _types
    import hashlib as _hashlib
    import sys as _sys

    class CryptContext:
        """Stub for passlib.context.CryptContext."""

        def __init__(self, schemes=("sha256",), **_):
            self.scheme = schemes[0]

        def hash(self, password):
            """Return fake hash."""
            if self.scheme == "bcrypt":
                algo = _hashlib.sha256(password.encode()).hexdigest()
                return f"sha256${algo}"
            return _hashlib.sha256(password.encode()).hexdigest()

        def verify(self, plain_password, hashed_password):
            """Verify password."""
            # The stubbed *hash()* method prefixes the SHA-256 digest with the
            # literal string ``sha256$`` when the *bcrypt* scheme is
            # requested.  To compare two passwords we therefore normalise
            # **both** values by stripping the optional prefix before the
            # constant-time comparison.

            def _normalise(val: str) -> str:
                return val.split("$", 1)[1] if val.startswith("sha256$") else val

            return _normalise(self.hash(plain_password)) == _normalise(hashed_password)

    passlib_mod = _types.ModuleType("passlib")
    context_mod = _types.ModuleType("passlib.context")
    context_mod.CryptContext = CryptContext
    passlib_mod.context = context_mod
    _sys.modules["passlib"] = passlib_mod
    _sys.modules["passlib.context"] = context_mod


def _install_gitpython_stub():
    """Register a stubbed gitpython API."""
    import sys as _sys
    import types as _types

    git_mod = _types.ModuleType("git")

    class _GitCommandError(Exception):
        """Stub git.exc.GitCommandError."""

    exc_mod = _types.ModuleType("git.exc")
    exc_mod.GitCommandError = _GitCommandError

    class _DummyRemote:
        """Stub remote."""

        def fetch(self):
            """Stub fetch method."""
            return []

        def pull(self):
            """Stub pull method."""
            return []

    class _DummyGit:
        """Stub Git commands."""

        def checkout(self, _):
            """Stub checkout method."""
            return None

        def diff(self, *_a, **_k):
            """Stub diff method."""
            return ""

    class _DummyCommit:
        """Stub commit."""

        def __init__(self):
            self.hexsha = "0" * 40
            self.tree = []

    class _DummyActiveBranch:
        name = "main"

    class _Repo:
        """Stub Repo."""

        def __init__(self, *_a, **_k):
            self.remote_obj = _DummyRemote()
            self.git = _DummyGit()
            self.head = _types.SimpleNamespace(commit=_DummyCommit())
            self.active_branch = _DummyActiveBranch()

        def remote(self, *_):
            """Stub remote method."""
            return self.remote_obj

        @staticmethod
        def clone_from(*_a, **_k):
            """Stub clone_from method."""
            return _Repo()

    git_mod.Repo = _Repo
    git_mod.exc = exc_mod
    _sys.modules["git"] = git_mod
    _sys.modules["git.exc"] = exc_mod


def _install_aiofiles_stub():
    """Register a stubbed aiofiles.open."""
    import sys as _sys
    import types as _types
    import asyncio as _asyncio

    aiofiles_mod = _types.ModuleType("aiofiles")

    class _AsyncFile:
        """Stub Async file for aiofiles."""

        def __init__(self, fname, mode, encoding=None):
            self._fp = open(fname, mode, encoding=encoding or "utf-8")

        async def __aenter__(self):
            """Async context manager entry."""
            return self

        async def __aexit__(self, *exc):
            """Async context manager exit."""
            self._fp.close()
            return False

        async def read(self):
            """Async read method."""
            loop = _asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._fp.read)

    def _open(file, mode="r", *, encoding=None):
        return _AsyncFile(file, mode, encoding)

    aiofiles_mod.open = _open
    _sys.modules["aiofiles"] = aiofiles_mod


def _install_numpy_stub():
    """Register a stubbed numpy API."""
    import sys as _sys
    import types as _types
    import math as _math
    import array as _array

    np = _types.ModuleType("numpy")

    class _float32(float):
        pass

    np.float32 = _float32

    class _ndarray(list):
        """Stub numpy ndarray."""

        def astype(self, *_args, **_kwargs):
            """Stub astype method."""
            return self

        def tobytes(self):
            """Stub .tobytes for numpy array."""
            return _array.array("f", self).tobytes()

    np.ndarray = _ndarray

    def _array_func(obj, dtype=None):  # pylint: disable=unused-argument
        """Stub numpy array function."""
        if isinstance(obj, _ndarray):
            return obj
        return _ndarray(obj)

    np.array = _array_func

    def _dot(a, b):
        return sum(x * y for x, y in zip(a, b))

    def _norm(v):
        return _math.sqrt(sum(x * x for x in v))

    np.dot = _dot

    class _LinalgModule(_types.ModuleType):
        """Stub np.linalg module."""

        def __init__(self, name):
            super().__init__(name)
            self.norm = _norm

    # add linalg module registration
    np.linalg = _LinalgModule("numpy.linalg")

    _sys.modules["numpy"] = np


# ---------------------------------------------------------------------------
# Prometheus client stub (Summary & Gauge)
# ---------------------------------------------------------------------------


def _install_prometheus_stub():  # noqa: D401 – mimic external API
    """Provide a minimal *prometheus_client* replacement.

    The real library exposes classes like ``Summary`` and ``Gauge`` whose
    instances are used as decorators (``@Summary.time()``) or chained calls
    (``Gauge.labels(...).inc()``).  The stub implements the same callables as
    no-ops so the business logic can import the package without running the
    heavy runtime.
    """

    import sys as _sys
    import types as _types

    prom_mod = _types.ModuleType("prometheus_client")

    class _Metric:  # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            pass

        def time(self):  # noqa: D401 – decorator
            return lambda fn: fn

        def labels(self, *_, **__):  # noqa: D401 – chainable
            return self

        def inc(self, *_):  # noqa: D401 – no-op
            return None

    prom_mod.Summary = _Metric  # type: ignore
    prom_mod.Gauge = _Metric  # type: ignore

    _sys.modules["prometheus_client"] = prom_mod


# ---------------------------------------------------------------------------
# anyio stub – exposes *only* the parts used by the code base
# ---------------------------------------------------------------------------


def _install_anyio_stub():  # noqa: D401 – mimic tiny subset
    """Install a minimal *anyio* shim.

    Vector store backends rely on ``anyio.to_thread.run_sync`` to delegate
    blocking DB/io tasks to a background thread when *asyncio* is active. The
    complete *anyio* distribution is hefty and often unavailable in the
    constrained execution sandbox running the test-suite.  Instead of adding
    the heavyweight dependency we register a lightweight fake that provides
    exactly the symbols accessed by the backend:

    • ``anyio.to_thread.run_sync(func, *args, **kwargs)`` – executes *func*
      synchronously (test environment does not require real thread offloading).
    • ``anyio.sleep(delay)`` – async no-op placeholder so callers can
      ``await anyio.sleep`` without errors.
    • ``anyio.run(func, *args, **kwargs)`` – simple pass-through helper used by
      some external libraries.
    """

    import sys as _sys
    import types as _types

    anyio_mod = _types.ModuleType("anyio")

    # async helpers ------------------------------------------------------ #

    async def _run_sync(func, /, *args, **kwargs):  # noqa: D401
        return func(*args, **kwargs)

    anyio_mod.to_thread = _types.SimpleNamespace(run_sync=_run_sync)

    async def _sleep(_):  # noqa: D401 – do nothing
        return None

    anyio_mod.sleep = _sleep  # type: ignore[attr-defined]

    def _run(func, *args, **kwargs):  # noqa: D401 – sync wrapper
        return func(*args, **kwargs)

    anyio_mod.run = _run  # type: ignore[attr-defined]

    _sys.modules["anyio"] = anyio_mod


# ---------------------------------------------------------------------------
# Tenacity stub – provides retry decorators used in the code base
# ---------------------------------------------------------------------------


def _install_tenacity_stub():  # noqa: D401 – mimic API
    """Register a *tenacity* replacement with no-op decorators."""

    import sys as _sys
    import types as _types

    t_module = _types.ModuleType("tenacity")

    def _retry(*dargs, **_dkwargs):  # noqa: D401
        """Return decorator that executes the function without retry."""

        def decorator(fn):
            return fn

        # Support both @retry and @retry(...) syntaxes
        if dargs and callable(dargs[0]):
            return decorator(dargs[0])
        return decorator

    t_module.retry = _retry

    def _identity(x):  # noqa: D401
        return x

    # Common helpers used in the code
    t_module.stop_after_attempt = lambda *_a, **_kw: None  # type: ignore
    t_module.wait_exponential = lambda *_a, **_kw: None  # type: ignore
    t_module.retry_if_exception_type = _identity  # type: ignore
    t_module.before_sleep_log = lambda *_a, **_kw: None  # type: ignore
    t_module.retry_if_exception = _identity  # type: ignore

    class RetryError(Exception):
        pass

    t_module.RetryError = RetryError

    _sys.modules["tenacity"] = t_module


# ---------------------------------------------------------------------------
# Jedi stub – static analysis placeholder
# ---------------------------------------------------------------------------


def _install_jedi_stub():  # noqa: D401 – minimal API for usage_searcher
    """Provide a lightweight stub for the *jedi* static analysis library.

    The backend's *UsageSearcher* relies on:

    • ``jedi.Project(path=...)`` – constructor, no behaviour needed.
    • ``jedi.Script(code, path, project)`` – constructor with method
      ``get_references`` returning an *iterable* of reference objects that
      expose attributes ``line``, ``column``, ``module_path``, ``name`` and a
      method ``get_line_code()``.

    Unit-tests never inspect the actual static analysis result. Returning an
    *empty list* is therefore sufficient as long as the call chain does not
    raise *AttributeError*.
    """

    import sys as _sys
    import types as _types

    jedi_mod = _types.ModuleType("jedi")

    class _Project:  # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            pass

    class _Reference:  # pylint: disable=too-few-public-methods
        def __init__(self):
            self.line = 0
            self.column = 0
            self.module_path = ""
            self.name = ""

        # Same method signature as real jedi Reference
        def get_line_code(self):  # noqa: D401
            return ""

    class _Script:  # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            pass

        def get_references(self, *_, **__):  # noqa: D401
            return []

    jedi_mod.Project = _Project
    jedi_mod.Script = _Script

    _sys.modules["jedi"] = jedi_mod


# ---------------------------------------------------------------------------
# pgvector stub – provides SQLAlchemy "Vector" type placeholder
# ---------------------------------------------------------------------------


def _install_pgvector_stub():  # noqa: D401 – minimal implementation
    """Register a minimal *pgvector* shim so imports succeed in the sandbox.

    Only the *Vector* type from ``pgvector.sqlalchemy`` is required by the
    backend. We therefore expose a tiny class with the same public name and
    register it under the expected module paths.  No vector operations are
    executed in the unit-tests so behaviour can be a no-op.
    """

    import sys as _sys
    import types as _types

    # Parent package module
    pgvector_mod = _types.ModuleType("pgvector")

    # Sub-module for SQLAlchemy integration
    sa_mod = _types.ModuleType("pgvector.sqlalchemy")

    class Vector:  # pylint: disable=too-few-public-methods
        """Stub SQLAlchemy column type."""

        cache_ok = True  # Compatibility attribute

        def __init__(self, _dim: int | None = None):  # noqa: D401 – mimic API
            self.dim = _dim

        def compile(self, dialect=None):  # noqa: D401 – mimic SQL compilation
            return "VECTOR"

    # Attach to sub-module
    sa_mod.Vector = Vector

    # Register both modules
    pgvector_mod.sqlalchemy = sa_mod
    _sys.modules["pgvector"] = pgvector_mod
    _sys.modules["pgvector.sqlalchemy"] = sa_mod


# ---------------------------------------------------------------------------
# Qdrant stub
# ---------------------------------------------------------------------------


def _install_qdrant_stub():
    """Register a dummy *qdrant_client* module with the minimal surface.

    The backend uses only *QdrantClient* and the *models* sub-module with a
    handful of attribute-like enums / classes.  We replicate just enough so
    that ``import qdrant_client`` succeeds and type-checks evaluating
    ``qdrant_client.models.Distance.COSINE`` do not crash.
    """

    import sys as _sys
    import types as _types

    qdrant_mod = _types.ModuleType("qdrant_client")

    class _FakeClient:  # pylint: disable=too-few-public-methods
        def __init__(self, *_, **__):
            pass

        # Public methods accessed by the wrapper. They all return trivial
        # placeholders so the higher level code can still inspect the
        # response structure without crashing.

        def get_collections(self):  # noqa: D401 – signature parity
            return _types.SimpleNamespace(collections=[])

        def create_collection(self, *_, **__):
            return None

        def upsert(self, *_, **__):
            return _types.SimpleNamespace(status="COMPLETED")

        def delete(self, *_, **__):
            return None

        def search(self, *_, **__):
            return []

        def get_collection(self, *_):
            return _types.SimpleNamespace(points_count=0)

    qdrant_mod.QdrantClient = _FakeClient

    # models sub-module with Distance enum and minimal PointStruct etc.
    models_mod = _types.ModuleType("qdrant_client.models")

    class _Distance:  # pylint: disable=too-few-public-methods
        COSINE = "cosine"

    models_mod.Distance = _Distance

    class _PointStruct(dict):  # pragma: no cover – placeholder only
        def __init__(self, **kw):  # noqa: D401 – mimic attrs
            super().__init__(**kw)

    models_mod.PointStruct = _PointStruct

    class _FieldCondition(dict):
        def __init__(self, **kw):
            super().__init__(**kw)

    models_mod.FieldCondition = _FieldCondition

    class _MatchAny(dict):
        def __init__(self, **kw):
            super().__init__(**kw)

    models_mod.MatchAny = _MatchAny

    class _MatchValue(dict):
        def __init__(self, **kw):
            super().__init__(**kw)

    models_mod.MatchValue = _MatchValue

    class _Filter(dict):
        def __init__(self, **kw):
            super().__init__(**kw)

    models_mod.Filter = _Filter

    class _VectorParams(dict):
        def __init__(self, **kw):
            super().__init__(**kw)

    models_mod.VectorParams = _VectorParams

    class _HnswConfigDiff(dict):
        def __init__(self, **kw):
            super().__init__(**kw)

    models_mod.HnswConfigDiff = _HnswConfigDiff

    class _UpdateStatus:  # pylint: disable=too-few-public-methods
        COMPLETED = "COMPLETED"

    models_mod.UpdateStatus = _UpdateStatus

    qdrant_mod.models = models_mod

    _sys.modules["qdrant_client"] = qdrant_mod
    _sys.modules["qdrant_client.models"] = models_mod


# ---------------------------------------------------------------------------
# tiktoken stub – naive tokenizer replacement
# ---------------------------------------------------------------------------


def _install_tiktoken_stub():  # noqa: D401 – simple char-based encoder
    """Register a lightweight *tiktoken* stub.

    The real *tiktoken* package is a compiled extension unavailable in the
    sandbox.  For the purpose of the unit-tests we only need *approximate*
    token counts – character count is good enough.  The backend uses:

    • ``tiktoken.get_encoding(name)``
    • ``tiktoken.encoding_for_model(model)``
    • tokeniser object's ``encode(text, disallowed_special=())`` returning
      ``List[int]`` with length equal to the token count.
    """

    import sys as _sys
    import types as _types

    t_mod = _types.ModuleType("tiktoken")

    class _FakeEncoding:  # pylint: disable=too-few-public-methods
        def encode(self, txt, *_, **__):  # noqa: D401 – mimic API
            # Very rough approximation: 1 char = 1 token
            return list(range(len(txt)))

    # Simple registry of encodings by name
    _ENCODINGS = {}

    def _get_encoding(name):  # noqa: D401 – mimic tiktoken API
        if name not in _ENCODINGS:
            _ENCODINGS[name] = _FakeEncoding()
        return _ENCODINGS[name]

    def _encoding_for_model(_model):  # noqa: D401
        return _get_encoding("default")

    t_mod.get_encoding = _get_encoding  # type: ignore[attr-defined]
    t_mod.encoding_for_model = _encoding_for_model  # type: ignore[attr-defined]

    _sys.modules["tiktoken"] = t_mod


def _install_openai_stub():
    """Register a stubbed openai API."""
    import sys as _sys
    import types as _types

    openai_mod = _types.ModuleType("openai")

    # ------------------------------------------------------------------
    # Exception hierarchy – we only add the symbols referenced by the code
    # base.  All stub classes inherit directly from *Exception* and carry no
    # additional logic.  They exist purely so that ``from openai import
    # AuthenticationError`` etc. succeeds when the real SDK is absent.
    # ------------------------------------------------------------------

    class AuthenticationError(Exception):
        """Stub AuthenticationError."""

    class RateLimitError(Exception):
        """Stub RateLimitError."""

    class BadRequestError(Exception):
        """Stub BadRequestError."""

    class APITimeoutError(Exception):
        """Stub APITimeoutError."""

    class APIConnectionError(Exception):
        """Stub APIConnectionError."""

    class InternalServerError(Exception):
        """Stub InternalServerError."""

    class _EmptyStream:
        """Stub streaming async object."""

        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class _FakeEmbedding:
        embedding = []

    class _FakeEmbeddingsResp:
        def __init__(self):
            self.data = [_FakeEmbedding()]

    class _BaseClient:
        class _ChatMgr:
            class _Completions:
                async def create(self, *, stream=False, **_):
                    if stream:
                        return _EmptyStream()
                    return _types.SimpleNamespace(choices=[])

            completions = _Completions()

        class _Responses:
            async def create(self, *, stream=False, **_):
                """Stub create method for responses."""
                if stream:
                    return _EmptyStream()
                return _types.SimpleNamespace(output_text="")

        class _Embeddings:
            async def create(self, **_):
                """Stub create method for embeddings."""
                return _FakeEmbeddingsResp()

        def __init__(self, *_, **__):
            self.chat = self._ChatMgr()
            self.responses = self._Responses()
            self.embeddings = self._Embeddings()

    # client classes – same structure as before
    openai_mod.AsyncOpenAI = _BaseClient
    openai_mod.AsyncAzureOpenAI = _BaseClient
    error_mod = _types.ModuleType("openai.error")
    # expose identical symbols under the nested module path that the real SDK
    # uses so that ``import openai.error as err`` keeps working.
    for _name, _cls in {
        "AuthenticationError": AuthenticationError,
        "RateLimitError": RateLimitError,
        "BadRequestError": BadRequestError,
        "APITimeoutError": APITimeoutError,
        "APIConnectionError": APIConnectionError,
        "InternalServerError": InternalServerError,
    }.items():
        setattr(error_mod, _name, _cls)
        setattr(openai_mod, _name, _cls)
    openai_mod.error = error_mod
    _sys.modules["openai"] = openai_mod
    _sys.modules["openai.error"] = error_mod


def install_stubs():
    """Master installer: patch sys.modules with stubs if not present."""
    installers = [
        ("fastapi", _install_fastapi_stub),
        ("pydantic", _install_pydantic_stub),
        ("pydantic_settings", _install_pydantic_stub),
        # The backend imports *openai* unconditionally via ``app.llm.client``.
        # When the real SDK is not available inside the sandbox we fall back
        # to a lightweight stub that exposes the minimal public surface area
        # required by the surrounding code-base (AsyncOpenAI, errors, etc.).
        #
        # Failing to register the stub caused **ModuleNotFoundError: openai**
        # during test collection which in turn prevented the application from
        # bootstrapping and broke seemingly unrelated features such as the
        # *login* and *register* endpoints.  Adding the entry here ensures the
        # stub is installed automatically whenever the genuine package is
        # missing so that the rest of the code can import ``openai`` without
        # errors.
        ("openai", _install_openai_stub),
        ("passlib.context", _install_passlib_stub),
        ("git", _install_gitpython_stub),
        ("aiofiles", _install_aiofiles_stub),
        ("numpy", _install_numpy_stub),
        ("prometheus_client", _install_prometheus_stub),
        ("tenacity", _install_tenacity_stub),
        # pgvector stub to satisfy PostgresVectorService imports
        ("pgvector", _install_pgvector_stub),
        ("jedi", _install_jedi_stub),
        ("tiktoken", _install_tiktoken_stub),
        # ``anyio`` is a heavy-weight async framework rarely available in the
        # restricted execution sandbox.  A **tiny** shim that only exposes the
        # subset needed by the vector services (``to_thread.run_sync``) is
        # sufficient for unit-tests and avoids *ModuleNotFoundError* during
        # import time.
        ("anyio", _install_anyio_stub),
        # Qdrant client is imported by the vector store service layer. Provide
        # a minimal stub so that test collection does not bail out early when
        # the binary wheels are unavailable in the sandbox.
        ("qdrant_client", _install_qdrant_stub),
    ]
    for pkg, fn in installers:
        try:
            importlib.import_module(pkg)
        except ModuleNotFoundError:
            fn()
