"""
Common dependency helpers shared by the ai_config router package.
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_db
from app.services.unified_config_service_async import UnifiedConfigServiceAsync
from app.dependencies import CurrentUserRequired, AdminRequired
from app.models.user import User

# async DB session ---------------------------------------------------------- #
DBSession = Annotated[AsyncSession, Depends(get_async_db)]


# services ------------------------------------------------------------------ #
async def get_config_service(db: DBSession) -> UnifiedConfigServiceAsync:
    """Get the unified config service instance."""
    return UnifiedConfigServiceAsync(db)


# auth wrappers ------------------------------------------------------------- #
CurrentUser = Annotated[User, Depends(CurrentUserRequired)]
CurrentAdmin = Annotated[User, Depends(AdminRequired)]
