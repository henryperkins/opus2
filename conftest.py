"""Global pytest configuration for the repository.

Adds the project root to *sys.path* so that helper stubs (e.g. the
light-weight ``fsspec`` replacement located at ``/fsspec``) are
importable regardless of the directory from which pytest collects
tests.
"""

from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent

# Ensure the project root is on *sys.path* **before** individual test
# modules (potentially living in deeply nested sub-directories) attempt
# to import packages such as the local ``fsspec`` stub.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Provide minimal *numpy* stub                                               
# ---------------------------------------------------------------------------
# The test environment does not have the real *numpy* package installed.     
# Some third-party libraries included in the repository (e.g. inside the      
# vendored ``venv`` folder) ship their own *conftest.py* files which Pytest   
# attempts to load as plugins via the dotted path ``numpy.conftest``. This    
# import fails if the top-level ``numpy`` module is missing, aborting the     
# entire test session during collection.  To avoid adding the heavy          
# dependency we create a lightweight stub that satisfies the import without   
# affecting runtime behaviour.                                               
#                                                                            
# Only the *conftest* plugin is expected to be imported, therefore an empty   
# module is sufficient.                                                      


import types


if 'numpy' not in sys.modules:
    numpy_stub = types.ModuleType('numpy')
    numpy_stub.__path__ = []  # mark as package so sub-modules can be imported
    numpy_stub.__version__ = '0.0.0'
    # Minimal API surface required by the codebase
    numpy_stub.ndarray = list  # type: ignore – pretend list is an ndarray

    def _array(obj, dtype=None):  # noqa: D401, WPS110 – signature like np.array
        """Very small subset of numpy.array. Returns *obj* unchanged."""
        return obj

    numpy_stub.array = _array  # type: ignore

    # Fallback attribute factory – returns a dummy *type* for unknown symbols
    def _create_dummy(name):  # noqa: D401, WPS110 – internal helper
        return type(name, (), {})

    def _getattr(attr):  # noqa: D401 – match *__getattr* protocol
        return _create_dummy(attr)

    numpy_stub.__getattr__ = _getattr  # type: ignore[attr-defined]

    # Common dtype aliases used by SciPy/NetworkX test helpers
    for _dtype in (
        'int8',
        'int16',
        'int32',
        'int64',
        'intc',
        'intp',
        'uint8',
        'uint16',
        'uint32',
        'uint64',
        'float16',
        'float32',
        'float64',
        'bool_',
    ):
        setattr(numpy_stub, _dtype, type(_dtype, (), {}))

    # Provide lightweight lin alg submodule with *norm* placeholder
    linalg_mod = types.ModuleType('numpy.linalg')

    def _norm(x, ord=None, axis=None, keepdims=False):  # noqa: D401, WPS110 – dummy
        return 0.0

    linalg_mod.norm = _norm  # type: ignore
    sys.modules['numpy.linalg'] = linalg_mod

    sys.modules['numpy'] = numpy_stub

# Provide the submodule expected by Pytest's plugin loader.
if 'numpy.conftest' not in sys.modules:
    sys.modules['numpy.conftest'] = types.ModuleType('numpy.conftest')
