from functools import lru_cache
from datetime import datetime
from typing import Dict, Any

from app.database import SessionLocal
from app.services.config_service import ConfigService


@lru_cache(maxsize=1)
def _cached() -> tuple[Dict[str, Any], datetime]:
    """Return cached configuration dictionary plus timestamp."""
    with SessionLocal() as db:
        return ConfigService(db).get_all_config(), datetime.utcnow()


def get_config(max_age: int = 30) -> Dict[str, Any]:
    """Fetch runtime configuration with lightweight LRU caching.

    Args:
        max_age: Maximum cache age in **seconds** before automatic refresh.

    Returns:
        The latest configuration dictionary.
    """
    cfg, ts = _cached()
    if (datetime.utcnow() - ts).seconds > max_age:
        _cached.cache_clear()
        cfg, _ = _cached()  # refresh
    return cfg
