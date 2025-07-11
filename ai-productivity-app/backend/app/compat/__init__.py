"""
CI-sandbox compatibility layer.

Imported **only** when `APP_CI_SANDBOX=1`.  Installs patches and
lightweight stubs so the test-runner works without C-extensions or
forbidden syscalls.
"""

import os

if os.getenv("APP_CI_SANDBOX") != "1":  # pragma: no cover – safety net
    raise ImportError("app.compat loaded outside the sandbox")

from .socket_patch import install_socketpair_patch
from .httpx_patch import install_httpx_patch
from .stubs import install_stubs

# one-shot installation
install_socketpair_patch()
install_httpx_patch()
install_stubs()
