from fastapi.testclient import TestClient
from app.main import app


def test_health():
    c = TestClient(app)
    r = c.get('/healthz')
    assert r.status_code == 200
    assert r.json().get('ok') is True


def test_guardrails_render_plan_failure(monkeypatch):
    # Force planner to return invalid JSON by mocking call_task
    from app.services import openrouter as orc

    def fake_call_task(task, messages, trace=None, **kw):
        return {"choices": [{"message": {"content": "not-json"}}]}

    monkeypatch.setattr(orc, 'call_task', fake_call_task)

    c = TestClient(app)
    body = {
        "project_id": "p1",
        "prompts": {"task": "create", "instruction": "xxxxx"},
        "outputs": {"count": 1, "format": "png", "dimensions": "64x64"},
    }
    r = c.post('/render', json=body)
    assert r.status_code == 422

