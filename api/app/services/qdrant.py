from __future__ import annotations

from typing import List, Optional, Dict, Any

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from ..core.config import settings
from ..core.security import extract_org_id_from_request_headers


def _collection_for_org(org_id: str | None) -> str:
    base = "brand_assets"
    return f"{base}_{org_id}" if org_id else base

COLLECTION = "brand_assets"
COLLECTIONS = ["brand_assets", "design_examples", "style_guides"]


async def ensure_collection(org_id: str | None = None):
    """Ensure collection exists with proper timeout configuration."""
    name = _collection_for_org(org_id)
    url = f"{settings.qdrant_url}/collections/{name}"
    
    # Configure timeouts for different operations
    timeout = httpx.Timeout(
        connect=5.0,    # Connection timeout
        read=30.0,      # Read timeout for large responses
        write=10.0,     # Write timeout
        pool=5.0        # Pool timeout
    )
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url)
        if r.status_code == 200:
            return
        schema = {
            "name": name,
            "vectors": {"size": 768, "distance": "Cosine"},
        }
        r = await client.put(f"{settings.qdrant_url}/collections/{name}", json=schema)
        r.raise_for_status()


async def upsert_vectors(ids: List[str], vectors: List[List[float]], payloads: Optional[List[dict]] = None, headers: Optional[dict] = None):
    org_id = None
    if headers is not None:
        try:
            org_id = extract_org_id_from_request_headers(headers)
        except Exception:
            org_id = None
    await ensure_collection(org_id)
    points = []
    for i, v in enumerate(vectors):
        p = {"id": ids[i], "vector": v}
        if payloads and i < len(payloads):
            p["payload"] = payloads[i]
        points.append(p)
    
    # Use longer timeout for vector operations
    timeout = httpx.Timeout(
        connect=5.0,
        read=60.0,      # Longer read timeout for vector operations
        write=30.0,     # Longer write timeout for large payloads
        pool=5.0
    )
    
    # Attach org_id payload if available
    if org_id:
        for p in points:
            p.setdefault("payload", {})["org_id"] = org_id
    async with httpx.AsyncClient(timeout=timeout) as client:
        name = _collection_for_org(org_id)
        r = await client.put(f"{settings.qdrant_url}/collections/{name}/points", json={"points": points})
        r.raise_for_status()


async def search(vector: List[float], limit: int = 5, headers: Optional[dict] = None):
    timeout = httpx.Timeout(
        connect=5.0,
        read=30.0,      # Search operations can take time
        write=10.0,
        pool=5.0
    )
    
    org_id = None
    if headers is not None:
        try:
            org_id = extract_org_id_from_request_headers(headers)
        except Exception:
            org_id = None
    name = _collection_for_org(org_id)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            f"{settings.qdrant_url}/collections/{name}/points/search",
            json={"vector": vector, "limit": limit},
        )
        r.raise_for_status()
        return r.json().get("result", [])


def get_sync_client() -> QdrantClient:
    """Get synchronous Qdrant client."""
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)


def ensure_collections_sync():
    """Ensure all collections exist with proper configuration."""
    try:
        client = get_sync_client()
        for collection_name in COLLECTIONS:
            try:
                client.get_collection(collection_name)
            except Exception:
                try:
                    client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(size=768, distance=Distance.COSINE)
                    )
                except Exception:
                    # In tests where Qdrant isn't available, skip creating
                    pass
    except Exception:
        # Qdrant not reachable; allow caller to proceed if collection ops are optional
        pass


def search_vectors(
    collection: str,
    query_text: str = None,
    query_vector: List[float] = None,
    filters: Dict[str, Any] = None,
    limit: int = 10
) -> List[Any]:
    """
    Search vectors in a collection.
    
    Args:
        collection: Collection name
        query_text: Text to embed and search (if query_vector not provided)
        query_vector: Direct vector to search with
        filters: Filter conditions
        limit: Maximum results
        
    Returns:
        List of search results
    """
    client = get_sync_client()
    
    if not query_vector and query_text:
        # Generate embedding from text
        from ..services.embed import embed_text
        query_vector = embed_text(query_text)
    
    if not query_vector:
        return []
    
    # Build filter if provided
    qdrant_filter = None
    if filters:
        conditions = []
        for key, value in filters.items():
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        if conditions:
            qdrant_filter = Filter(must=conditions)
    
    results = client.search(
        collection_name=collection,
        query_vector=query_vector,
        query_filter=qdrant_filter,
        limit=limit
    )
    
    return results


def get_vector_by_id(collection: str, vector_id: str) -> Any:
    """
    Get a vector by ID from collection.
    
    Args:
        collection: Collection name
        vector_id: Vector ID
        
    Returns:
        Vector point or None
    """
    client = get_sync_client()
    try:
        points = client.retrieve(
            collection_name=collection,
            ids=[vector_id]
        )
        return points[0] if points else None
    except Exception:
        return None


def upsert_vectors_sync(
    collection: str,
    ids: List[str],
    vectors: List[List[float]],
    payloads: Optional[List[Dict[str, Any]]] = None
):
    """
    Upsert vectors synchronously.
    
    Args:
        collection: Collection name
        ids: Vector IDs
        vectors: Vector embeddings
        payloads: Optional metadata payloads
    """
    client = get_sync_client()
    points = []
    
    for i, vector in enumerate(vectors):
        point = PointStruct(
            id=ids[i],
            vector=vector,
            payload=payloads[i] if payloads and i < len(payloads) else {}
        )
        points.append(point)
    
    client.upsert(collection_name=collection, points=points)
