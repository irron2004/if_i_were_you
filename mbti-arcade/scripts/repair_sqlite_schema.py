from __future__ import annotations

import sys
from pathlib import Path

from app.utils.sqlite_schema_repair import repair_sqlite_file


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python repair_sqlite_schema.py <sqlite_db_path>")
        return 2

    db_path = Path(sys.argv[1]).resolve()
    changed = repair_sqlite_file(db_path)
    print(f"DB: {db_path}")
    if not changed:
        print("No changes (db not found or no target tables)")
        return 0

    for key, did_change in sorted(changed.items()):
        print(f"{key}: {'added' if did_change else 'ok'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
