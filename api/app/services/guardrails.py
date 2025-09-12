from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException
from jsonschema import Draft7Validator


_SCHEMA_CACHE: Dict[str, Draft7Validator] = {}


def _load_schema(name: str) -> Draft7Validator:
    if name in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[name]
    
    # Try to find the guardrails directory
    current_path = Path(__file__).resolve()
    
    # Look for guardrails directory by traversing up the directory tree
    for parent in [current_path.parent] + list(current_path.parents):
        guardrails_path = parent / "guardrails"
        if guardrails_path.exists():
            schema_path = guardrails_path / name
            break
    else:
        # Fallback: try relative to current file
        schema_path = current_path.parent.parent.parent / "guardrails" / name
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    validator = Draft7Validator(schema)
    _SCHEMA_CACHE[name] = validator
    return validator


def validate_contract(name: str, payload: Any) -> None:
    validator = _load_schema(name)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if errors:
        msgs = [f"{list(e.path)}: {e.message}" for e in errors]
        raise HTTPException(status_code=422, detail={"guardrails": msgs})
