from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from supabase import AuthApiError

from app.main import app

USER_ID = str(uuid4())


class FakeAuth:
    async def get_user(self, token: str):
        if token != "good-token":
            raise AuthApiError("invalid JWT", 403, "bad_jwt")
        return SimpleNamespace(
            user=SimpleNamespace(id=USER_ID, email="a@driftwood.com")
        )


class FakeTable:
    def __init__(self, calls: list):
        self.calls = calls

    def upsert(self, row, on_conflict):
        self.calls.append((row, on_conflict))
        return self

    async def execute(self):
        return None


class FakeAdmin:
    def __init__(self):
        self.auth = FakeAuth()
        self.upserts: list = []

    def table(self, name: str):
        assert name == "users"
        return FakeTable(self.upserts)


@pytest.fixture
def admin():
    fake = FakeAdmin()
    app.state.supabase_admin = fake
    return fake


@pytest.fixture
def client(admin):
    return TestClient(app)


def test_missing_token_is_401(client):
    assert client.get("/me").status_code == 401


def test_invalid_token_is_401(client):
    r = client.get("/me", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_valid_token_returns_user_and_creates_profile(client, admin):
    r = client.get("/me", headers={"Authorization": "Bearer good-token"})
    assert r.status_code == 200
    assert r.json() == {"id": USER_ID, "email": "a@driftwood.com"}
    assert admin.upserts == [({"id": USER_ID, "email": "a@driftwood.com"}, "id")]


def test_health_needs_no_token(client):
    assert client.get("/health").status_code == 200
