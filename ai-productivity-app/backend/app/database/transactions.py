# backend/app/database/transactions.py
"""Utility helpers to run *multi-step* operations inside a single SQLAlchemy
transaction (Hardening checklist 3-A).

The code base uses regular synchronous ``Session`` objects – *not* the new
async variant – therefore ``session.begin()`` is the correct primitive.
"""

from __future__ import annotations

import contextlib
from typing import Iterator

from sqlalchemy.orm import Session


@contextlib.contextmanager
def atomic(session: Session) -> Iterator[Session]:  # noqa: D401 – helper
    """Context manager that commits on success and rolls back on error."""

    tx = session.begin()
    try:
        yield session
        tx.commit()
    except Exception:  # pragma: no cover  # noqa: BLE001 – re-raise caller error
        tx.rollback()
        raise
