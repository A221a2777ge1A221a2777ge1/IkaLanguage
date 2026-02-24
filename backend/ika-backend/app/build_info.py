"""
Build and dataset fingerprint for verification (Cursor, GitHub, Cloud Run).
Reads GIT_SHA from env; hashes data/ contents for deterministic dataset_sha256.
"""
import hashlib
import os
from pathlib import Path
from typing import Any, Dict


def _dataset_fingerprint(data_dir: Path) -> tuple[str, int]:
    """
    Compute SHA256 over data directory: walk in sorted order, hash (path + bytes).
    Returns (hex digest, file count). On missing dir or error returns ("missing", 0).
    """
    if not data_dir.is_dir():
        return ("missing", 0)
    h = hashlib.sha256()
    count = 0
    try:
        for rel_path in sorted(data_dir.rglob("*")):
            if rel_path.is_file():
                count += 1
                # Use relative path for determinism
                h.update(rel_path.relative_to(data_dir).as_posix().encode("utf-8"))
                h.update(rel_path.read_bytes())
    except Exception:
        return ("error", count)
    return (h.hexdigest(), count)


def get_build_info() -> Dict[str, Any]:
    """
    Return build info for /health and /build-info.
    Lightweight; must not crash if Firebase/Firestore fails (no external deps here).
    """
    git_sha = os.getenv("GIT_SHA", "unknown")
    # Data dir: in container /app/data; locally same parent as app (backend/ika-backend/data)
    app_dir = Path(__file__).resolve().parent
    data_dir = app_dir.parent / "data"
    dataset_sha256, dataset_files_count = _dataset_fingerprint(data_dir)
    return {
        "git_sha": git_sha,
        "dataset_sha256": dataset_sha256,
        "dataset_files_count": dataset_files_count,
    }
