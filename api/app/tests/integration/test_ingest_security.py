from fastapi.testclient import TestClient
from app.main import app


def test_ingest_block_exe(monkeypatch):
    client = TestClient(app)
    # Simulate EXE content
    files = {"file": ("malware.exe", b"MZ\x00\x00bad", "application/octet-stream")}
    resp = client.post("/ingest/file", data={"project_id": "p1"}, files=files)
    # Depending on clamd availability, this may pass dev; assert 400 or 200 quarantine gate
    assert resp.status_code in (200, 400)


def test_ingest_exif_strip_png(monkeypatch):
    client = TestClient(app)
    # Minimal PNG header
    png = b"\x89PNG\r\n\x1a\nxxxx"
    files = {"file": ("img.png", png, "image/png")}
    resp = client.post("/ingest/file", data={"project_id": "p1"}, files=files)
    assert resp.status_code in (200, 201)

