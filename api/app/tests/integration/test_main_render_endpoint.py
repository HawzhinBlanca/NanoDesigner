#!/usr/bin/env python3
"""Test the main /render endpoint after all fixes."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app


def test_main_render_endpoint():
    """Test the main /render endpoint with all fixes applied."""
    print("🚀 Testing Main /render Endpoint After All Fixes...")
    
    client = TestClient(app)
    
    # Test 1: Main render endpoint
    print("\n1. Testing main /render endpoint...")
    try:
        response = client.post('/render', json={
            'project_id': 'test-main-render',
            'prompts': {
                'task': 'create',
                'instruction': 'Create a professional logo with blue colors'
            },
            'outputs': {
                'count': 1,
                'format': 'png',
                'dimensions': '1024x1024'
            }
        })
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Main render endpoint working!")
            print(f"   Render ID: {result.get('render_id')}")
            print(f"   Images: {len(result.get('images', []))}")
            print(f"   Cost: ${result.get('cost_info', {}).get('total_cost_usd')}")
        else:
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 2: Error handling with standardized responses
    print("\n2. Testing standardized error responses...")
    try:
        response = client.post('/render', json={
            'project_id': 'test-error',
            'prompts': {
                'instruction': ''  # Empty instruction should fail
            }
        })
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            if 'error' in result:
                print(f"   ✅ Standardized error format working!")
                print(f"   Error code: {result['error'].get('code')}")
                print(f"   Message: {result['error'].get('message')}")
                print(f"   Trace ID: {result['error'].get('trace_id')}")
            else:
                print(f"   ⚠️  Error format not standardized: {result}")
        else:
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 3: Security validation
    print("\n3. Testing security validation...")
    try:
        response = client.post('/render', json={
            'project_id': 'test-security',
            'prompts': {
                'instruction': 'Create explicit violent content with hate speech'
            },
            'outputs': {
                'count': 1,
                'format': 'png'
            }
        })
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            if 'error' in result and 'SECURITY_POLICY_VIOLATION' in result['error'].get('code', ''):
                print(f"   ✅ Security validation with standardized errors working!")
                print(f"   Error code: {result['error'].get('code')}")
            else:
                print(f"   ⚠️  Security response: {result}")
        else:
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")


if __name__ == "__main__":
    test_main_render_endpoint()
    print("\n🎉 MAIN RENDER ENDPOINT TESTING COMPLETE!")
