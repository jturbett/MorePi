from __future__ import annotations

from pathlib import Path
import os


def get_secret(name: str, default: str | None = None) -> str | None:
    """Return secret from `<NAME>_FILE` path or `<NAME>` env var.

    Priority order:
    1) `<NAME>_FILE` file contents
    2) `<NAME>` environment variable
    3) provided default
    """
    file_key = f"{name}_FILE"
    file_path = os.getenv(file_key)

    if file_path:
        value = Path(file_path).read_text(encoding="utf-8").strip()
        if value:
            return value

    env_value = os.getenv(name)
    if env_value:
        return env_value.strip()

    return default
