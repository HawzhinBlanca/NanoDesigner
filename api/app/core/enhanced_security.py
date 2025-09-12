"""Enhanced security module for Week 2 - Production-grade content policy and validation."""

import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import magic
from fastapi import HTTPException, status


class ThreatLevel(Enum):
    """Threat level classification."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    BLOCKED = "blocked"


@dataclass
class SecurityScanResult:
    """Result of security scanning."""
    threat_level: ThreatLevel
    confidence: float
    reasons: List[str]
    sanitized_content: Optional[str] = None
    metadata: Dict[str, Any] = None


class ContentPolicyEngine:
    """Production-grade content policy enforcement engine."""
    
    def __init__(self, policy_file: Optional[str] = None):
        self.policy_file = policy_file or "policies/content_policy.json"
        self.load_policies()
        
        # Compile regex patterns for performance
        self._compiled_patterns = {}
        self._compile_patterns()
    
    def load_policies(self):
        """Load content policies from configuration."""
        try:
            policy_path = Path(__file__).parent.parent.parent / self.policy_file
            if policy_path.exists():
                with open(policy_path, 'r') as f:
                    self.policies = json.load(f)
            else:
                # Default policies if file doesn't exist
                self.policies = self._get_default_policies()
        except Exception as e:
            print(f"Warning: Failed to load content policies: {e}")
            self.policies = self._get_default_policies()
    
    def _get_default_policies(self) -> Dict[str, Any]:
        """Get default content policies."""
        return {
            "blocked_terms": [
                # Explicit content
                "explicit", "nsfw", "adult", "pornographic",
                # Violence
                "violence", "weapon", "bomb", "kill", "murder",
                # Hate speech
                "hate", "racist", "nazi", "terrorist",
                # Illegal activities
                "drug", "illegal", "piracy", "fraud",
                # Malware/Security
                "malware", "virus", "trojan", "backdoor", "exploit"
            ],
            "suspicious_patterns": [
                r"<script[^>]*>.*?</script>",  # JavaScript injection
                r"javascript:",  # JavaScript URLs
                r"data:.*base64",  # Base64 data URLs
                r"eval\s*\(",  # Code evaluation
                r"exec\s*\(",  # Code execution
                r"\.\./",  # Path traversal
                r"file://",  # File protocol
                r"ftp://",  # FTP protocol
            ],
            "allowed_domains": [
                "example.com", "trusted-domain.com", "api.openai.com"
            ],
            "max_content_length": 50000,
            "max_url_length": 2048,
            "allowed_file_types": [
                ".jpg", ".jpeg", ".png", ".gif", ".webp",
                ".pdf", ".txt", ".md", ".json", ".csv"
            ],
            "max_file_size": 10 * 1024 * 1024,  # 10MB
        }
    
    def _compile_patterns(self):
        """Compile regex patterns for performance."""
        for pattern in self.policies.get("suspicious_patterns", []):
            try:
                self._compiled_patterns[pattern] = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            except re.error as e:
                print(f"Warning: Invalid regex pattern '{pattern}': {e}")
    
    def scan_text_content(self, content: str) -> SecurityScanResult:
        """Scan text content for policy violations."""
        reasons = []
        threat_level = ThreatLevel.SAFE
        confidence = 0.0
        
        # Check content length
        if len(content) > self.policies.get("max_content_length", 50000):
            reasons.append(f"Content too long: {len(content)} chars")
            threat_level = ThreatLevel.SUSPICIOUS
            confidence = max(confidence, 0.7)
        
        # Check for blocked terms
        content_lower = content.lower()
        blocked_terms = self.policies.get("blocked_terms", [])
        found_blocked = [term for term in blocked_terms if term.lower() in content_lower]
        
        if found_blocked:
            reasons.append(f"Blocked terms found: {', '.join(found_blocked)}")
            threat_level = ThreatLevel.BLOCKED
            confidence = 1.0
        
        # Check suspicious patterns
        for pattern_str, compiled_pattern in self._compiled_patterns.items():
            if compiled_pattern.search(content):
                reasons.append(f"Suspicious pattern: {pattern_str}")
                if threat_level == ThreatLevel.SAFE:
                    threat_level = ThreatLevel.SUSPICIOUS
                confidence = max(confidence, 0.8)
        
        # Sanitize content if needed
        sanitized_content = None
        if threat_level in [ThreatLevel.SUSPICIOUS, ThreatLevel.SAFE]:
            sanitized_content = self._sanitize_text(content)
        
        return SecurityScanResult(
            threat_level=threat_level,
            confidence=confidence,
            reasons=reasons,
            sanitized_content=sanitized_content
        )
    
    def _sanitize_text(self, content: str) -> str:
        """Sanitize text content."""
        import html
        
        # HTML escape
        content = html.escape(content)
        
        # Remove suspicious patterns
        for pattern_str, compiled_pattern in self._compiled_patterns.items():
            content = compiled_pattern.sub("[REMOVED]", content)
        
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def scan_file_content(self, file_content: bytes, filename: str) -> SecurityScanResult:
        """Scan file content for policy violations with deep content inspection."""
        reasons = []
        threat_level = ThreatLevel.SAFE
        confidence = 0.0
        
        # Check file size
        if len(file_content) > self.policies.get("max_file_size", 10 * 1024 * 1024):
            reasons.append(f"File too large: {len(file_content)} bytes")
            threat_level = ThreatLevel.BLOCKED
            confidence = 1.0
            return SecurityScanResult(threat_level, confidence, reasons)
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        allowed_types = self.policies.get("allowed_file_types", [])
        if file_ext not in allowed_types:
            reasons.append(f"File type not allowed: {file_ext}")
            threat_level = ThreatLevel.BLOCKED
            confidence = 1.0
            return SecurityScanResult(threat_level, confidence, reasons)
        
        # Deep MIME type validation with multiple checks
        try:
            # Primary MIME detection
            mime_type = magic.from_buffer(file_content, mime=True)
            
            # Secondary validation: Check magic bytes directly
            if not self._validate_magic_bytes(file_content, file_ext):
                reasons.append(f"Magic bytes validation failed for {file_ext}")
                threat_level = ThreatLevel.BLOCKED
                confidence = 0.95
                return SecurityScanResult(threat_level, confidence, reasons)
            
            # Check MIME type against expected
            if not self._is_mime_type_allowed(mime_type, file_ext):
                # Perform deep content scan for suspicious files
                if self._deep_scan_file_content(file_content, mime_type, file_ext):
                    reasons.append(f"Deep scan passed despite MIME mismatch: {mime_type} for {file_ext}")
                    threat_level = ThreatLevel.SUSPICIOUS
                    confidence = 0.6
                else:
                    reasons.append(f"MIME type validation failed: {mime_type} for {file_ext}")
                    threat_level = ThreatLevel.BLOCKED
                    confidence = 0.9
                    return SecurityScanResult(threat_level, confidence, reasons)
        except Exception as e:
            reasons.append(f"MIME type detection failed: {e}")
            threat_level = ThreatLevel.SUSPICIOUS
            confidence = 0.6
        
        # Check for embedded executables (basic check)
        if self._contains_executable_signatures(file_content):
            reasons.append("Contains executable signatures")
            threat_level = ThreatLevel.MALICIOUS
            confidence = 0.9
        
        # Calculate file hash for tracking
        file_hash = hashlib.sha256(file_content).hexdigest()
        metadata = {"file_hash": file_hash, "file_size": len(file_content)}
        
        return SecurityScanResult(
            threat_level=threat_level,
            confidence=confidence,
            reasons=reasons,
            metadata=metadata
        )
    
    def _is_mime_type_allowed(self, mime_type: str, file_ext: str) -> bool:
        """Check if MIME type matches expected type for file extension."""
        expected_mime_types = {
            '.jpg': ['image/jpeg', 'image/jpg'],
            '.jpeg': ['image/jpeg', 'image/jpg'],
            '.png': ['image/png'],
            '.gif': ['image/gif'],
            '.webp': ['image/webp'],
            '.svg': ['image/svg+xml', 'text/xml'],
            '.pdf': ['application/pdf'],
            '.txt': ['text/plain', 'application/octet-stream'],
            '.md': ['text/markdown', 'text/plain', 'text/x-markdown'],
            '.json': ['application/json', 'text/plain', 'text/json'],
            '.csv': ['text/csv', 'text/plain', 'application/csv']
        }
        
        expected = expected_mime_types.get(file_ext, [])
        return not expected or mime_type in expected
    
    def _validate_magic_bytes(self, content: bytes, file_ext: str) -> bool:
        """Validate file content against known magic bytes for the extension."""
        # Define magic bytes for common file types
        magic_bytes = {
            '.jpg': [b'\xff\xd8\xff'],
            '.jpeg': [b'\xff\xd8\xff'],
            '.png': [b'\x89PNG\r\n\x1a\n'],
            '.gif': [b'GIF87a', b'GIF89a'],
            '.pdf': [b'%PDF'],
            '.webp': [b'RIFF', b'WEBP'],
            '.svg': [b'<svg', b'<?xml'],
        }
        
        expected_magic = magic_bytes.get(file_ext, [])
        if not expected_magic:
            # No magic bytes defined for this type, pass validation
            return True
        
        # Check if content starts with any of the expected magic bytes
        for magic in expected_magic:
            if content.startswith(magic):
                return True
        
        # Special case for WebP (needs both RIFF and WEBP)
        if file_ext == '.webp':
            return content.startswith(b'RIFF') and b'WEBP' in content[:20]
        
        return False
    
    def _deep_scan_file_content(self, content: bytes, mime_type: str, file_ext: str) -> bool:
        """Perform deep content analysis to validate file safety.
        
        Returns True if file passes deep scan despite MIME mismatch.
        """
        # Check for embedded executables
        if self._contains_executable_signatures(content):
            return False
        
        # Check for suspicious patterns in content
        suspicious_patterns = [
            b'<script',  # JavaScript in files
            b'javascript:',  # JavaScript URLs
            b'eval(',  # Code evaluation
            b'exec(',  # Code execution
            b'<?php',  # PHP code
            b'<%',  # ASP/JSP code
        ]
        
        for pattern in suspicious_patterns:
            if pattern in content[:10000]:  # Check first 10KB
                return False
        
        # Additional checks for specific file types
        if file_ext in ['.svg', '.xml']:
            # SVG/XML specific checks
            if b'<!ENTITY' in content or b'<!DOCTYPE' in content:
                # Check for XXE attack patterns
                if b'SYSTEM' in content or b'file://' in content:
                    return False
        
        if file_ext in ['.pdf']:
            # PDF specific checks
            if b'/JavaScript' in content or b'/JS' in content:
                return False
        
        return True
    
    def _contains_executable_signatures(self, content: bytes) -> bool:
        """Check for common executable file signatures with enhanced detection."""
        # PE header (Windows executables)
        if content.startswith(b'MZ'):
            # Additional PE validation
            if len(content) > 0x3c + 4:
                pe_offset = int.from_bytes(content[0x3c:0x3c+4], 'little')
                if len(content) > pe_offset + 4:
                    if content[pe_offset:pe_offset+4] == b'PE\x00\x00':
                        return True
            return True  # Conservative: treat as executable if starts with MZ
        
        # ELF header (Linux executables)
        if content.startswith(b'\x7fELF'):
            return True
        
        # Mach-O header (macOS executables)
        mach_o_headers = [
            b'\xfe\xed\xfa\xce',  # Mach-O 32-bit big endian
            b'\xfe\xed\xfa\xcf',  # Mach-O 64-bit big endian
            b'\xce\xfa\xed\xfe',  # Mach-O 32-bit little endian
            b'\xcf\xfa\xed\xfe',  # Mach-O 64-bit little endian
        ]
        for header in mach_o_headers:
            if content.startswith(header):
                return True
        
        # Shell script indicators
        if content.startswith(b'#!/'):
            return True
        
        # Windows batch files
        if content.lower().startswith(b'@echo off'):
            return True
        
        # Java class files
        if content.startswith(b'\xca\xfe\xba\xbe'):
            return True
        
        # Python compiled files
        if content.startswith(b'\x03\xf3\r\n') or content.startswith(b'o\r\r\n'):
            return True
        
        return False


class URLValidator:
    """Validate and sanitize URLs."""
    
    def __init__(self, allowed_domains: Optional[List[str]] = None):
        self.allowed_domains = set(allowed_domains or [])
        self.blocked_schemes = {'javascript', 'data', 'file', 'ftp'}
    
    def validate_url(self, url: str) -> SecurityScanResult:
        """Validate URL for security issues."""
        reasons = []
        threat_level = ThreatLevel.SAFE
        confidence = 0.0
        
        # Check URL length
        if len(url) > 2048:
            reasons.append(f"URL too long: {len(url)} chars")
            threat_level = ThreatLevel.SUSPICIOUS
            confidence = 0.7
        
        # Parse URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme.lower() in self.blocked_schemes:
                reasons.append(f"Blocked URL scheme: {parsed.scheme}")
                threat_level = ThreatLevel.BLOCKED
                confidence = 1.0
            
            # Check domain if whitelist is configured
            if self.allowed_domains and parsed.netloc:
                domain_allowed = any(
                    parsed.netloc.endswith(domain) 
                    for domain in self.allowed_domains
                )
                if not domain_allowed:
                    reasons.append(f"Domain not in allowlist: {parsed.netloc}")
                    threat_level = ThreatLevel.SUSPICIOUS
                    confidence = 0.8
            
            # Check for suspicious patterns in URL
            suspicious_patterns = [
                r'\.\./', r'%2e%2e%2f', r'%252e%252e%252f',  # Path traversal
                r'<script', r'%3cscript',  # Script injection
            ]
            
            # Check for dangerous schemes (these should be blocked, not just suspicious)
            dangerous_scheme_patterns = [
                r'javascript:', r'data:', r'file:',  # Dangerous schemes
            ]
            
            for pattern in dangerous_scheme_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    reasons.append(f"Dangerous URL scheme pattern: {pattern}")
                    threat_level = ThreatLevel.BLOCKED
                    confidence = 1.0
            
            for pattern in suspicious_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    reasons.append(f"Suspicious URL pattern: {pattern}")
                    if threat_level == ThreatLevel.SAFE:
                        threat_level = ThreatLevel.SUSPICIOUS
                    confidence = max(confidence, 0.8)
            
        except Exception as e:
            reasons.append(f"URL parsing failed: {e}")
            threat_level = ThreatLevel.SUSPICIOUS
            confidence = 0.6
        
        return SecurityScanResult(
            threat_level=threat_level,
            confidence=confidence,
            reasons=reasons,
            sanitized_content=url if threat_level != ThreatLevel.BLOCKED else None
        )


class EnhancedSecurityManager:
    """Main security manager coordinating all security checks."""
    
    def __init__(self, policy_file: Optional[str] = None):
        self.content_policy = ContentPolicyEngine(policy_file)
        # Allowed domains from settings, fallback to policy
        try:
            from ..core.config import settings
            allow_env = settings.ref_url_allow_hosts or ""
            allowed_domains = [d.strip() for d in allow_env.split(",") if d.strip()] or self.content_policy.policies.get("allowed_domains", [])
        except Exception:
            allowed_domains = self.content_policy.policies.get("allowed_domains", [])
        self.url_validator = URLValidator(allowed_domains)
    
    def scan_render_request(self, instruction: str, references: List[str] = None) -> SecurityScanResult:
        """Comprehensive security scan for render requests."""
        all_reasons = []
        max_threat_level = ThreatLevel.SAFE
        max_confidence = 0.0
        
        # Scan instruction text
        instruction_result = self.content_policy.scan_text_content(instruction)
        all_reasons.extend([f"Instruction: {r}" for r in instruction_result.reasons])
        
        # Update threat level using enum comparison
        threat_levels = [ThreatLevel.SAFE, ThreatLevel.SUSPICIOUS, ThreatLevel.MALICIOUS, ThreatLevel.BLOCKED]
        if threat_levels.index(instruction_result.threat_level) > threat_levels.index(max_threat_level):
            max_threat_level = instruction_result.threat_level
        max_confidence = max(max_confidence, instruction_result.confidence)
        
        # Scan references (URLs)
        if references:
            for ref in references:
                ref_result = self.url_validator.validate_url(ref)
                all_reasons.extend([f"Reference {ref}: {r}" for r in ref_result.reasons])
                if threat_levels.index(ref_result.threat_level) > threat_levels.index(max_threat_level):
                    max_threat_level = ref_result.threat_level
                max_confidence = max(max_confidence, ref_result.confidence)
        
        # If we found blocked terms, escalate to BLOCKED
        if any("Blocked terms found" in reason for reason in all_reasons):
            max_threat_level = ThreatLevel.BLOCKED
            max_confidence = 1.0
        
        # Create combined result
        return SecurityScanResult(
            threat_level=max_threat_level,
            confidence=max_confidence,
            reasons=all_reasons,
            sanitized_content=instruction_result.sanitized_content
        )
    
    def scan_file_upload(self, file_content: bytes, filename: str) -> SecurityScanResult:
        """Comprehensive security scan for file uploads."""
        return self.content_policy.scan_file_content(file_content, filename)
    
    def enforce_policy(self, scan_result: SecurityScanResult, operation: str = "request"):
        """Enforce security policy based on scan results."""
        if scan_result.threat_level == ThreatLevel.BLOCKED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Content blocked by security policy",
                    "operation": operation,
                    "reasons": scan_result.reasons,
                    "threat_level": scan_result.threat_level.value,
                    "confidence": scan_result.confidence
                }
            )
        
        if scan_result.threat_level == ThreatLevel.MALICIOUS:
            # Log security incident
            print(f"🚨 SECURITY ALERT: Malicious content detected in {operation}")
            print(f"   Reasons: {', '.join(scan_result.reasons)}")
            print(f"   Confidence: {scan_result.confidence}")
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Malicious content detected",
                    "operation": operation,
                    "threat_level": scan_result.threat_level.value
                }
            )
        
        if scan_result.threat_level == ThreatLevel.SUSPICIOUS:
            # Log warning but allow with sanitization
            print(f"⚠️  SECURITY WARNING: Suspicious content in {operation}")
            print(f"   Reasons: {', '.join(scan_result.reasons)}")
            print(f"   Confidence: {scan_result.confidence}")
            
            # Could implement additional logging/monitoring here
        
        return scan_result.sanitized_content or "Content sanitized"


# Global security manager instance
security_manager = EnhancedSecurityManager()


def scan_and_enforce(content: str, content_type: str = "text") -> str:
    """Convenience function for scanning and enforcing security policies."""
    # Validate inputs
    if not isinstance(content, str):
        raise ValueError(f"Content must be a string, got {type(content).__name__}")
    
    if not isinstance(content_type, str):
        raise ValueError(f"Content type must be a string, got {type(content_type).__name__}")
    
    # Handle supported content types
    if content_type == "text":
        result = security_manager.content_policy.scan_text_content(content)
    elif content_type == "url":
        result = security_manager.url_validator.validate_url(content)
    elif content_type.startswith("file:"):
        # Extract filename from content_type (e.g., "file:example.pdf")
        filename = content_type.split(":", 1)[1] if ":" in content_type else "unknown"
        if isinstance(content, str):
            # If content is a string, convert to bytes for file scanning
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content
        result = security_manager.content_policy.scan_file_content(content_bytes, filename)
    else:
        # Log unsupported content type for monitoring
        logger.warning(f"Unsupported content type for security scan: {content_type}")
        raise ValueError(f"Unsupported content type: {content_type}. Supported types: text, url, file:<filename>")
    
    security_manager.enforce_policy(result, f"{content_type}_content")
    return result.sanitized_content or content
