import os
import pytest


def _otel_installed() -> bool:
    try:
        import opentelemetry  # noqa: F401
        import opentelemetry.instrumentation.fastapi  # noqa: F401
        import opentelemetry.instrumentation.httpx  # noqa: F401
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _otel_installed(), reason="OpenTelemetry not installed")
def test_traceparent_header_present(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    # Traceparent should be present when OTEL is enabled
    assert "Traceparent" in resp.headers

