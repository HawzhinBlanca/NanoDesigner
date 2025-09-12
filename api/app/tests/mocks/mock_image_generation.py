"""Mock image generation service for testing without API keys."""

import base64
import io
import json
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Any


def generate_mock_image(prompt: str, size: str = "512x512") -> bytes:
    """Generate a mock image based on the prompt."""
    
    # Parse size
    try:
        width, height = map(int, size.split('x'))
    except:
        width, height = 512, 512
    
    # Create a simple image
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Determine colors and shapes based on prompt
    if 'blue' in prompt.lower():
        color = '#007bff'
    elif 'red' in prompt.lower():
        color = '#dc3545'
    elif 'green' in prompt.lower():
        color = '#28a745'
    else:
        color = '#6c757d'
    
    # Draw based on prompt content
    if 'circle' in prompt.lower():
        # Draw a circle
        margin = min(width, height) // 4
        draw.ellipse([margin, margin, width-margin, height-margin], fill=color)
    elif 'square' in prompt.lower() or 'rectangle' in prompt.lower():
        # Draw a rectangle
        margin = min(width, height) // 4
        draw.rectangle([margin, margin, width-margin, height-margin], fill=color)
    else:
        # Draw a default shape (rounded rectangle)
        margin = min(width, height) // 4
        draw.rounded_rectangle([margin, margin, width-margin, height-margin], radius=20, fill=color)
    
    # Add text if prompt is short enough
    if len(prompt) < 50:
        try:
            # Try to use a default font
            font = ImageFont.load_default()
            text_bbox = draw.textbbox((0, 0), "Mock Design", font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            text_x = (width - text_width) // 2
            text_y = height - text_height - 20
            
            draw.text((text_x, text_y), "Mock Design", fill='black', font=font)
        except:
            # Fallback if font loading fails
            draw.text((width//2 - 40, height - 30), "Mock Design", fill='black')
    
    # Convert to bytes
    img_buffer = io.BytesIO()
    image.save(img_buffer, format='PNG')
    return img_buffer.getvalue()


def mock_call_openrouter_images(model: str, prompt: str, n: int = 1, size: str = "512x512") -> Dict[str, Any]:
    """Mock version of call_openrouter_images."""
    
    images = []
    for i in range(n):
        # Generate mock image
        image_bytes = generate_mock_image(prompt, size)
        
        # Convert to base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        images.append({
            "url": f"data:image/png;base64,{image_b64}",
            "b64_json": image_b64,
            "revised_prompt": f"Mock revised prompt for: {prompt}"
        })
    
    # Return OpenRouter-style response
    return {
        "created": 1234567890,
        "data": images,
        "model": model,
        "usage": {
            "prompt_tokens": len(prompt.split()) * 2,
            "completion_tokens": 0,
            "total_tokens": len(prompt.split()) * 2
        },
        "mock": True
    }
