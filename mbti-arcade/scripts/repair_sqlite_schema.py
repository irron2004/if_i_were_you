from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


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


def repair(db_path: Path) -> dict[str, bool]:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

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


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python repair_sqlite_schema.py <sqlite_db_path>")
        return 2

    db_path = Path(sys.argv[1]).resolve()
    changed = repair(db_path)
    print(f"DB: {db_path}")
    for key, did_change in sorted(changed.items()):
        print(f"{key}: {'added' if did_change else 'ok'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
