from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .config import get_config


def _cache_root() -> Path:
    config = get_config()
    cache_dir = Path(config.get("data_cache_dir", "data_cache")) / "yfinance"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _cache_file_path(prefix: str, payload: dict[str, Any], extension: str) -> Path:
    canonical_payload = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()[:20]
    safe_prefix = "".join(ch for ch in prefix if ch.isalnum() or ch in ("_", "-"))
    return _cache_root() / f"{safe_prefix}-{digest}.{extension}"


def _is_stale(path: Path, max_age_seconds: int) -> bool:
    if not path.exists():
        return True
    age_seconds = time.time() - path.stat().st_mtime
    return age_seconds > max_age_seconds


def get_cached_text(
    *,
    prefix: str,
    payload: dict[str, Any],
    max_age_seconds: int,
    fetcher: Callable[[], str],
) -> str:
    path = _cache_file_path(prefix, payload, "txt")

    if not _is_stale(path, max_age_seconds):
        return path.read_text(encoding="utf-8")

    content = fetcher()
    path.write_text(content, encoding="utf-8")
    return content


def get_cached_dataframe(
    *,
    prefix: str,
    payload: dict[str, Any],
    max_age_seconds: int,
    fetcher: Callable[[], pd.DataFrame],
) -> pd.DataFrame:
    path = _cache_file_path(prefix, payload, "csv")

    if not _is_stale(path, max_age_seconds):
        try:
            return pd.read_csv(path, on_bad_lines="skip")
        except Exception:
            # Corrupted cache entries are replaced by a fresh fetch.
            pass

    data = fetcher()
    data.to_csv(path, index=False)
    return data
