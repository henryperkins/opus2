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
    """Run operations inside a database *transaction* and guarantee atomicity.

    Behaviour details:

    • When the *caller* is **already** inside an open transaction (for example
      when the SQLAlchemy session was implicitly started by previous queries
      executed earlier in the same request) we *do not* open a *second* top-
      level transaction.  SQLAlchemy would raise
      ``InvalidRequestError: A transaction is already begun on this Session``
      in that case (which is exactly what the failing test-suite observed).

      Instead we create a **SAVEPOINT** via :pyfunc:`Session.begin_nested` so
      that our atomic block can still roll back independently without
      interfering with the outer transaction.  No explicit *commit* is
      performed for the nested transaction – leaving control to the outer
      scope.

    • When *no* transaction is active we create the usual top-level
      transaction via :pyfunc:`Session.begin` and commit/roll back
      accordingly.
    """

    # Detect whether the session is already participating in a transaction.
    if session.in_transaction():
        # Nested scope – use SAVEPOINT so that rollback is local to this block
        nested_tx = session.begin_nested()
        try:
            yield session
            # Commit the SAVEPOINT (no-op if outer tx rolls back later)
            nested_tx.commit()
        except Exception:  # pragma: no cover  # noqa: BLE001
            nested_tx.rollback()
            raise
    else:
        # Outermost transaction – full commit / rollback semantics
        tx = session.begin()
        try:
            yield session
            tx.commit()
        except Exception:  # pragma: no cover  # noqa: BLE001
            tx.rollback()
            raise
