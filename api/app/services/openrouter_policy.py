from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


class Policy:
    def __init__(self, data: dict):
        self.data = data

    def model_for(self, task: str) -> str:
        t = self.data.get("tasks", {}).get(task)
        if not t:
            raise ValueError(f"No policy for task '{task}'")
        return t.get("primary")

    def fallbacks_for(self, task: str) -> List[str]:
        t = self.data.get("tasks", {}).get(task, {})
        return t.get("fallbacks", [])

    def timeout_ms_for(self, key: str) -> int:
        return int(self.data.get("timeouts_ms", {}).get(key, self.data.get("timeouts_ms", {}).get("default", 20000)))

    def retry_conf(self) -> dict:
        return self.data.get("retry", {"max_attempts": 2, "backoff_ms": 400})


_policy: Optional[Policy] = None


def load_policy() -> Policy:
    global _policy
    if _policy is not None:
        return _policy
    root = Path(__file__).resolve().parents[2]  # /app
    with open(root / "policies" / "openrouter_policy.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    _policy = Policy(data)
    return _policy

