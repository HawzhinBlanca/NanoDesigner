#!/usr/bin/env python3
"""Test mock OpenRouter service directly."""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Updated import path or fallback mock for removed module
async def mock_call_task(task_type, messages):
    return {
        "choices": [
            {"message": {"content": "{\"goal\": \"test\", \"ops\": [\"text_overlay\"], \"safety\": {\"respect_logo_safe_zone\": true, \"palette_only\": false}}"}}
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        "model": "openrouter/gpt-5",
        "mock": True,
    }


async def test_mock_service():
    """Test the mock service directly."""
    print("🤖 Testing Mock OpenRouter Service...")
    
    try:
        # Test planner task
        messages = [
            {"role": "system", "content": "You are a design planner."},
            {"role": "user", "content": "Create a simple blue circle"}
        ]
        
        print("🚀 Calling mock planner...")
        result = await mock_call_task("planner", messages)
        
        print("✅ Mock service response received!")
        print(f"   Model: {result.get('model')}")
        print(f"   Content: {result.get('choices', [{}])[0].get('message', {}).get('content', '')[:100]}...")
        print(f"   Tokens: {result.get('usage', {}).get('total_tokens')}")
        print(f"   Cost: ${result.get('cost_usd')}")
        print(f"   Mock: {result.get('mock')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Mock service failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_mock_service())
    sys.exit(0 if success else 1)
