from __future__ import annotations

import json
from typing import List, Optional, Dict, Any

from .openrouter import call_task
from .prompts import CANON_SYSTEM
from .langfuse import Trace
from .qdrant import search_vectors, get_sync_client


def extract_canon_from_evidence(project_id: str, evidence_ids: List[str], trace: Optional[Trace] = None) -> Dict[str, Any]:
    """Use LLM to extract canon JSON from evidence IDs.

    This function assumes the caller fetched/ingested documents and stored them in Qdrant.
    It queries Qdrant to retrieve payload snippets for the evidence IDs and provides them to the LLM.
    """
    client = get_sync_client()
    # Retrieve points by IDs
    points = client.retrieve(collection_name="brand_assets", ids=evidence_ids)
    snippets: List[str] = []
    for p in points or []:
        payload = getattr(p, "payload", None) or {}
        text = payload.get("text") or payload.get("asset_ref") or ""
        if text:
            snippets.append(text[:500])
    context = {"project_id": project_id, "evidence": snippets}
    resp = call_task(
        "canon",
        [
            {"role": "system", "content": CANON_SYSTEM},
            {"role": "user", "content": json.dumps(context)},
        ],
        trace=trace,
        temperature=0.0,
    )
    content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
    start = content.find("{")
    end = content.rfind("}")
    return json.loads(content[start : end + 1] if start != -1 and end != -1 else content)


def derive_canon_from_project(project_id: str, trace: Optional[Trace] = None) -> Dict[str, Any]:
    """Derive canon by sampling project documents from Qdrant and asking the LLM.
    """
    client = get_sync_client()
    # We do a naive scroll using search without query but filtered by project
    # If client supports, we can use scroll API. Here we sample via search on a generic token.
    examples = search_vectors("brand_assets", query_text="brand", filters={"project_id": project_id}, limit=5)
    snippets: List[str] = []
    for ex in examples or []:
        payload = getattr(ex, "payload", None) or {}
        text = payload.get("text") or payload.get("asset_ref") or ""
        if text:
            snippets.append(text[:500])
    context = {"project_id": project_id, "evidence": snippets}
    resp = call_task(
        "canon",
        [
            {"role": "system", "content": CANON_SYSTEM},
            {"role": "user", "content": json.dumps(context)},
        ],
        trace=trace,
        temperature=0.0,
    )
    content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
    start = content.find("{")
    end = content.rfind("}")
    return json.loads(content[start : end + 1] if start != -1 and end != -1 else content)

"""
Canon extraction and management service.
Handles brand canon derivation from ingested documents.
"""

import json
from typing import Dict, List, Optional, Any
import hashlib

from ..services.openrouter import call_task
from ..services.guardrails import validate_contract
from ..services.qdrant import search_vectors, get_vector_by_id
from ..services.redis import cache_get_set, sha1key
from ..services.langfuse import Trace
from ..services.prompts import CANON_EXTRACTOR_SYSTEM


def extract_canon_from_evidence(
    project_id: str,
    evidence_ids: List[str],
    trace: Optional[Trace] = None
) -> Dict[str, Any]:
    """
    Extract brand canon from evidence documents.
    
    Args:
        project_id: Project identifier
        evidence_ids: List of Qdrant vector IDs to use as evidence
        trace: Optional Langfuse trace
        
    Returns:
        Normalized canon dictionary with palette, fonts, voice
    """
    
    def _factory() -> bytes:
        # Fetch evidence from Qdrant
        evidence_docs = []
        for eid in evidence_ids:
            vec = get_vector_by_id("brand_assets", eid)
            if vec and vec.payload:
                evidence_docs.append(vec.payload.get("text", ""))
        
        if not evidence_docs:
            raise ValueError(f"No evidence found for IDs: {evidence_ids}")
        
        # Prepare evidence text
        evidence_text = "\n\n---\n\n".join(evidence_docs[:10])  # Limit to 10 docs
        
        # Call LLM to extract canon
        messages = [
            {"role": "system", "content": CANON_EXTRACTOR_SYSTEM},
            {"role": "user", "content": f"Extract brand canon from these documents:\n\n{evidence_text}"}
        ]
        
        resp = call_task("planner", messages, trace=trace, temperature=0.1)
        content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Parse JSON response
        canon = None
        if isinstance(content, str):
            try:
                canon = json.loads(content)
            except Exception:
                # Try to extract JSON from markdown
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1:
                    canon = json.loads(content[start:end+1])
        
        if not canon:
            # Fallback to minimal canon
            canon = {
                "palette_hex": ["#000000", "#FFFFFF"],
                "fonts": ["Helvetica"],
                "voice": {
                    "tone": "professional",
                    "dos": ["Be clear", "Be concise"],
                    "donts": ["Avoid jargon"]
                }
            }
        
        # Validate against Guardrails schema
        validate_contract("canon.json", canon)
        
        return json.dumps(canon).encode("utf-8")
    
    # Cache key based on evidence IDs
    cache_key = sha1key("canon", project_id, ",".join(sorted(evidence_ids)))
    canon_bytes = cache_get_set(cache_key, _factory, ttl=86400 * 7)  # Cache for 7 days
    
    return json.loads(canon_bytes.decode("utf-8"))


def derive_canon_from_project(
    project_id: str,
    limit: int = 20,
    trace: Optional[Trace] = None
) -> Dict[str, Any]:
    """
    Derive canon by searching for relevant brand assets in project.
    
    Args:
        project_id: Project identifier
        limit: Maximum number of documents to consider
        trace: Optional Langfuse trace
        
    Returns:
        Derived canon dictionary
    """
    
    # Search for brand-related documents in Qdrant
    query_text = f"brand guidelines style palette fonts logo {project_id}"
    results = search_vectors(
        collection="brand_assets",
        query_text=query_text,
        filters={"project_id": project_id},
        limit=limit
    )
    
    if not results:
        # Return default canon if no brand assets found
        return {
            "palette_hex": ["#000000", "#FFFFFF", "#808080"],
            "fonts": ["Inter", "Roboto"],
            "voice": {
                "tone": "professional",
                "dos": ["Be clear", "Be helpful", "Be concise"],
                "donts": ["Use jargon", "Be overly casual"]
            }
        }
    
    # Extract IDs from search results
    evidence_ids = [str(r.id) for r in results]
    
    return extract_canon_from_evidence(project_id, evidence_ids, trace)


def merge_canons(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two canon dictionaries, with override taking precedence.
    
    Args:
        base: Base canon dictionary
        override: Override canon dictionary
        
    Returns:
        Merged canon dictionary
    """
    merged = base.copy()
    
    if "palette_hex" in override:
        merged["palette_hex"] = override["palette_hex"]
    
    if "fonts" in override:
        merged["fonts"] = override["fonts"]
    
    if "voice" in override:
        if "voice" not in merged:
            merged["voice"] = {}
        merged["voice"].update(override["voice"])
    
    return merged


def validate_canon(canon: Dict[str, Any]) -> bool:
    """
    Validate a canon dictionary against the Guardrails schema.
    
    Args:
        canon: Canon dictionary to validate
        
    Returns:
        True if valid
        
    Raises:
        HTTPException: If validation fails
    """
    validate_contract("canon.json", canon)
    return True