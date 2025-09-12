#!/usr/bin/env python3
"""Test HTTP client for the fixed API."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app


def test_http_endpoints():
    """Test HTTP endpoints using TestClient."""
    print("🚀 Testing HTTP endpoints with TestClient...")
    
    client = TestClient(app)
    
    # Test health endpoint
    print("\n1. Testing health endpoint...")
    try:
        response = client.get('/healthz')
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        if response.status_code == 200:
            print("   ✅ Health endpoint working")
        else:
            print("   ❌ Health endpoint failed")
            return False
    except Exception as e:
        print(f"   ❌ Health endpoint exception: {e}")
        return False
    
    # Test render endpoint
    print("\n2. Testing render endpoint...")
    try:
        response = client.post('/render', json={
            'project_id': 'test-http-client',
            'prompts': {
                'task': 'create',
                'instruction': 'Create a simple blue circle design'
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
            print(f"   ✅ Render successful!")
            print(f"   Render ID: {result.get('render_id')}")
            print(f"   Images: {len(result.get('images', []))}")
            print(f"   Cost: ${result.get('cost_info', {}).get('total_cost_usd', 0)}")
            return True
        else:
            print(f"   ❌ Render failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Render endpoint exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_http_endpoints()
    if success:
        print("\n🎉 ALL HTTP ENDPOINTS WORKING!")
        sys.exit(0)
    else:
        print("\n❌ HTTP ENDPOINTS FAILED!")
        sys.exit(1)
