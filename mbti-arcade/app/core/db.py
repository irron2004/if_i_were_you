import os
import sys

from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mbti.db")


def _is_testing() -> bool:
    return os.getenv("TESTING") == "1" or "pytest" in sys.modules


_engine_kwargs: dict[str, object] = {"echo": False, "pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    if _is_testing() and ":memory:" in DATABASE_URL:
        _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session():
    with SessionLocal() as session:
        yield session


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
