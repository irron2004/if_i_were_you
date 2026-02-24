from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from sqlmodel import SQLModel

os.environ.setdefault(
    "CANONICAL_BASE_URL",
    "https://webservice-production-c039.up.railway.app",
)
os.environ.setdefault(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,webservice-production-c039.up.railway.app",
)

# Ensure tests run against an isolated, ephemeral database.
# The application reads DATABASE_URL at import time when building SQLAlchemy/SQLModel engines.
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.main import app as fastapi_app
from app.database import Base, engine as orm_engine
from app.core.db import engine as core_engine
from .client import create_client


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """FastAPI 앱 인스턴스를 세션 전역으로 공유."""

    return fastapi_app


@pytest.fixture
def client(app: FastAPI):
    """FastAPI 앱에 대한 동기 HTTP 클라이언트."""

    Base.metadata.drop_all(bind=orm_engine)
    SQLModel.metadata.drop_all(bind=core_engine)
    test_client = create_client(app)
    try:
        yield test_client
    finally:
        test_client.close()


@pytest.fixture
def user_token() -> str:
    return "test-user-token"


@pytest.fixture
def auth_headers(user_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_token}"}
