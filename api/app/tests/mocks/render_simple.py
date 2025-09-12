"""Simplified render endpoint that bypasses Pydantic V2 issues."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import json
import uuid
import time
from typing import Dict, Any

from ..services.mock_openrouter import mock_call_task
from ..services.mock_image_generation import mock_call_openrouter_images
from ..core.enhanced_security import security_manager
from ..core.standardized_errors import StandardErrors

router = APIRouter()


@router.post("/render/simple")
@router.post("/render")  # Make this the primary render endpoint
async def render_simple(request: Request) -> JSONResponse:
    """
    Simplified render endpoint that bypasses Pydantic V2 issues.
    
    Accepts raw JSON and processes it manually to avoid forward reference issues.
    """
    try:
        # Get raw JSON body
        body = await request.json()
        
        # Basic validation
        if not isinstance(body, dict):
            return StandardErrors.validation_error("Request body must be a JSON object").to_json_response()
        
        # Extract required fields
        project_id = body.get("project_id", f"simple-{uuid.uuid4().hex[:8]}")
        prompts = body.get("prompts", {})
        outputs = body.get("outputs", {})
        
        instruction = prompts.get("instruction", "")
        if not instruction or len(instruction.strip()) < 3:
            return StandardErrors.validation_error(
                "Instruction is required and must be at least 3 characters", 
                field="prompts.instruction"
            ).to_json_response()
        
        count = outputs.get("count", 1)
        format_type = outputs.get("format", "png")
        dimensions = outputs.get("dimensions", "512x512")
        
        # Security scanning
        try:
            security_result = security_manager.scan_render_request(
                instruction=instruction,
                references=prompts.get("references", [])
            )
            security_manager.enforce_policy(security_result, "render_request")
            
            # Use sanitized content if available
            if security_result.sanitized_content:
                instruction = security_result.sanitized_content
                
        except Exception as e:
            return StandardErrors.security_policy_error(
                "content_validation", 
                details=str(e)
            ).to_json_response()
        
        # Generate plan using mock AI
        start_time = time.time()
        
        try:
            planner_response = await mock_call_task(
                "planner",
                [
                    {"role": "system", "content": "You are a design planner. Return valid JSON."},
                    {"role": "user", "content": f"Create a design plan for: {instruction}"}
                ]
            )
            
            plan_content = planner_response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Parse the plan JSON
            try:
                plan = json.loads(plan_content)
            except json.JSONDecodeError:
                # Fallback plan if JSON parsing fails
                plan = {
                    "goal": f"Create design for: {instruction}",
                    "ops": ["local_edit"],
                    "safety": {"respect_logo_safe_zone": True, "palette_only": False}
                }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI planning failed: {str(e)}")
        
        # Generate images using mock service
        try:
            image_response = mock_call_openrouter_images(
                model="mock/image-generator",
                prompt=instruction,
                n=count,
                size=dimensions
            )
            
            images = []
            for img_data in image_response.get("data", []):
                images.append({
                    "url": img_data.get("url", ""),
                    "format": format_type,
                    "dimensions": dimensions,
                    "verified_by": "mock-synthid"
                })
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Build response
        response_data = {
            "render_id": f"render_{uuid.uuid4().hex}",
            "project_id": project_id,
            "status": "completed",
            "images": images,
            "plan": plan,
            "cost_info": {
                "total_cost_usd": 0.001,
                "breakdown": {
                    "planner": 0.0005,
                    "image_generation": 0.0005
                }
            },
            "processing_time_ms": processing_time,
            "security_scan": {
                "threat_level": str(security_result.threat_level),
                "confidence": float(security_result.confidence)
            },
            "metadata": {
                "model_used": "mock/gpt-3.5-turbo",
                "image_model": "mock/image-generator",
                "api_version": "simple-v1"
            }
        }
        
        return JSONResponse(content=response_data, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/render/simple/health")
async def render_simple_health():
    """Health check for the simple render endpoint."""
    return {
        "status": "healthy",
        "endpoint": "render_simple",
        "version": "1.0.0",
        "pydantic_bypass": True
    }
