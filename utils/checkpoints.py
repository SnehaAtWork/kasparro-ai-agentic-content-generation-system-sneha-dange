# utils/checkpoints.py
"""
Simple checkpoint helper to persist intermediate pipeline state to disk.
Used to save after parse, after logic blocks, etc.
Files written to artifacts/ by default.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def save(name: str, obj: Any, prefix: Optional[str] = None) -> str:
    """
    Save object as JSON under artifacts/ with timestamped filename.
    Returns path to saved file (str).
    """
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    fname = f"{prefix+'_' if prefix else ''}{name}_{ts}.json"
    path = ARTIFACTS_DIR / fname
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return str(path)

def load(path: str) -> Any:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)
