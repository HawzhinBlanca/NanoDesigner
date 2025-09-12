from __future__ import annotations

import json
from typing import List, Dict, Any

from fastapi import APIRouter, Body, HTTPException

from ..models.schemas import CritiqueRequest, CritiqueResponse
from ..services.guardrails import validate_contract
from ..services.openrouter import call_task
from ..services.prompts import CRITIC_SYSTEM
from ..services.langfuse import Trace
from ..services.canon import derive_canon_from_project
from ..services.storage_r2 import get_object, signed_public_url
from ..services.redis import cache_get_set, sha1key


router = APIRouter()


@router.post("/critique", response_model=CritiqueResponse)
async def critique(request: CritiqueRequest = Body(...)):
    """
    Critique assets against brand canon.
    
    Flow:
    1. Retrieve brand canon for project
    2. Fetch asset data/metadata
    3. Call critic LLM to evaluate
    4. Validate response with Guardrails
    5. Return score, violations, and repair suggestions
    """
    trace = Trace("critique")
    project_id = request.project_id
    asset_ids = request.asset_ids
    
    # Get brand canon for project
    canon = None
    with trace.span("fetch_canon"):
        # Try cache first
        canon_key = sha1key("canon", project_id, "latest")
        
        def _canon_factory() -> bytes:
            c = derive_canon_from_project(project_id, trace=trace)
            return json.dumps(c).encode("utf-8")
        
        canon_bytes = cache_get_set(canon_key, _canon_factory, ttl=86400)
        canon = json.loads(canon_bytes.decode("utf-8"))
    
    # Fetch asset information (OPTIMIZED: Batch processing)
    assets_info = []
    with trace.span("fetch_assets"):
        # Limit to 10 assets and batch process
        limited_asset_ids = asset_ids[:10]
        
        # Separate R2 keys from references for batch processing
        r2_assets = [aid for aid in limited_asset_ids if "/" in aid]
        reference_assets = [aid for aid in limited_asset_ids if "/" not in aid]
        
        # Batch generate signed URLs for R2 assets
        for asset_id in r2_assets:
            try:
                # Generate signed URL for reference
                url = signed_public_url(asset_id, expires_seconds=300)
                assets_info.append({
                    "id": asset_id,
                    "url": url,
                    "type": "image" if any(asset_id.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]) else "document"
                })
            except Exception as e:
                trace.log(f"Failed to process asset {asset_id}: {e}")
        
        # Batch add reference assets
        for asset_id in reference_assets:
            assets_info.append({"id": asset_id, "type": "reference"})
    
    # Prepare critique prompt
    critique_prompt = {
        "project_id": project_id,
        "brand_canon": canon,
        "assets": assets_info,
        "task": "Evaluate these assets against the brand canon. Identify violations and suggest repairs."
    }
    
    # Call critic LLM
    critique_result = None
    with trace.span("critic_evaluation"):
        resp = call_task(
            "critic",
            [
                {"role": "system", "content": CRITIC_SYSTEM},
                {"role": "user", "content": json.dumps(critique_prompt)}
            ],
            trace=trace,
            temperature=0.0,
        )
        
        content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Parse JSON response
        try:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                critique_result = json.loads(content[start:end+1])
            else:
                critique_result = json.loads(content)
        except Exception:
            # Fallback result if parsing fails
            critique_result = {
                "score": 0.5,
                "violations": ["Unable to parse critique response"],
                "repair_suggestions": ["Review asset manually"]
            }
    
    # Validate with Guardrails - strictly reject on failure per blueprint
    validate_contract("critique.json", critique_result)
    
    await trace.flush()
    
    return CritiqueResponse(**critique_result)
