from __future__ import annotations

import os
import subprocess
from pathlib import Path


def main() -> None:
    base_dir = Path(__file__).resolve().parent / "mbti-arcade"
    os.chdir(base_dir)

    subprocess.run(["alembic", "upgrade", "head"], check=True)

    port = os.environ.get("PORT", "8000")
    os.execvp(
        "uvicorn",
        ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", port],
    )


if __name__ == "__main__":
    main()
