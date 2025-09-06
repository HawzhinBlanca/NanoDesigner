"""Pydantic models for API request and response schemas.

This module defines all the data models used by the Smart Graphic Designer API,
including request models, response models, and nested component models.
Each model includes proper validation, documentation, and examples.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from enum import Enum

class TaskType(str, Enum):
    """Available task types for render requests."""
    CREATE = "create"
    EDIT = "edit" 
    VARIATIONS = "variations"

class ImageFormat(str, Enum):
    """Supported image formats for outputs."""
    PNG = "png"
    JPG = "jpg"
    WEBP = "webp"

class RenderRequestPrompts(BaseModel):
    """Prompt configuration for render requests."""
    
    task: TaskType = Field(
        ...,
        description="Type of design task to perform",
        example="create"
    )
    instruction: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Detailed instruction for the design task",
        example="Create a modern banner for a tech startup with blue color scheme"
    )
    references: Optional[List[str]] = Field(
        None,
        max_items=8,
        description="List of reference image URLs (HTTPS only)",
        example=["https://example.com/logo.png", "https://example.com/inspiration.jpg"]
    )
    
    @validator('references')
    def validate_references(cls, v):
        """Validate that all references are HTTPS URLs."""
        if v:
            from urllib.parse import urlparse
            for ref in v:
                parsed = urlparse(ref)
                if parsed.scheme and parsed.scheme != 'https':
                    raise ValueError(f'Reference URL must use HTTPS: {ref}')
        return v

class RenderRequestOutputs(BaseModel):
    """Output configuration for render requests."""
    
    count: int = Field(
        ...,
        ge=1,
        le=6,
        description="Number of image variations to generate",
        example=2
    )
    format: ImageFormat = Field(
        ...,
        description="Output image format",
        example="png"
    )
    dimensions: str = Field(
        ...,
        pattern=r'^[0-9]{2,5}x[0-9]{2,5}$',
        description="Image dimensions in WIDTHxHEIGHT format",
        example="1024x768"
    )
    
    @validator('dimensions')
    def validate_dimensions(cls, v):
        """Validate dimension constraints."""
        try:
            width, height = map(int, v.split('x'))
            if width * height > 4096 * 4096:
                raise ValueError('Image dimensions too large (max 16MP)')
            if width < 64 or height < 64:
                raise ValueError('Image dimensions too small (min 64px)')
        except ValueError as e:
            if 'too large' in str(e) or 'too small' in str(e):
                raise e
            raise ValueError('Invalid dimension format, use WIDTHxHEIGHT')
        return v

class RenderRequestConstraints(BaseModel):
    """Brand constraints and guidelines for render requests."""
    
    palette_hex: Optional[List[str]] = Field(
        None,
        max_items=12,
        description="Brand color palette as hex codes",
        example=["#1E3A8A", "#FFFFFF", "#F59E0B"]
    )
    fonts: Optional[List[str]] = Field(
        None,
        max_items=6,
        description="Preferred font families to use",
        example=["Inter", "Roboto", "Helvetica"]
    )
    logo_safe_zone_pct: Optional[float] = Field(
        None,
        ge=0,
        le=40,
        description="Logo safe zone as percentage of total area",
        example=15.0
    )
    
    @validator('palette_hex')
    def validate_hex_colors(cls, v):
        """Validate hex color format."""
        if v:
            import re
            hex_pattern = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
            for color in v:
                if not hex_pattern.match(color):
                    raise ValueError(f'Invalid hex color format: {color}')
        return v

class RenderRequest(BaseModel):
    """Complete render request with prompts, outputs, and constraints."""
    
    project_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique identifier for the project",
        example="my-startup-campaign"
    )
    prompts: RenderRequestPrompts = Field(
        ...,
        description="Design prompts and instructions"
    )
    outputs: RenderRequestOutputs = Field(
        ...,
        description="Output format and count specifications"
    )
    constraints: Optional[RenderRequestConstraints] = Field(
        None,
        description="Brand guidelines and design constraints"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "project_id": "startup-banner-2024",
                "prompts": {
                    "task": "create",
                    "instruction": "Create a modern banner for a tech startup with clean typography and professional look",
                    "references": ["https://example.com/brand-guide.pdf"]
                },
                "outputs": {
                    "count": 3,
                    "format": "png",
                    "dimensions": "1200x630"
                },
                "constraints": {
                    "palette_hex": ["#1E3A8A", "#FFFFFF", "#F59E0B"],
                    "fonts": ["Inter", "Roboto"],
                    "logo_safe_zone_pct": 20.0
                }
            }
        }

class SynthID(BaseModel):
    """SynthID watermarking information for generated images."""
    
    present: bool = Field(
        ...,
        description="Whether SynthID watermark is present in the image",
        example=True
    )
    payload: str = Field(
        ...,
        description="SynthID payload data (empty if not present)",
        example=""
    )

class Asset(BaseModel):
    """Generated asset information with URLs and metadata."""
    
    url: str = Field(
        ...,
        description="Signed URL for accessing the generated asset",
        example="https://cdn.example.com/assets/generated-image.png?signature=abc123"
    )
    r2_key: str = Field(
        ...,
        description="Internal storage key for the asset",
        example="public/startup-banner-2024/550e8400-e29b-41d4-a716-446655440000.png"
    )
    synthid: Optional[SynthID] = Field(
        None,
        description="SynthID watermarking information"
    )

class Audit(BaseModel):
    """Audit trail and metadata for render operations."""
    
    trace_id: str = Field(
        ...,
        description="Unique trace ID for observability",
        example="trace_550e8400e29b41d4a716446655440000"
    )
    model_route: str = Field(
        ...,
        description="AI model route used for generation",
        example="openrouter/gemini-2.5-flash-image"
    )
    cost_usd: float = Field(
        ...,
        ge=0,
        description="Estimated cost in USD for the operation",
        example=0.05
    )
    guardrails_ok: bool = Field(
        ...,
        description="Whether all guardrails validations passed",
        example=True
    )
    verified_by: Literal['declared', 'external', 'none'] = Field(
        'declared',
        description="SynthID verification provenance: declared | external | none",
        example='declared'
    )

class RenderResponse(BaseModel):
    """Response containing generated assets and audit information."""
    
    assets: List[Asset] = Field(
        ...,
        description="List of generated assets with access URLs",
        min_items=1
    )
    audit: Audit = Field(
        ...,
        description="Audit trail and operation metadata"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "assets": [
                    {
                        "url": "https://cdn.example.com/public/startup-banner.png?expires=1640995200",
                        "r2_key": "public/startup-banner-2024/image-001.png",
                        "synthid": {
                            "present": True,
                            "payload": ""
                        }
                    }
                ],
                "audit": {
                    "trace_id": "trace_abc123def456",
                    "model_route": "openrouter/gemini-2.5-flash-image",
                    "cost_usd": 0.05,
                    "guardrails_ok": True,
                    "verified_by": "declared"
                }
            }
        }


# Ingest
class IngestRequest(BaseModel):
    project_id: str
    assets: List[str] = Field(..., max_items=50)


class IngestResponse(BaseModel):
    processed: int
    qdrant_ids: List[str]


# Canon
class CanonDeriveRequest(BaseModel):
    project_id: str
    evidence_ids: List[str]


class CanonDeriveResponse(BaseModel):
    palette_hex: List[str]
    fonts: List[str]
    class Voice(BaseModel):
        tone: str
        dos: Optional[List[str]] = None
        donts: Optional[List[str]] = None
    voice: Voice


# Critique
class CritiqueRequest(BaseModel):
    project_id: str
    asset_ids: List[str] = Field(..., max_items=10)


class CritiqueResponse(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    violations: List[str]
    repair_suggestions: List[str]
