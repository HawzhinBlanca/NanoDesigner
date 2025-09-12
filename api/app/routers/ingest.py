from __future__ import annotations

import hashlib
import uuid
from typing import List, Optional
import json

from fastapi import APIRouter, Body, HTTPException, UploadFile, File, Form, Header, Request
from pydantic import BaseModel

from ..models.schemas import IngestRequest, IngestResponse
from ..services.embed import embed_text
from ..services.redis import cache_get_set, sha1key
from ..services.qdrant import upsert_vectors, ensure_collections_sync, upsert_vectors_sync
from ..services.unstructured import basic_parse_text_blobs
from ..services.docai import process_document_bytes, extract_text_blocks
from ..services.storage_adapter import put_object, get_object, put_quarantine, promote_quarantine_to_public
from ..core.security import extract_org_id_from_request_headers
from ..services.canon import extract_canon_from_evidence
from ..services.langfuse import Trace
from ..services.security_scanner import scan_upload, strip_exif_from_image
from ..core.config import settings
from ..core.security import InputSanitizer


router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    request: IngestRequest = Body(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    http_request: Request = None
):
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
    # Idempotency: if present, check cached response
    if idempotency_key:
        try:
            from ..services.redis import get_client
            import hashlib, json as _json
            cache = get_client()
            body_hash = hashlib.sha256(_json.dumps(request.model_dump(), sort_keys=True).encode("utf-8")).hexdigest()
            idem_key = f"idemp:ingest:{idempotency_key}:{request.project_id}:{body_hash}"
            prev = cache.get(idem_key)
            if prev:
                return IngestResponse(**_json.loads(prev))
        except Exception:
            pass
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
                    
                    # Security scan the content
                    with trace.span("security_scan"):
                        scan_result = scan_upload(content, filename=asset_ref)
                        
                        # If it's an image and EXIF was not already removed, strip it
                        if scan_result.get("actual_mime", "").startswith("image/") and not scan_result.get("exif_removed"):
                            content = strip_exif_from_image(content)
                            trace.log("EXIF metadata stripped from image")
                    
                    # Promote from quarantine to public after successful scan
                    if asset_ref.startswith("quarantine/"):
                        public_key = promote_quarantine_to_public(asset_ref)
                        trace.log(f"Asset promoted from quarantine to {public_key}")
                    
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
            headers = dict(request.headers)
            await upsert_vectors(ids, vectors, payloads, headers=headers)
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
    
    resp = IngestResponse(processed=processed, qdrant_ids=ids)
    if idempotency_key:
        try:
            cache.setex(idem_key, 86400, json.dumps(resp.model_dump()))
        except Exception:
            pass
    return resp


@router.post("/ingest/file")
async def ingest_file(
    request: Request,
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
    headers = dict(request.headers)
    org_id = extract_org_id_from_request_headers(headers, fallback=safe_project_id)
    quarantine_key = put_quarantine(safe_project_id, safe_filename, content, content_type=file.content_type or "application/octet-stream", org_id=org_id)
    
    # Process using main ingest endpoint
    request = IngestRequest(project_id=safe_project_id, assets=[quarantine_key])
    
    return await ingest(request)
