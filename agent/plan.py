from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Plan:
    kind: str
    tool: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    reply: str = ""
