from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import async_session_maker

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection helper that yields an async database session
    and guarantees it closes after the API request is complete."""
    async with async_session_maker() as session:
        yield session