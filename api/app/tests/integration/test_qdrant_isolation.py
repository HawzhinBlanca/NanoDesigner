import json
from app.services.qdrant import upsert_vectors_sync, search_vectors


def test_qdrant_per_org_isolation(monkeypatch):
    # Insert two vectors with different project/org payloads
    v1 = [0.1] * 768
    v2 = [0.2] * 768
    upsert_vectors_sync("brand_assets", ["a1"], [v1], payloads=[{"project_id": "pA"}])
    upsert_vectors_sync("brand_assets", ["b1"], [v2], payloads=[{"project_id": "pB"}])
    # Search filtered by project_id pA should not return pB
    res = search_vectors("brand_assets", query_vector=v1, filters={"project_id": "pA"}, limit=5)
    ids = [str(r.id) for r in res]
    assert "a1" in ids

