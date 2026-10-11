"""Tests run against a real Postgres+pgvector (no SQLite): the schema relies on
pgvector, generated tsvector columns and composite FKs."""

import os

import psycopg
import pytest
from psycopg import sql
from sqlalchemy.engine import make_url

TEST_DB_URL = os.environ.get(
    "MC_TEST_DATABASE_URL",
    "postgresql+psycopg://memory:memory@localhost:5433/memory_companion_test",
)
os.environ["MC_DATABASE_URL"] = TEST_DB_URL  # must precede any `app` import

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402


def _ensure_database() -> None:
    url = make_url(TEST_DB_URL)
    with psycopg.connect(
        host=url.host, port=url.port, user=url.username, password=url.password,
        dbname="postgres", autocommit=True,
    ) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (url.database,)
        ).fetchone()
        if not exists:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(url.database)))


@pytest.fixture(scope="session")
def engine():
    _ensure_database()
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    eng = create_engine(TEST_DB_URL)
    yield eng
    eng.dispose()


@pytest.fixture(autouse=True)
def clean_db(engine):
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users CASCADE"))


@pytest.fixture
def client(engine):
    from app.main import app

    with TestClient(app) as c:
        yield c


def register(client: TestClient, email: str, password: str = "correct-horse-battery") -> dict:
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def alice(client):
    return register(client, "alice@example.com")


@pytest.fixture
def bob(client):
    return register(client, "bob@example.com")
