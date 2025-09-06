import os
import pytest
from fastapi.testclient import TestClient

from app.main import app


def has_external():
    return bool(os.getenv("OPENROUTER_API_KEY") and os.getenv("R2_ACCOUNT_ID") and os.getenv("R2_ACCESS_KEY_ID") and os.getenv("R2_SECRET_ACCESS_KEY"))


@pytest.mark.skipif(not has_external(), reason="Requires OpenRouter and R2 credentials")
def test_render_happy_path():
    client = TestClient(app)
    payload = {
        "project_id": "demo",
        "prompts": {"task": "create", "instruction": "Create a banner"},
        "outputs": {"count": 1, "format": "png", "dimensions": "512x512"}
    }
    r = client.post("/render", json=payload)
    assert r.status_code == 200, r.text
    js = r.json()
    assert "assets" in js and len(js["assets"]) >= 1
    assert "audit" in js
    assert js["audit"].get("verified_by") in {"declared", "external", "none"}

