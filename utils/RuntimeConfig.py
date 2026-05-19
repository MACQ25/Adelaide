from __future__ import annotations

from pathlib import Path
import os


def read_required_setting(env_var: str, fallback_path: str) -> str:
    value = os.getenv(env_var)
    if value:
        return value

    path = Path(fallback_path)
    if path.exists():
        return path.read_text(encoding="utf-8").splitlines()[0].strip()

    raise RuntimeError(
        f"Missing required setting {env_var}. Set the environment variable or provide {fallback_path}."
    )


def ensure_directories(*paths: str) -> None:
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)