from __future__ import annotations

import hashlib
import uuid
from typing import List, Optional
import json

from fastapi import APIRouter, Body, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from ..models.schemas import IngestRequest, IngestResponse
from ..services.embed import embed_text
from ..services.redis import cache_get_set, sha1key
from ..services.qdrant import upsert_vectors, ensure_collections_sync, upsert_vectors_sync
from ..services.unstructured import basic_parse_text_blobs
from ..services.docai import process_document_bytes, extract_text_blocks
from ..services.storage_r2 import put_object, get_object
from ..services.canon import extract_canon_from_evidence
from ..services.langfuse import Trace
from ..core.config import settings
from ..core.security import InputSanitizer


router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest = Body(...)):
    """
    Ingest brand assets and documents.
    
    Flow:
    1. Upload to R2 (quarantine path)
    2. Unstructured → basic parse
    3. Document AI → structure (tables/forms/layout)
    4. Canon extractor (LLM) → normalized JSON
    5. Embed & upsert to Qdrant; cache in Redis
    6. Return stats + IDs
    """
    trace = Trace("ingest")
    project_id = request.project_id
    # Sanitize inputs
    sanitizer = InputSanitizer(mode="strict")
    project_id = sanitizer.sanitize(request.project_id)
    assets = [sanitizer.sanitize(a) for a in request.assets]
    
    # Ensure collections exist
    ensure_collections_sync()
    
    ids: List[str] = []
    vectors: List[List[float]] = []
    payloads: List[dict] = []
    
    with trace.span("process_assets"):
        for asset_ref in assets:
            try:
                # Process each asset
                with trace.span("process_asset", {"asset": asset_ref}):
                    # Check if it's an R2 reference or external URL
                    if asset_ref.startswith("quarantine/") or asset_ref.startswith("public/"):
                        # Fetch from R2
                        content = get_object(asset_ref)
                        if not content:
                            continue
                    else:
                        # External URLs: apply allowlist; do not fetch to avoid SSRF
                        from urllib.parse import urlparse
                        allowed = {h.strip() for h in (settings.ref_url_allow_hosts or "").split(",") if h.strip()}
                        u = urlparse(asset_ref)
                        if u.scheme and u.scheme != "https":
                            raise HTTPException(status_code=400, detail={"error": "invalid_protocol", "message": "Only https allowed"})
                        if allowed and (u.hostname not in allowed):
                            raise HTTPException(status_code=400, detail={"error": "forbidden_host", "message": f"Host {u.hostname} not allowed"})
                        # Use URL literal as content
                        content = asset_ref.encode("utf-8")
                    
                    # Try Document AI first if it's a document
                    text_blocks = []
                    try:
                        if len(content) > 100:  # Skip very small content
                            doc = process_document_bytes(content)
                            if doc:
                                text_blocks = extract_text_blocks(doc)
                    except Exception as e:
                        trace.log(f"DocAI failed: {e}")
                    
                    # Fallback to basic parsing if DocAI didn't work
                    if not text_blocks:
                        text_blobs = basic_parse_text_blobs([asset_ref])
                        text_blocks = text_blobs if text_blobs else [asset_ref]
                    
                    # Combine text blocks
                    full_text = "\n\n".join(text_blocks)
                    
                    # Generate embedding with caching
                    cache_key = sha1key("embed", full_text)
                    
                    def _embed_factory() -> bytes:
                        vec = embed_text(full_text)
                        return ",".join(map(str, vec)).encode("utf-8")
                    
                    raw = cache_get_set(cache_key, _embed_factory, ttl=864000)  # 10 days cache
                    vec = [float(x) for x in raw.decode("utf-8").split(",")]
                    
                    # Generate unique ID for this vector
                    vid = str(uuid.uuid4())
                    
                    # Prepare payload
                    payload = {
                        "project_id": project_id,
                        "asset_ref": asset_ref,
                        "text": full_text[:1000],  # Store first 1000 chars for reference
                        "type": "document"
                    }
                    
                    ids.append(vid)
                    vectors.append(vec)
                    payloads.append(payload)
                    
            except Exception as e:
                trace.log(f"Failed to process asset {asset_ref}: {e}")
                continue
    
    # Upsert to Qdrant
    processed = 0
    if ids:
        with trace.span("qdrant_upsert", {"count": len(ids)}):
            await upsert_vectors(ids, vectors, payloads)
            processed = len(ids)
    
    # Try to extract canon from the ingested documents
    if ids and len(ids) >= 2:
        try:
            with trace.span("canon_extraction"):
                canon = extract_canon_from_evidence(project_id, ids[:5], trace)  # Use first 5 docs
                # Cache the extracted canon
                canon_key = sha1key("canon", project_id, "latest")
                cache_get_set(
                    canon_key,
                    lambda: json.dumps(canon).encode("utf-8"),
                    ttl=86400 * 7  # 7 days
                )
        except Exception as e:
            trace.log(f"Canon extraction failed: {e}")
    
    await trace.flush()
    
    return IngestResponse(processed=processed, qdrant_ids=ids)


@router.post("/ingest/file")
async def ingest_file(
    project_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Direct file upload endpoint for document ingestion.
    """
    trace = Trace("ingest_file")
    
    # Read file content
    content = await file.read()
    
    # Store in R2 quarantine
    sanitizer = InputSanitizer(mode="strict")
    safe_project_id = sanitizer.sanitize(project_id)
    safe_filename = sanitizer.sanitize(file.filename)
    quarantine_key = f"quarantine/{safe_project_id}/{uuid.uuid4()}_{safe_filename}"
    put_object(quarantine_key, content, content_type=file.content_type or "application/octet-stream")
    
    # Process using main ingest endpoint
    request = IngestRequest(project_id=safe_project_id, assets=[quarantine_key])
    
    return await ingest(request)
