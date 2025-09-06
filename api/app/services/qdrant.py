from __future__ import annotations

from typing import List, Optional, Dict, Any

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from ..core.config import settings


COLLECTION = "brand_assets"
COLLECTIONS = ["brand_assets", "design_examples", "style_guides"]


async def ensure_collection():
    url = f"{settings.qdrant_url}/collections/{COLLECTION}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(url)
        if r.status_code == 200:
            return
        schema = {
            "name": COLLECTION,
            "vectors": {"size": 384, "distance": "Cosine"},
        }
        r = await client.put(f"{settings.qdrant_url}/collections/{COLLECTION}", json=schema)
        r.raise_for_status()


async def upsert_vectors(ids: List[str], vectors: List[List[float]], payloads: Optional[List[dict]] = None):
    await ensure_collection()
    points = []
    for i, v in enumerate(vectors):
        p = {"id": ids[i], "vector": v}
        if payloads and i < len(payloads):
            p["payload"] = payloads[i]
        points.append(p)
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.put(f"{settings.qdrant_url}/collections/{COLLECTION}/points", json={"points": points})
        r.raise_for_status()


async def search(vector: List[float], limit: int = 5):
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.post(
            f"{settings.qdrant_url}/collections/{COLLECTION}/points/search",
            json={"vector": vector, "limit": limit},
        )
        r.raise_for_status()
        return r.json().get("result", [])


def get_sync_client() -> QdrantClient:
    """Get synchronous Qdrant client."""
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)


def ensure_collections_sync():
    """Ensure all collections exist with proper configuration."""
    client = get_sync_client()
    for collection_name in COLLECTIONS:
        try:
            client.get_collection(collection_name)
        except Exception:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )


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
