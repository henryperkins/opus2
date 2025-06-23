"""
Starlette ≤ 0.36 passes an 'app' kwarg to httpx≥0.26, which removed it.
This shim drops the arg so TestClient works in the sandbox.
"""
import inspect
import httpx  # type: ignore

def install_httpx_patch() -> None:
    if getattr(httpx, "_patch_applied", False):
        return
    orig_init = httpx.Client.__init__            # type: ignore[attr-defined]
    if "app" not in inspect.signature(orig_init).parameters:
        def _patched(self, *a, **kw):            # type: ignore[no-self-arg]
            kw.pop("app", None)
            return orig_init(self, *a, **kw)
        httpx.Client.__init__ = _patched         # type: ignore[assignment]
    httpx._patch_applied = True                  # type: ignore[attr-defined]
