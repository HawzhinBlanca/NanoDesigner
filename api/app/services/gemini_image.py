from __future__ import annotations

import base64
from typing import List, Tuple
import json
import os

import httpx
from urllib.parse import urlparse

from ..core.config import settings

from .openrouter import call_openrouter, async_call_task, call_openrouter_images
from .langfuse import Trace
import logging

logger = logging.getLogger(__name__)


def _extract_images_from_openrouter(resp: dict) -> List[Tuple[bytes, str]]:
    images: List[Tuple[bytes, str]] = []
    # Try common patterns: choices[].message.content (array of parts) with type=image_url/base64
    choices = resp.get("choices", [])
    for ch in choices:
        message = ch.get("message", {})
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "image_url" and "url" in part:
                        url = part["url"]
                        # SSRF guard: only https and allowlist hosts if provided
                        _ssrf_guard(url)
                        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
                            with client.stream("GET", url) as r:
                                r.raise_for_status()
                                total = 0
                                chunks: List[bytes] = []
                                for chunk in r.iter_bytes():
                                    total += len(chunk)
                                    if total > 10_000_000:  # 10MB cap
                                        raise ValueError("Image too large")
                                    chunks.append(chunk)
                                images.append((b"".join(chunks), _infer_format_from_content_type(r.headers.get("content-type"))))
                    elif part.get("type") == "image_base64" and "data" in part:
                        data = base64.b64decode(part["data"])  # assume png
                        images.append((data, "png"))
        # Some providers return message["images"]= [ {"b64":..., "format":"png"} ]
        imgs = message.get("images")
        if isinstance(imgs, list):
            for it in imgs:
                # Handle gemini-2.5-flash-image format: {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
                if it.get("type") == "image_url" and "image_url" in it:
                    url = it["image_url"].get("url")
                    if url and url.startswith("data:image/"):
                        # Parse data URL: "data:image/png;base64,iVBORw0KGgoAAAA..."
                        try:
                            header, b64_data = url.split(",", 1)
                            fmt = "png"  # Default format
                            if "image/jpeg" in header or "image/jpg" in header:
                                fmt = "jpg"
                            elif "image/webp" in header:
                                fmt = "webp"
                            images.append((base64.b64decode(b64_data), fmt))
                        except Exception:
                            pass  # Skip malformed data URLs
                # Original format: {"b64": "...", "format": "png"}
                else:
                    b64 = it.get("b64") or it.get("data")
                    fmt = it.get("format") or "png"
                    if b64:
                        images.append((base64.b64decode(b64), fmt))
    return images


def _infer_format_from_content_type(ct: str | None) -> str:
    if not ct:
        return "png"
    if "jpeg" in ct:
        return "jpg"
    if "webp" in ct:
        return "webp"
    return "png"


def _ssrf_guard(url: str) -> None:
    u = urlparse(url)
    if u.scheme != "https":
        raise ValueError("Blocked non-HTTPS image URL")
    allow = (settings.__dict__.get("image_fetch_allow_hosts") or os.getenv("IMAGE_FETCH_ALLOW_HOSTS"))
    if allow:
        hosts = {h.strip() for h in allow.split(",") if h.strip()}
        if u.hostname not in hosts:
            raise ValueError("Blocked external host")


async def generate_images(prompt: str, n: int = 1, size: str = "1024x1024", trace: Trace | None = None) -> List[Tuple[bytes, str]]:
    # Try actual image generation first
    images: List[Tuple[bytes, str]] = []
    
    # Enhanced prompt for image generation
    enhanced_prompt = f"""Generate an image based on this description: {prompt}

Output format: Please generate a high-quality image that matches the description exactly."""

    try:
        # Use chat completions for image generation with gemini-2.5-flash-image
        resp = await async_call_task(
            "image",
            messages=[{
                "role": "user", 
                "content": enhanced_prompt
            }],
            trace=trace,
            model="google/gemini-2.5-flash-image-preview",  # MISSION requirement: gemini-2.5-flash-image-preview only
            n=n,
            size=size,
        )
        
        # Save response for debugging (debug-only)
        try:
            if os.getenv("OPENROUTER_DEBUG") == "1":
                with open("/tmp/openrouter_image_resp.json", "w", encoding="utf-8") as f:
                    json.dump(resp, f)
        except Exception:
            logger.debug("Failed to write debug image response", exc_info=False)
            
        # Extract images from chat response
        images = _extract_images_from_openrouter(resp)
        
    except Exception as e:
        logger.warning(f"Chat completions image generation failed: {e}")
        # If chat completions fails, try the legacy Images API as fallback
        try:
            # Enforce preview-only model per mission requirements
            model_name = "google/gemini-2.5-flash-image-preview"
            raw = call_openrouter_images(prompt, n=n, size=size, model=model_name)
            
            try:
                if os.getenv("OPENROUTER_DEBUG") == "1":
                    with open("/tmp/openrouter_images_resp.json", "w", encoding="utf-8") as f:
                        json.dump(raw, f)
            except Exception:
                logger.debug("Failed to write debug images response", exc_info=False)
                
            # Handle different response formats from OpenRouter Images API
            if not raw or not isinstance(raw, dict):
                raise RuntimeError(f"Invalid response format from OpenRouter Images API: {type(raw)}")
            
            # Check for error in response
            if "error" in raw:
                error_msg = raw.get("error", {}).get("message", "Unknown error")
                raise RuntimeError(f"OpenRouter Images API error: {error_msg}")
            
            data = raw.get("data") or []
            out: List[Tuple[bytes, str]] = []
            
            for item in data:
                if not isinstance(item, dict):
                    continue
                    
                # Try multiple possible field names for the base64 data
                b64 = item.get("b64_json") or item.get("b64") or item.get("data")
                fmt = item.get("format") or "png"
                
                if b64:
                    try:
                        # Add size guard before decoding to prevent huge payloads
                        if len(b64) > 14_000_000:  # ~10MB base64
                            raise ValueError("Image too large in base64 response")
                        decoded_data = base64.b64decode(b64)
                        out.append((decoded_data, fmt))
                    except Exception as decode_e:
                        logger.warning(f"Failed to decode base64 image data: {decode_e}")
                        continue
                        
            images = out
            
        except Exception as fallback_e:
            logger.error(f"Images API also failed: {fallback_e}")
            # Both methods failed - for development/demo, generate a branded placeholder
            images = await _generate_demo_image(prompt, n, size)
    
    if not images:
        # Last resort: generate demo images
        images = await _generate_demo_image(prompt, n, size)
    
    return images[:n]


async def _generate_demo_image(prompt: str, n: int = 1, size: str = "1024x1024") -> List[Tuple[bytes, str]]:
    """Generate demo placeholder images with KAAE branding when API fails."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # Parse dimensions
        width, height = map(int, size.split('x'))
        
        # KAAE brand colors
        kaae_blue = (71, 112, 163)  # #4770A3
        kaae_gold = (247, 181, 0)   # #F7B500
        cream = (253, 248, 243)     # #FDF8F3
        
        images = []
        
        for i in range(n):
            # Create image with KAAE blue background
            img = Image.new('RGB', (width, height), kaae_blue)
            draw = ImageDraw.Draw(img)
            
            # Add golden border
            border_width = max(10, width // 100)
            draw.rectangle([0, 0, width-1, height-1], outline=kaae_gold, width=border_width)
            
            # Add text
            try:
                # Try to use a nice font if available
                font_size = max(20, min(width, height) // 20)
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # KAAE logo text
            logo_text = "KAAE"
            subtitle = "Kurdistan Academia for\nArchitecture & Engineering"
            
            # Calculate text positions
            logo_bbox = draw.textbbox((0, 0), logo_text, font=font)
            logo_w = logo_bbox[2] - logo_bbox[0]
            logo_h = logo_bbox[3] - logo_bbox[1]
            
            logo_x = (width - logo_w) // 2
            logo_y = height // 3
            
            # Draw main KAAE text in gold
            draw.text((logo_x, logo_y), logo_text, fill=kaae_gold, font=font)
            
            # Draw subtitle in cream
            try:
                subtitle_font_size = max(12, font_size // 2)
                try:
                    subtitle_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", subtitle_font_size)
                except:
                    subtitle_font = ImageFont.load_default()
                
                subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
                subtitle_w = subtitle_bbox[2] - subtitle_bbox[0]
                subtitle_x = (width - subtitle_w) // 2
                subtitle_y = logo_y + logo_h + 20
                
                draw.text((subtitle_x, subtitle_y), subtitle, fill=cream, font=subtitle_font)
            except:
                pass
            
            # Add a subtle pattern/decoration
            center_x, center_y = width // 2, height // 2
            for radius in range(50, 150, 25):
                if radius < min(width, height) // 4:
                    draw.ellipse([
                        center_x - radius, center_y - radius,
                        center_x + radius, center_y + radius
                    ], outline=kaae_gold, width=2)
            
            # Save to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            images.append((img_bytes.getvalue(), "png"))
        
        logger.info(f"Generated {len(images)} demo KAAE images with brand colors")
        return images
        
    except Exception as e:
        logger.error(f"Failed to generate demo image: {e}")
        # Ultra fallback - return a basic PNG
        return [(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x04\x00\x00\x00\x04\x00\x08\x06\x00\x00\x00\xa7\x8d\x84\xa7\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x00\x0eIDATx\xdac\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x18\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82', "png")]
