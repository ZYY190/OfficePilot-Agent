from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("AGENT_DATA_DIR", ROOT / "data")).resolve()
WORKSPACE_DIR = Path(os.environ.get("AGENT_WORKSPACE_DIR", ROOT / "workspace")).resolve()
DB_PATH = Path(os.environ.get("AGENT_DB_PATH", DATA_DIR / "agent.db")).resolve()

DATA_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

WEB_HOST = os.environ.get("AGENT_WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.environ.get("AGENT_WEB_PORT", "8765"))
MAX_HISTORY = int(os.environ.get("AGENT_MAX_HISTORY", "12"))
