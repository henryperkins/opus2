# Re-export the single authoritative implementation
from app.services.hybrid_search import HybridSearch  # noqa: F401

# ---------------------------------------------------------------------------
# Compatibility shim – expose deprecated module path `app.search.hybrid` so
# existing imports continue to work even though the file has been removed.
# ---------------------------------------------------------------------------

import sys
import types

module_alias = types.ModuleType(__name__ + ".hybrid")
module_alias.HybridSearch = HybridSearch
sys.modules[module_alias.__name__] = module_alias

__all__ = ["HybridSearch"]
