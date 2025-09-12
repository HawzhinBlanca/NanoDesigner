"""Hardened file upload endpoint with quarantine and security scanning.

This endpoint:
- Validates file size and type
- Scans using EnhancedSecurityManager (and ClamAV if available)
- Stores in quarantine via storage adapter, and promotes to public on pass
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Query
from typing import Dict, Any, Optional
import os
import io
import uuid
from pathlib import Path

from ..core.enhanced_security import security_manager, ThreatLevel
from ..core.security import extract_org_id_from_request_headers
from ..services.storage_adapter import (
    put_quarantine,
    promote_quarantine_to_public,
    signed_public_url,
)

router = APIRouter()


MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_PREFIXES = (
    "image/",
    "application/pdf",
    "text/plain",
)


def _clamav_scan(content: bytes) -> Optional[str]:
    """Scan bytes with ClamAV if available. Returns virus name if infected, else None."""
    try:
        import clamd  # type: ignore
        host = os.getenv("CLAMAV_HOST", "clamav")
        port = int(os.getenv("CLAMAV_PORT", "3310"))
        cd = clamd.ClamdNetworkSocket(host=host, port=port)
        result = cd.instream(io.BytesIO(content))
        # result example: {'stream': ('FOUND', 'Eicar-Test-Signature')}
        status, signature = result.get("stream", ("OK", None))
        if status == "FOUND":
            return str(signature)
        return None
    except Exception:
        # Best-effort: if ClamAV not reachable, skip silently
        return None


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    project_id: Optional[str] = Query(None, description="Project ID for storage key scoping"),
) -> Dict[str, Any]:
    """Secure file upload with quarantine and scanning."""
    try:
        # Size guard: read into memory once; enforce cap
        content = await file.read()
        size = len(content)
        if size == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        if size > MAX_SIZE_BYTES:
            raise HTTPException(status_code=413, detail=f"File exceeds {MAX_SIZE_BYTES // (1024*1024)}MB limit")

        # Basic MIME allowlist (best-effort; authoritative check happens in enhanced security)
        content_type = (file.content_type or "").lower()
        if not content_type or not any(
            content_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES
        ):
            raise HTTPException(status_code=415, detail=f"Unsupported Content-Type: {content_type}")

        # Disallow SVG uploads explicitly due to XSS risk
        if (file.filename or "").lower().endswith(".svg") or content_type == "image/svg+xml":
            raise HTTPException(status_code=415, detail="SVG uploads are not allowed")

        # Enhanced security scan
        scan = security_manager.scan_file_upload(content, file.filename or "upload.bin")
        # Enforce policy (raises for malicious/blocked)
        security_manager.enforce_policy(scan, operation="file_upload")

        # Optional ClamAV scan
        virus = _clamav_scan(content)
        if virus:
            raise HTTPException(status_code=400, detail=f"Malware detected: {virus}")

        # Determine org_id from headers (best-effort) and project id
        headers = request.headers
        org_id = extract_org_id_from_request_headers(headers, fallback=project_id or "uploads")
        proj = project_id or "uploads"

        # Store to quarantine first
        quarantine_key = put_quarantine(
            project_id=proj,
            filename=file.filename or "upload.bin",
            data=content,
            content_type=content_type,
            org_id=org_id,
        )

        # Promote to public if threat level is SAFE; if SUSPICIOUS keep quarantined
        promoted = None
        if scan.threat_level == ThreatLevel.SAFE:
            storage_key = promote_quarantine_to_public(quarantine_key)
            url = signed_public_url(storage_key)
            promoted = {
                "storage_key": storage_key,
                "url": url,
            }

        response: Dict[str, Any] = {
            "success": True,
            "filename": file.filename,
            "size": size,
            "content_type": content_type,
            "org_id": org_id,
            "project_id": proj,
            "quarantine_key": quarantine_key,
            "security": {
                "threat_level": scan.threat_level.value,
                "reasons": scan.reasons,
                "clamav": "clean" if not virus else virus,
            },
        }
        if promoted:
            response.update({
                "asset": promoted,
                "message": "File uploaded and published",
            })
        else:
            response.update({
                "message": "File uploaded to quarantine (requires manual review)",
            })

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
