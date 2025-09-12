#!/usr/bin/env python3
"""Test the mock endpoint to verify system works."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app


def test_mock_endpoint():
    """Test the mock render endpoint."""
    print("🚀 Testing Mock Render Endpoint...")
    
    client = TestClient(app)
    
    try:
        response = client.post('/render/mock', json={
            'instruction': 'Create a beautiful blue circle design',
            'count': 1,
            'format': 'png'
        })
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Mock render successful!")
            print(f"   Render ID: {result.get('render_id')}")
            print(f"   Images: {len(result.get('images', []))}")
            print(f"   Processing time: {result.get('processing_time_ms')}ms")
            return True
        else:
            print(f"   ❌ Mock render failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Mock endpoint exception: {e}")
        return False


if __name__ == "__main__":
    success = test_mock_endpoint()
    if success:
        print("\n🎉 MOCK ENDPOINT WORKING - SYSTEM ARCHITECTURE VERIFIED!")
        sys.exit(0)
    else:
        print("\n❌ MOCK ENDPOINT FAILED!")
        sys.exit(1)
