from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import unquote


def _get_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _maybe_add_column(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    ddl_type: str,
    default_clause: str | None = None,
) -> bool:
    cols = _get_columns(conn, table)
    if column in cols:
        return False

    default_sql = f" DEFAULT {default_clause}" if default_clause is not None else ""
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}{default_sql}")
    return True


def _sqlite_raw_path(database_url: str) -> str | None:
    for prefix in ("sqlite+pysqlite:///", "sqlite:///"):
        if database_url.startswith(prefix):
            raw = unquote(database_url[len(prefix) :])
            if raw == ":memory:":
                return None
            return raw
    return None


def _candidate_paths(raw_path: str) -> list[Path]:
    path = Path(raw_path)
    if path.is_absolute():
        return [path]

    candidates: list[Path] = [
        Path.cwd() / path,
        Path("/app") / path,
        Path("/app/mbti-arcade") / path,
    ]
    unique: list[Path] = []
    seen: set[Path] = set()
    for item in candidates:
        resolved = item.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def repair_sqlite_file(db_path: Path) -> dict[str, bool]:
    if not db_path.exists():
        return {}

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        changed: dict[str, bool] = {}

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        if "sessions" in tables:
            changed["sessions.owner_token_hash"] = _maybe_add_column(
                conn,
                table="sessions",
                column="owner_token_hash",
                ddl_type="VARCHAR(64)",
            )

        if "pair" in tables:
            changed["pair.my_avatar"] = _maybe_add_column(
                conn,
                table="pair",
                column="my_avatar",
                ddl_type="VARCHAR",
            )
            changed["pair.my_mbti_source"] = _maybe_add_column(
                conn,
                table="pair",
                column="my_mbti_source",
                ddl_type="VARCHAR(20)",
                default_clause="'input'",
            )
            changed["pair.show_public"] = _maybe_add_column(
                conn,
                table="pair",
                column="show_public",
                ddl_type="BOOLEAN",
                default_clause="1",
            )

        conn.commit()
        return changed


def repair_sqlite_schema_for_url(database_url: str) -> dict[str, bool]:
    raw = _sqlite_raw_path(database_url)
    if not raw:
        return {}

    combined: dict[str, bool] = {}
    for path in _candidate_paths(raw):
        changed = repair_sqlite_file(path)
        for key, value in changed.items():
            combined[key] = combined.get(key, False) or value
    return combined
