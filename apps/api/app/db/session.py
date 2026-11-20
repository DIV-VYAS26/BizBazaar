from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine():
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_timeout=5,
        connect_args={
            "connect_timeout": 5,
            "options": "-c lock_timeout=5000 -c statement_timeout=15000",
        },
    )


def get_db():
    # Synchronous routes run in FastAPI's thread pool; no blocking DB in async handlers.
    with sessionmaker(get_engine(), expire_on_commit=False)() as session:
        yield session
