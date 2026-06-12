from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False, # true if need sql queries in console
    future=True
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False # this is kept false, as python marks the state as expired and anything accessed after commit would trigger
                           # an implicit query(async cannot run implicit query call in the background, which might crash the program with an exception
)

class Base(DeclarativeBase):
    pass