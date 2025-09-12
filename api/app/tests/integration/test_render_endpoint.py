#!/usr/bin/env python3
"""Test render endpoint directly to find the issue."""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.schemas import RenderRequest, RenderRequestPrompts, RenderRequestOutputs


async def test_render_function():
    """Test the render function directly."""
    print("🔍 Testing render function directly...")
    
    try:
        # Import the render function
        from app.routers.render import render
        
        # Create a test request
        request = RenderRequest(
            project_id="test-project",
            prompts=RenderRequestPrompts(
                task="create",
                instruction="Create a simple blue circle"
            ),
            outputs=RenderRequestOutputs(
                count=1,
                format="png",
                dimensions="512x512"
            )
        )
        
        print("✅ Request object created successfully")
        print(f"   Instruction: {request.prompts.instruction}")
        
        # Try to call the render function
        print("🚀 Calling render function...")
        
        # Set a timeout to prevent hanging
        try:
            result = await asyncio.wait_for(render(request), timeout=10.0)
            print("✅ Render function completed successfully!")
            print(f"   Result type: {type(result)}")
            return True
        except asyncio.TimeoutError:
            print("❌ Render function timed out after 10 seconds")
            return False
        except Exception as e:
            print(f"❌ Render function failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Failed to import or setup: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_render_function())
    sys.exit(0 if success else 1)
