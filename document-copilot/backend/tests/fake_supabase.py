"""A tiny in-memory stand-in for the Supabase client, enough for the chat tables."""

from types import SimpleNamespace
from uuid import uuid4


class FakeQuery:
    def __init__(self, db: "FakeAdmin", table: str):
        self.db, self.table = db, table
        self.rows = db.tables.setdefault(table, [])
        self.filters: list[tuple[str, str]] = []
        self.sort: tuple[str, bool] | None = None
        self.max: int | None = None
        self.action = "select"
        self.payload = None

    def select(self, _columns="*"):
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def in_(self, column, values):
        self.filters.append((column, set(values)))
        return self

    def delete(self):
        self.action = "delete"
        return self

    def order(self, column, desc=False):
        self.sort = (column, desc)
        return self

    def limit(self, n):
        self.max = n
        return self

    def insert(self, payload):
        self.action, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.action, self.payload = "update", payload
        return self

    def upsert(self, payload, on_conflict):
        self.action, self.payload, self.key = "upsert", payload, on_conflict
        return self

    def _matching(self):
        return [
            r
            for r in self.rows
            if all(
                r.get(c) in v if isinstance(v, set) else r.get(c) == v
                for c, v in self.filters
            )
        ]

    async def execute(self):
        if self.table in self.db.fail_inserts_into and self.action == "insert":
            raise RuntimeError("database is down")
        if self.action == "insert":
            items = self.payload if isinstance(self.payload, list) else [self.payload]
            stamped = []
            for item in items:
                row = {
                    "id": str(uuid4()),
                    "title": None,
                    "created_at": f"2026-01-01T00:00:{len(self.rows) + 1:02d}+00:00",
                    "updated_at": f"2026-01-01T00:00:{len(self.rows) + 1:02d}+00:00",
                    **item,
                }
                self.rows.append(row)
                stamped.append(row)
            return SimpleNamespace(data=stamped)
        if self.action == "delete":
            gone = self._matching()
            self.rows[:] = [r for r in self.rows if r not in gone]
            return SimpleNamespace(data=gone)
        if self.action == "update":
            for row in self._matching():
                row.update(self.payload)
            return SimpleNamespace(data=self._matching())
        if self.action == "upsert":
            existing = next(
                (r for r in self.rows if r[self.key] == self.payload[self.key]), None
            )
            if existing:
                existing.update(self.payload)
            else:
                self.rows.append(dict(self.payload))
            return SimpleNamespace(data=[self.payload])
        data = self._matching()
        if self.sort:
            column, desc = self.sort
            data = sorted(data, key=lambda r: r[column], reverse=desc)
        return SimpleNamespace(data=data[: self.max] if self.max else data)


class FakeAdmin:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {}
        self.fail_inserts_into: set[str] = set()
        self.auth = SimpleNamespace(get_user=self._get_user)
        self.tokens: dict[str, SimpleNamespace] = {}

    def add_user(self, token: str, user_id: str, email: str):
        self.tokens[token] = SimpleNamespace(
            user=SimpleNamespace(id=user_id, email=email)
        )

    async def _get_user(self, token: str):
        from supabase import AuthApiError

        if token not in self.tokens:
            raise AuthApiError("invalid JWT", 403, "bad_jwt")
        return self.tokens[token]

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self, name)
