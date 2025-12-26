"""
SQLAlchemy custom types for cross-dialect compatibility.

This repo uses Postgres in production (UUID + pgvector), but tests often run on SQLite.
These type helpers keep the ORM models importable and allow `Base.metadata.create_all()`
to work under SQLite without requiring a running Postgres instance.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """
    Platform-independent GUID/UUID type.

    - Postgres: native UUID (returns/accepts `uuid.UUID`)
    - Other DBs (e.g. SQLite): stores as CHAR(36), returns `uuid.UUID`
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect):
        if value is None:
            return None

        # Normalize to UUID
        if isinstance(value, uuid.UUID):
            u = value
        elif isinstance(value, str):
            u = uuid.UUID(value)
        else:
            raise ValueError(f"Invalid UUID value: {value!r}")

        # For Postgres we pass UUID objects through (as_uuid=True)
        if dialect.name == "postgresql":
            return u

        # For SQLite and others, store string form
        return str(u)

    def process_result_value(self, value: Any, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


