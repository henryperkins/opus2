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

    for _name in [
        "Body",
        "Query",
        "Header",
        "Path",
        "Cookie",
        "Depends",
        "File"
    ]:
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

        def _add(self, method, path, handler):
            self.routes[(method, self.prefix + path)] = handler
            return handler

        def get(self, p, **_):
            """Stub GET route."""
            return lambda fn: self._add("GET", p, fn)

        def post(self, p, **_):
            """Stub POST route."""
            return lambda fn: self._add("POST", p, fn)

        def put(self, p, **_):
            """Stub PUT route."""
            return lambda fn: self._add("PUT", p, fn)

        def patch(self, p, **_):
            """Stub PATCH route."""
            return lambda fn: self._add("PATCH", p, fn)

        def delete(self, p, **_):
            """Stub DELETE route."""
            return lambda fn: self._add("DELETE", p, fn)

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

        def include_router(self, router):
            """Stub include_router."""
            self.routes.update(router.routes)

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
            handler = self.app.routes.get((method, path))
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
                    kwargs[name] = types.SimpleNamespace(
                        id=1, username="stub"
                    )
                elif name == "db":
                    override_dep = None
                    for dep_fn, override_fn in (
                        getattr(self.app, "dependency_overrides", {}).items()
                    ):
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
            if inspect.iscoroutinefunction(handler):
                import asyncio as _asyncio
                response_val = _asyncio.run(handler(**kwargs))
            else:
                response_val = handler(**kwargs)
            if isinstance(response_val, tuple):
                payload, status_code = response_val
            elif hasattr(response_val, "dict"):
                payload, status_code = response_val.dict(), 200
            elif isinstance(response_val, dict):
                payload, status_code = response_val, 200
            else:
                payload, status_code = {}, 204
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
                        merged[key] = env_val.lower() in {
                            "1", "true", "yes", "on"
                        }
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
            if hashed_password.startswith("sha256$"):
                hashed_password = hashed_password.split("$", 1)[1]
            return self.hash(plain_password) == hashed_password

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

    np.linalg = _LinalgModule("numpy.linalg")

    _sys.modules["numpy"] = np


def _install_openai_stub():
    """Register a stubbed openai API."""
    import sys as _sys
    import types as _types

    openai_mod = _types.ModuleType("openai")

    class RateLimitError(Exception):
        """Stub RateLimitError."""

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

    openai_mod.AsyncOpenAI = _BaseClient
    openai_mod.AsyncAzureOpenAI = _BaseClient
    error_mod = _types.ModuleType("openai.error")
    error_mod.RateLimitError = RateLimitError
    openai_mod.RateLimitError = RateLimitError
    openai_mod.error = error_mod
    _sys.modules["openai"] = openai_mod
    _sys.modules["openai.error"] = error_mod


def install_stubs():
    """Master installer: patch sys.modules with stubs if not present."""
    installers = [
        ("fastapi", _install_fastapi_stub),
        ("pydantic", _install_pydantic_stub),
        ("pydantic_settings", _install_pydantic_stub),
        ("passlib.context", _install_passlib_stub),
        ("git", _install_gitpython_stub),
        ("aiofiles", _install_aiofiles_stub),
        ("numpy", _install_numpy_stub),
        ("openai", _install_openai_stub),
    ]
    for pkg, fn in installers:
        try:
            importlib.import_module(pkg)
        except ModuleNotFoundError:
            fn()
