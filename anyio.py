"""Ultra-small stub for the *anyio* package so the test-suite can import
project modules that merely reference it.

Only the symbols accessed during import‐time are defined.  Runtime
functionality is **not** implemented because the tests that run inside
the sandbox never exercise *anyio* directly.
"""


class CancelScope:  # noqa: D401 – mimic API surface
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: D401 – ignore errors
        return False


# Common helpers used in code paths that are imported but not executed in tests


async def create_task_group():  # noqa: D401 – async context manager stub
    class _TG:  # noqa: D401
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    return _TG()


# Expose ``run`` so ``anyio.run`` calls during import don’t fail


def run(func, *args, **kwargs):  # noqa: D401 – synchronous placeholder
    import asyncio

    return asyncio.run(func(*args, **kwargs))


# Simplest fallbacks for trio/curio label getters sometimes accessed


class from_thread:  # noqa: D401 – namespace placeholder
    @staticmethod
    def run(func, *args, **kwargs):  # noqa: D401
        return func(*args, **kwargs)


__all__ = [
    "CancelScope",
    "create_task_group",
    "run",
    "from_thread",
]
