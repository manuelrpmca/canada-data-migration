"""Raw landing: save each API response exactly as received, before any parsing (ADR 0005)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LandedFile:
    path: Path
    sha256: str


def land(raw: bytes, root: Path, source: str, series_key: str, run_id: str) -> LandedFile:
    """Write `raw` to `<root>/raw/<source>/<series_key>/<run_id>.json` and return its hash."""
    target_dir = root / "raw" / source / series_key
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{run_id}.json"
    path.write_bytes(raw)
    return LandedFile(path=path, sha256=hashlib.sha256(raw).hexdigest())
