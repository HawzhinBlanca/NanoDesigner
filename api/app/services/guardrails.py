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
    # Get the project root (NanoDesigner directory)
    base = Path(__file__).resolve().parents[3]  # /Users/hawzhin/NanoDesigner
    schema_path = base / "guardrails" / name
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
