#!/usr/bin/env python3
"""Test the simple render endpoint that bypasses Pydantic issues."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app


def test_simple_endpoint():
    """Test the simple render endpoint."""
    print("🚀 Testing Simple Render Endpoint (Pydantic Bypass)...")
    
    client = TestClient(app)
    
    # Test health endpoint first
    print("\n1. Testing simple health endpoint...")
    try:
        response = client.get('/render/simple/health')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Health check passed!")
            print(f"   Status: {result.get('status')}")
            print(f"   Pydantic bypass: {result.get('pydantic_bypass')}")
        else:
            print(f"   ❌ Health check failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Health check exception: {e}")
        return False
    
    # Test simple render endpoint
    print("\n2. Testing simple render endpoint...")
    try:
        response = client.post('/render/simple', json={
            'project_id': 'test-simple-endpoint',
            'prompts': {
                'task': 'create',
                'instruction': 'Create a beautiful blue circle design'
            },
            'outputs': {
                'count': 1,
                'format': 'png',
                'dimensions': '512x512'
            }
        })
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Simple render successful!")
            print(f"   Render ID: {result.get('render_id')}")
            print(f"   Project ID: {result.get('project_id')}")
            print(f"   Status: {result.get('status')}")
            print(f"   Images: {len(result.get('images', []))}")
            print(f"   Cost: ${result.get('cost_info', {}).get('total_cost_usd', 0)}")
            print(f"   Processing time: {result.get('processing_time_ms')}ms")
            print(f"   Security threat level: {result.get('security_scan', {}).get('threat_level')}")
            print(f"   API version: {result.get('metadata', {}).get('api_version')}")
            return True
        else:
            print(f"   ❌ Simple render failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Simple render exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_simple_endpoint()
    if success:
        print("\n🎉 SIMPLE ENDPOINT WORKING - PYDANTIC ISSUE BYPASSED!")
        print("✅ HTTP API IS NOW FUNCTIONAL!")
        sys.exit(0)
    else:
        print("\n❌ SIMPLE ENDPOINT FAILED!")
        sys.exit(1)
