from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

from ..models.schemas import RenderRequest
from .langfuse import Trace
from .redis import sha1key, cache_get_set
from .canon import derive_canon_from_project

logger = logging.getLogger(__name__)


@dataclass
class CanonEnforcementResult:
    enhanced_prompt: str
    enforced: bool
    violations: List[str]
    confidence_score: float

    def to_audit_dict(self) -> Dict[str, Any]:
        return asdict(self)


def enforce_brand_canon(request: RenderRequest, base_prompt: str, trace: Trace | None) -> CanonEnforcementResult:
    """Lightweight, deterministic prompt enhancer using provided constraints.

    This does not call external services. It appends explicit constraints to the
    prompt to bias the image model, and records basic policy notes.
    """
    constraints = []
    violations: List[str] = []

    if request.constraints and request.constraints.palette_hex:
        constraints.append(f"Palette: {', '.join(request.constraints.palette_hex)}")
    if request.constraints and request.constraints.fonts:
        constraints.append(f"Fonts: {', '.join(request.constraints.fonts)}")
    if request.constraints and request.constraints.logo_safe_zone_pct is not None:
        constraints.append(f"Logo safe zone: {request.constraints.logo_safe_zone_pct}%")

    # No actual validation against a stored canon here; just format constraints
    if constraints:
        enhanced = base_prompt + "\n" + "\n".join(constraints)
        enforced = True
    else:
        enhanced = base_prompt
        enforced = False

    # Confidence is heuristic: 1.0 if constraints present, else 0.5
    confidence = 1.0 if enforced else 0.5

    return CanonEnforcementResult(
        enhanced_prompt=enhanced,
        enforced=enforced,
        violations=violations,
        confidence_score=confidence,
    )




@dataclass
class CanonEnforcementResult:
    """Result of brand canon enforcement."""
    enforced: bool
    canon_used: Dict[str, Any]
    violations: List[str]
    enhanced_prompt: str
    confidence_score: float
    
    def to_audit_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for audit logging."""
        return {
            "canon_enforced": self.enforced,
            "violations_count": len(self.violations),
            "confidence_score": self.confidence_score,
            "canon_elements": list(self.canon_used.keys()) if self.canon_used else []
        }


class BrandCanonEnforcer:
    """Service for enforcing brand canon in AI-generated designs."""
    
    def __init__(self):
        self.enabled = True
        logger.info("Brand canon enforcer initialized")
    
    def enforce_canon_in_prompt(self, 
                               request: RenderRequest, 
                               base_prompt: str,
                               trace: Optional[Trace] = None) -> CanonEnforcementResult:
        """Enforce brand canon by enhancing the generation prompt.
        
        Args:
            request: The render request with constraints
            base_prompt: The base prompt for image generation
            trace: Optional tracing context
            
        Returns:
            CanonEnforcementResult: Enforcement result with enhanced prompt
        """
        if not self.enabled:
            logger.debug("Brand canon enforcement disabled")
            return CanonEnforcementResult(
                enforced=False,
                canon_used={},
                violations=[],
                enhanced_prompt=base_prompt,
                confidence_score=0.0
            )
        
        # Get project canon
        canon = self._get_project_canon(request.project_id, trace)
        
        # Merge request constraints with project canon
        merged_canon = self._merge_constraints_with_canon(request.constraints, canon)
        
        # Validate constraints against canon
        violations = self._validate_constraints_against_canon(request.constraints, canon)
        
        # Enhance prompt with canon enforcement
        enhanced_prompt = self._enhance_prompt_with_canon(base_prompt, merged_canon)
        
        # Calculate confidence score
        confidence = self._calculate_enforcement_confidence(merged_canon, violations)
        
        result = CanonEnforcementResult(
            enforced=True,
            canon_used=merged_canon,
            violations=violations,
            enhanced_prompt=enhanced_prompt,
            confidence_score=confidence
        )
        
        logger.info(f"Brand canon enforcement completed: {len(violations)} violations, "
                   f"confidence {confidence:.2f}")
        
        return result
    
    def _get_project_canon(self, project_id: str, trace: Optional[Trace] = None) -> Dict[str, Any]:
        """Get brand canon for a project with caching."""
        try:
            import json
            
            # Try cache first
            canon_key = sha1key("canon", project_id, "enforcement")
            
            def _canon_factory() -> bytes:
                canon = derive_canon_from_project(project_id, trace=trace)
                return json.dumps(canon).encode("utf-8")
            
            canon_bytes = cache_get_set(canon_key, _canon_factory, ttl=3600)  # 1 hour cache
            canon = json.loads(canon_bytes.decode("utf-8"))
            
            logger.debug(f"Retrieved canon for project {project_id}: {list(canon.keys())}")
            return canon
            
        except Exception as e:
            logger.warning(f"Failed to retrieve canon for project {project_id}: {e}")
            # Return default canon to ensure enforcement continues
            return self._get_default_canon()
    
    def _get_default_canon(self) -> Dict[str, Any]:
        """Get default brand canon when project canon is unavailable."""
        return {
            "palette_hex": ["#000000", "#FFFFFF", "#808080"],
            "fonts": ["Arial", "Helvetica", "sans-serif"],
            "voice": {
                "tone": "professional",
                "dos": ["Be clear", "Be concise", "Be consistent"],
                "donts": ["Avoid jargon", "Avoid clutter", "Avoid inconsistency"]
            },
            "logo_safe_zone_pct": 15.0,
            "style_guidelines": {
                "prefer_minimal": True,
                "avoid_gradients": False,
                "max_colors": 5
            }
        }
    
    def _merge_constraints_with_canon(self, 
                                    request_constraints: Optional[Any], 
                                    project_canon: Dict[str, Any]) -> Dict[str, Any]:
        """Merge request constraints with project canon, prioritizing canon."""
        merged = project_canon.copy()
        
        if not request_constraints:
            return merged
        
        # Convert constraints to dict if it's a Pydantic model
        if hasattr(request_constraints, 'model_dump'):
            constraints_dict = request_constraints.model_dump(exclude_none=True)
        else:
            constraints_dict = request_constraints or {}
        
        # Merge constraints, but canon takes precedence for core brand elements
        core_brand_elements = {"palette_hex", "fonts", "voice"}
        
        for key, value in constraints_dict.items():
            if key in core_brand_elements:
                # For core brand elements, validate against canon but don't override
                if key in merged:
                    logger.debug(f"Canon override: {key} from constraints ignored, using canon value")
                else:
                    merged[key] = value
            else:
                # For non-core elements, allow constraints to override
                merged[key] = value
        
        return merged
    
    def _validate_constraints_against_canon(self, 
                                          request_constraints: Optional[Any],
                                          project_canon: Dict[str, Any]) -> List[str]:
        """Validate request constraints against project canon."""
        violations = []
        
        if not request_constraints:
            return violations
        
        # Convert constraints to dict
        if hasattr(request_constraints, 'model_dump'):
            constraints_dict = request_constraints.model_dump(exclude_none=True)
        else:
            constraints_dict = request_constraints or {}
        
        # Validate palette colors
        if "palette_hex" in constraints_dict and "palette_hex" in project_canon:
            request_colors = set(constraints_dict["palette_hex"])
            canon_colors = set(project_canon["palette_hex"])
            
            # Check if request colors are subset of canon colors
            invalid_colors = request_colors - canon_colors
            if invalid_colors:
                violations.append(f"Colors not in brand palette: {', '.join(invalid_colors)}")
        
        # Validate fonts
        if "fonts" in constraints_dict and "fonts" in project_canon:
            request_fonts = set(constraints_dict["fonts"])
            canon_fonts = set(project_canon["fonts"])
            
            invalid_fonts = request_fonts - canon_fonts
            if invalid_fonts:
                violations.append(f"Fonts not in brand guidelines: {', '.join(invalid_fonts)}")
        
        # Validate logo safe zone
        if "logo_safe_zone_pct" in constraints_dict and "logo_safe_zone_pct" in project_canon:
            request_safe_zone = constraints_dict["logo_safe_zone_pct"]
            canon_safe_zone = project_canon["logo_safe_zone_pct"]
            
            if request_safe_zone < canon_safe_zone:
                violations.append(f"Logo safe zone {request_safe_zone}% below minimum {canon_safe_zone}%")
        
        return violations
    
    def _enhance_prompt_with_canon(self, base_prompt: str, canon: Dict[str, Any]) -> str:
        """Enhance the generation prompt with brand canon enforcement."""
        enhancement_parts = [base_prompt]
        
        # Add color palette enforcement
        if "palette_hex" in canon and canon["palette_hex"]:
            colors = ", ".join(canon["palette_hex"])
            enhancement_parts.append(f"STRICT COLOR PALETTE: Use ONLY these exact colors: {colors}")
        
        # Add font enforcement
        if "fonts" in canon and canon["fonts"]:
            fonts = ", ".join(canon["fonts"])
            enhancement_parts.append(f"TYPOGRAPHY: Use ONLY these approved fonts: {fonts}")
        
        # Add voice and tone guidance
        if "voice" in canon:
            voice = canon["voice"]
            if isinstance(voice, dict):
                if "tone" in voice:
                    enhancement_parts.append(f"BRAND TONE: Maintain {voice['tone']} tone throughout")
                
                if "dos" in voice and voice["dos"]:
                    dos = "; ".join(voice["dos"])
                    enhancement_parts.append(f"BRAND GUIDELINES - DO: {dos}")
                
                if "donts" in voice and voice["donts"]:
                    donts = "; ".join(voice["donts"])
                    enhancement_parts.append(f"BRAND GUIDELINES - AVOID: {donts}")
        
        # Add logo safe zone enforcement
        if "logo_safe_zone_pct" in canon:
            safe_zone = canon["logo_safe_zone_pct"]
            enhancement_parts.append(f"LOGO SAFE ZONE: Maintain {safe_zone}% clear space around logo placement")
        
        # Add style guidelines
        if "style_guidelines" in canon:
            style = canon["style_guidelines"]
            if isinstance(style, dict):
                if style.get("prefer_minimal"):
                    enhancement_parts.append("STYLE: Prefer clean, minimal design approach")
                
                if style.get("avoid_gradients"):
                    enhancement_parts.append("STYLE: Avoid gradients, use solid colors only")
                
                if "max_colors" in style:
                    enhancement_parts.append(f"COLOR LIMIT: Use maximum {style['max_colors']} colors")
        
        # Add enforcement emphasis
        enhancement_parts.append("CRITICAL: Strictly adhere to ALL brand guidelines above. Any deviation from brand canon is unacceptable.")
        
        enhanced_prompt = "\n\n".join(enhancement_parts)
        
        logger.debug(f"Enhanced prompt length: {len(enhanced_prompt)} chars (added {len(enhanced_prompt) - len(base_prompt)})")
        
        return enhanced_prompt
    
    def _calculate_enforcement_confidence(self, canon: Dict[str, Any], violations: List[str]) -> float:
        """Calculate confidence score for canon enforcement."""
        # Base confidence starts high
        confidence = 0.9
        
        # Reduce confidence for each violation
        confidence -= len(violations) * 0.1
        
        # Boost confidence for comprehensive canon
        canon_elements = len([k for k in ["palette_hex", "fonts", "voice", "logo_safe_zone_pct"] 
                             if k in canon and canon[k]])
        confidence += canon_elements * 0.025
        
        # Ensure confidence stays in valid range
        return max(0.0, min(1.0, confidence))
    
    def validate_generated_output(self, 
                                 image_data: bytes, 
                                 canon: Dict[str, Any],
                                 trace: Optional[Trace] = None) -> Dict[str, Any]:
        """Validate generated image against brand canon (future implementation).
        
        Args:
            image_data: Generated image bytes
            canon: Brand canon to validate against
            trace: Optional tracing context
            
        Returns:
            Dict: Validation results
            
        Note:
            Real image analysis implementation using computer vision.
            Would integrate with computer vision models to analyze:
            - Color palette compliance
            - Font usage detection
            - Logo placement validation
            - Style guideline adherence
        """
        try:
            import cv2
            import numpy as np
            from PIL import Image
            import io
            
            # Convert bytes to image
            image = Image.open(io.BytesIO(image_data))
            image_array = np.array(image)
            
            violations = []
            
            # Extract dominant colors from image
            pixels = image_array.reshape(-1, 3)
            from sklearn.cluster import KMeans
            
            # Get 5 dominant colors
            kmeans = KMeans(n_clusters=5, random_state=42)
            kmeans.fit(pixels)
            dominant_colors = kmeans.cluster_centers_
            
            # Check color palette compliance
            if canon.get("palette_hex"):
                canon_colors = []
                for hex_color in canon["palette_hex"]:
                    # Convert hex to RGB
                    hex_color = hex_color.lstrip('#')
                    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    canon_colors.append(rgb)
                
                # Check if dominant colors are close to canon colors
                for dom_color in dominant_colors:
                    min_distance = float('inf')
                    for canon_color in canon_colors:
                        distance = np.linalg.norm(dom_color - np.array(canon_color))
                        min_distance = min(min_distance, distance)
                    
                    # If color is too far from any canon color
                    if min_distance > 50:  # Threshold for color similarity
                        violations.append(f"Non-canon color detected: RGB{tuple(dom_color.astype(int))}")
            
            # Check image dimensions for logo safe zones
            if canon.get("logo_safe_zone_pct"):
                height, width = image_array.shape[:2]
                safe_zone_pct = canon["logo_safe_zone_pct"]
                
                # This is a simplified check - in reality would need logo detection
                logger.info(f"Image dimensions: {width}x{height}, safe zone: {safe_zone_pct}%")
            
            return {
                "validation_performed": True,
                "violations": violations,
                "dominant_colors": [tuple(color.astype(int)) for color in dominant_colors],
                "compliance_score": max(0, 1 - len(violations) * 0.2)
            }
            
        except ImportError as e:
            logger.error(f"Image analysis dependencies not installed: {e}")
            raise ImportError(
                "Image analysis requires: pip install opencv-python pillow scikit-learn"
            )
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            return {
                "validation_performed": False,
                "reason": "not yet implemented",
                "error": str(e),
                "violations": ["Image analysis failed"],
                "future_capabilities": [
                    "palette_compliance",
                    "font_detection",
                    "logo_safe_zone",
                    "style_guidelines"
                ]
            }


# Global enforcer instance
_enforcer: Optional[BrandCanonEnforcer] = None


def get_brand_canon_enforcer() -> BrandCanonEnforcer:
    """Get the global brand canon enforcer instance."""
    global _enforcer
    if _enforcer is None:
        _enforcer = BrandCanonEnforcer()
    return _enforcer


def enforce_brand_canon(request: RenderRequest, 
                       base_prompt: str,
                       trace: Optional[Trace] = None) -> CanonEnforcementResult:
    """Convenience function to enforce brand canon in design generation.
    
    Args:
        request: The render request with constraints
        base_prompt: The base prompt for image generation
        trace: Optional tracing context
        
    Returns:
        CanonEnforcementResult: Enforcement result with enhanced prompt
    """
    enforcer = get_brand_canon_enforcer()
    return enforcer.enforce_canon_in_prompt(request, base_prompt, trace)
