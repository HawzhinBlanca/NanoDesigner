from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Body, HTTPException

from ..models.schemas import CanonDeriveRequest, CanonDeriveResponse, CanonSaveRequest, CanonSaveResponse
from ..services.guardrails import validate_contract
from ..services.canon import extract_canon_from_evidence, derive_canon_from_project, save_canon
from ..services.redis import cache_get_set, sha1key
from ..services.langfuse import Trace


router = APIRouter()


@router.post("/canon/derive", response_model=CanonDeriveResponse)
async def canon_derive(request: CanonDeriveRequest = Body(...)):
    """
    Derive brand canon from evidence documents.
    
    Flow:
    1. Fetch evidence documents from Qdrant
    2. Extract brand elements using LLM
    3. Validate with Guardrails
    4. Cache result
    5. Return normalized canon
    """
    trace = Trace("canon_derive")
    project_id = request.project_id
    evidence_ids = request.evidence_ids
    
    canon = None
    
    with trace.span("derive_canon"):
        if evidence_ids:
            # Use specific evidence IDs
            canon = extract_canon_from_evidence(project_id, evidence_ids, trace)
        else:
            # Auto-derive from project assets
            canon = derive_canon_from_project(project_id, trace=trace)
    
    # Validate with Guardrails - strictly reject on failure per blueprint
    validate_contract("canon.json", canon)
    
    # Cache the derived canon
    cache_key = sha1key("canon", project_id, "derived")
    cache_get_set(
        cache_key,
        lambda: json.dumps(canon).encode("utf-8"),
        ttl=86400 * 7  # Cache for 7 days
    )
    
    await trace.flush()
    
    return CanonDeriveResponse(**canon)


@router.get("/canon/{project_id}")
async def get_canon(project_id: str):
    """
    Get cached canon for a project.
    """
    trace = Trace("get_canon")
    
    # Try to get from cache
    cache_key = sha1key("canon", project_id, "latest")
    
    def _factory() -> bytes:
        canon = derive_canon_from_project(project_id, trace=trace)
        return json.dumps(canon).encode("utf-8")
    
    canon_bytes = cache_get_set(cache_key, _factory, ttl=86400)
    canon = json.loads(canon_bytes.decode("utf-8"))
    
    await trace.flush()
    
    return canon


@router.put("/canon/{project_id}", response_model=CanonSaveResponse)
async def save_canon_endpoint(project_id: str, request: CanonSaveRequest = Body(...)):
    """
    Save/update canon for a project.
    
    Stores the canon data in Redis cache with proper TTL.
    Validates the canon structure before saving.
    """
    trace = Trace("save_canon")
    
    try:
        # Convert request to dictionary format
        canon_data = {
            "palette_hex": request.palette_hex,
            "fonts": request.fonts,
            "voice": {
                "tone": request.voice.tone,
                "dos": request.voice.dos,
                "donts": request.voice.donts
            }
        }
        
        # Save canon data
        save_canon(project_id, canon_data, trace=trace)
        
        await trace.flush()
        
        return CanonSaveResponse(
            success=True,
            message=f"Canon successfully saved for project {project_id}"
        )
        
    except Exception as e:
        await trace.flush()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to save canon: {str(e)}"
        )
