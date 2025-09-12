import os
import json
from app.services.cost_control import get_cost_control_service


def test_budget_alert_thresholds(monkeypatch):
    monkeypatch.setenv("DAILY_BUDGET_USD", "0.05")
    calls = []

    def fake_post(url, json=None):
        calls.append({"url": url, "json": json})
        class R:
            def raise_for_status(self):
                return None
        return R()

    import httpx
    monkeypatch.setattr(httpx, "Client", lambda timeout=5.0: type("C", (), {"__enter__": lambda s: type("X", (), {"post": fake_post})(), "__exit__": lambda s, *a: False}))
    monkeypatch.setenv("BUDGET_ALERT_WEBHOOK", "http://webhook")

    svc = get_cost_control_service()
    # Reset internal state by recreating service
    # Spend to cross 50%, 80%, 100%
    org = "org-test"
    svc.track_cost(org, 0.03, "openrouter/gpt-5", "planner")  # >50%
    svc.track_cost(org, 0.02, "openrouter/gpt-5", "planner")  # >100%

    assert any(c["json"]["alert_level"] == 50 for c in calls)
    assert any(c["json"]["alert_level"] == 100 for c in calls)

