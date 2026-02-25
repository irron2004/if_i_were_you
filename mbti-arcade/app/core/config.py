from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from uuid import uuid4

DEFAULT_EXPIRES_HOURS = 72
REQUEST_ID_HEADER = "X-Request-ID"


def generate_session_id() -> str:
    return str(uuid4())


def generate_invite_token() -> str:
    return uuid4().hex


def generate_owner_token() -> str:
    return uuid4().hex


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def compute_expiry(hours: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=hours)
