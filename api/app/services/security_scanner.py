from __future__ import annotations

import io
import logging
import os
import hashlib
import subprocess
import tempfile
from typing import Dict, Any, Optional, Tuple, List

import magic
from PIL import Image

from dataclasses import dataclass
from pathlib import Path

# Optional feature flags
try:
    import magic  # noqa: F401
    HAS_MAGIC = True
except Exception:
    HAS_MAGIC = False

try:
    from PIL import Image  # noqa: F401
    from PIL.ExifTags import TAGS  # noqa: F401
    HAS_PIL = True
except Exception:
    HAS_PIL = False

from ..core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class ScanResult:
    """Result from security scanning."""
    is_safe: bool
    threats: List[str]
    mime_type: str
    actual_mime: str
    exif_removed: bool
    file_hash: str
    scan_details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_safe": self.is_safe,
            "threats": self.threats,
            "mime_type": self.mime_type,
            "actual_mime": self.actual_mime,
            "exif_removed": self.exif_removed,
            "file_hash": self.file_hash,
            "scan_details": self.scan_details
        }


class SecurityScanner:
    """Service for scanning uploaded content for security threats."""
    
    def __init__(self):
        """Initialize security scanner."""
        self.clamav_available = self._check_clamav()
        self.magic_available = HAS_MAGIC
        self.pil_available = HAS_PIL
        
        # Allowed MIME types
        self.allowed_mimes = {
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
            "application/pdf",
            "text/plain",
            "text/html",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        }
        
        # Dangerous file extensions to block
        self.blocked_extensions = {
            ".exe", ".dll", ".scr", ".vbs", ".js", ".jar",
            ".bat", ".cmd", ".com", ".pif", ".application",
            ".gadget", ".msi", ".msp", ".hta", ".cpl",
            ".msc", ".jar", ".reg", ".app", ".sh"
        }
        
        logger.info(
            f"Security scanner initialized: ClamAV={self.clamav_available}, "
            f"Magic={self.magic_available}, PIL={self.pil_available}"
        )
    
    def _check_clamav(self) -> bool:
        """Check if ClamAV is available."""
        try:
            result = subprocess.run(
                ["clamscan", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def scan_content(
        self,
        content: bytes,
        declared_mime: Optional[str] = None,
        filename: Optional[str] = None
    ) -> ScanResult:
        """Perform comprehensive security scan on content.
        
        Args:
            content: Raw file content
            declared_mime: MIME type declared by client
            filename: Original filename if available
            
        Returns:
            ScanResult with scan details
        """
        threats = []
        scan_details = {}
        
        # Calculate file hash
        file_hash = hashlib.sha256(content).hexdigest()
        scan_details["hash"] = file_hash
        scan_details["size"] = len(content)
        
        # Check file extension if filename provided
        if filename:
            ext = Path(filename).suffix.lower()
            if ext in self.blocked_extensions:
                threats.append(f"Blocked file extension: {ext}")
                logger.warning(f"Blocked dangerous file extension: {ext}")
        
        # Verify MIME type
        actual_mime = self._detect_mime_type(content)
        scan_details["actual_mime"] = actual_mime
        scan_details["declared_mime"] = declared_mime
        
        if declared_mime and actual_mime != declared_mime:
            if not self._is_acceptable_mime_mismatch(declared_mime, actual_mime):
                threats.append(f"MIME mismatch: declared={declared_mime}, actual={actual_mime}")
                logger.warning(f"MIME type mismatch detected: {declared_mime} != {actual_mime}")
        
        # Check if MIME type is allowed
        if actual_mime not in self.allowed_mimes:
            threats.append(f"Disallowed MIME type: {actual_mime}")
            logger.warning(f"Disallowed MIME type: {actual_mime}")
        
        # Perform antivirus scan
        av_threats = self._scan_with_clamav(content)
        if av_threats:
            threats.extend(av_threats)
            scan_details["av_threats"] = av_threats
        
        # Process image-specific security
        exif_removed = False
        if actual_mime and actual_mime.startswith("image/"):
            processed_content, exif_removed = self._process_image_security(content, actual_mime)
            if exif_removed:
                scan_details["exif_removed"] = True
                # Return processed content with EXIF removed
                content = processed_content
        
        # Determine if content is safe
        is_safe = len(threats) == 0
        
        return ScanResult(
            is_safe=is_safe,
            threats=threats,
            mime_type=declared_mime or actual_mime,
            actual_mime=actual_mime,
            exif_removed=exif_removed,
            file_hash=file_hash,
            scan_details=scan_details
        )
    
    def _detect_mime_type(self, content: bytes) -> str:
        """Detect actual MIME type of content using libmagic."""
        if self.magic_available:
            try:
                mime = magic.from_buffer(content, mime=True)
                return mime
            except Exception as e:
                logger.error(f"Magic MIME detection failed: {e}")
        
        # Fallback: basic detection based on file signatures
        if content.startswith(b'\x89PNG'):
            return "image/png"
        elif content.startswith(b'\xff\xd8\xff'):
            return "image/jpeg"
        elif content.startswith(b'RIFF') and b'WEBP' in content[:20]:
            return "image/webp"
        elif content.startswith(b'GIF8'):
            return "image/gif"
        elif content.startswith(b'%PDF'):
            return "application/pdf"
        else:
            return "application/octet-stream"
    
    def _is_acceptable_mime_mismatch(self, declared: str, actual: str) -> bool:
        """Check if MIME mismatch is acceptable.
        
        Some mismatches are acceptable, like:
        - text/plain vs text/html (HTML can be plain text)
        - image/jpg vs image/jpeg (synonym)
        """
        acceptable_pairs = [
            ("text/plain", "text/html"),
            ("image/jpg", "image/jpeg"),
            ("application/octet-stream", actual),  # Generic binary can be anything
        ]
        
        for pair in acceptable_pairs:
            if (declared, actual) == pair or (actual, declared) == pair:
                return True
        
        return False
    
    def _scan_with_clamav(self, content: bytes) -> List[str]:
        """Scan content with ClamAV antivirus.
        
        Returns:
            List of detected threats, empty if clean
        """
        if not self.clamav_available:
            # In production, ClamAV must be available
            from ..core.config import settings
            if settings.service_env not in {"dev", "test", "development", "local"}:
                raise RuntimeError("ClamAV is required in production environment")
            logger.debug("ClamAV not available, skipping AV scan in non-prod env")
            return []
        
        threats = []
        
        # Write content to temporary file for scanning
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Run ClamAV scan
            result = subprocess.run(
                ["clamscan", "--no-summary", tmp_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse output for threats
            for line in result.stdout.split('\n'):
                if 'FOUND' in line and 'OK' not in line:
                    # Extract threat name
                    parts = line.split(':')
                    if len(parts) >= 2:
                        threat = parts[1].strip().replace(' FOUND', '')
                        threats.append(f"Malware detected: {threat}")
                        logger.warning(f"ClamAV detected threat: {threat}")
            
        except subprocess.TimeoutExpired:
            logger.error("ClamAV scan timed out")
        except Exception as e:
            logger.error(f"ClamAV scan failed: {e}")
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        
        return threats
    
    def _process_image_security(
        self,
        content: bytes,
        mime_type: str
    ) -> Tuple[bytes, bool]:
        """Process image for security, including EXIF stripping.
        
        Returns:
            Tuple of (processed_content, exif_was_removed)
        """
        if not self.pil_available:
            logger.debug("PIL not available, cannot process image EXIF")
            return content, False
        
        try:
            # Open image
            import io
            img = Image.open(io.BytesIO(content))
            
            # Check for EXIF data
            exif = img.getexif()
            has_exif = bool(exif)
            
            if has_exif:
                logger.info(f"Stripping EXIF data from {mime_type} image")
                
                # Create new image without EXIF
                # This preserves image quality but removes metadata
                data = list(img.getdata())
                image_without_exif = Image.new(img.mode, img.size)
                image_without_exif.putdata(data)
                
                # Save to bytes
                output = io.BytesIO()
                format_map = {
                    "image/jpeg": "JPEG",
                    "image/png": "PNG",
                    "image/webp": "WEBP",
                    "image/gif": "GIF"
                }
                save_format = format_map.get(mime_type, "PNG")
                image_without_exif.save(output, format=save_format)
                
                return output.getvalue(), True
            else:
                return content, False
                
        except Exception as e:
            logger.error(f"Failed to process image for EXIF: {e}")
            return content, False
    
    def quarantine_file(
        self,
        content: bytes,
        threat_info: Dict[str, Any]
    ) -> str:
        """Move infected file to quarantine.
        
        Returns:
            Quarantine path
        """
        # Generate quarantine path
        file_hash = threat_info.get("file_hash", hashlib.sha256(content).hexdigest())
        quarantine_path = f"quarantine/threats/{file_hash}"
        
        # Store file with threat metadata
        from ..services.storage_adapter import put_object
        metadata = {
            "threats": ",".join(threat_info.get("threats", [])),
            "scan_time": threat_info.get("scan_time", ""),
            "original_name": threat_info.get("filename", "unknown")
        }
        
        # Backend adapters may not support metadata; store bytes only
        put_object(quarantine_path, content)
        
        logger.warning(f"File quarantined: {quarantine_path}, threats: {metadata['threats']}")
        
        return quarantine_path


# Global scanner instance
_scanner: Optional[SecurityScanner] = None


def get_security_scanner() -> SecurityScanner:
    """Get the global security scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = SecurityScanner()
    return _scanner


def scan_upload(
    content: bytes,
    mime_type: Optional[str] = None,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """Scan uploaded content for security threats.
    
    Args:
        content: Raw file content
        mime_type: Declared MIME type
        filename: Original filename
        
    Returns:
        Dictionary with scan results
        
    Raises:
        HTTPException: If content is not safe
    """
    from fastapi import HTTPException
    
    scanner = get_security_scanner()
    result = scanner.scan_content(content, mime_type, filename)
    
    if not result.is_safe:
        # Quarantine the file
        quarantine_info = {
            "file_hash": result.file_hash,
            "threats": result.threats,
            "filename": filename
        }
        quarantine_path = scanner.quarantine_file(content, quarantine_info)
        
        # Raise exception with threat details
        raise HTTPException(
            status_code=400,
            detail={
                "error": "SecurityThreatDetected",
                "message": "File failed security scan",
                "threats": result.threats,
                "quarantine_path": quarantine_path
            }
        )
    
    return result.to_dict()


def strip_exif_from_image(image_bytes: bytes) -> bytes:
    """Strip EXIF metadata from an image.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Image bytes with EXIF removed
    """
    scanner = get_security_scanner()
    processed, _ = scanner._process_image_security(
        image_bytes,
        scanner._detect_mime_type(image_bytes)
    )
    return processed