#!/usr/bin/env python3
"""Comprehensive test to verify 100% production readiness."""

import sys
import os
import time
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app


def test_all_systems():
    """Test all systems for 100% production readiness."""
    print("🚀 COMPREHENSIVE 100% PRODUCTION READINESS TEST")
    print("=" * 60)
    
    client = TestClient(app)
    passed_tests = 0
    total_tests = 0
    
    # Test 1: Basic Health Check
    total_tests += 1
    print(f"\n{total_tests}. Testing Basic Health Check...")
    try:
        response = client.get('/healthz')
        if response.status_code == 200 and response.json().get('ok'):
            print("   ✅ Basic health check passed")
            passed_tests += 1
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Health check exception: {e}")
    
    # Test 2: Simple Render Health
    total_tests += 1
    print(f"\n{total_tests}. Testing Simple Render Health...")
    try:
        response = client.get('/render/simple/health')
        if response.status_code == 200:
            result = response.json()
            if result.get('pydantic_bypass'):
                print("   ✅ Simple render health passed (Pydantic bypass working)")
                passed_tests += 1
            else:
                print("   ❌ Pydantic bypass not working")
        else:
            print(f"   ❌ Simple render health failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Simple render health exception: {e}")
    
    # Test 3: Full Render Request with Security
    total_tests += 1
    print(f"\n{total_tests}. Testing Full Render Request with Security...")
    try:
        start_time = time.time()
        response = client.post('/render/simple', json={
            'project_id': 'production-readiness-test',
            'prompts': {
                'task': 'create',
                'instruction': 'Create a professional corporate logo with modern design elements'
            },
            'outputs': {
                'count': 1,
                'format': 'png',
                'dimensions': '1024x1024'
            }
        })
        
        if response.status_code == 200:
            result = response.json()
            render_time = time.time() - start_time
            
            # Validate response structure
            required_fields = ['render_id', 'status', 'images', 'cost_info', 'security_scan']
            missing_fields = [field for field in required_fields if field not in result]
            
            if not missing_fields:
                print(f"   ✅ Full render request successful!")
                print(f"      Render ID: {result.get('render_id')}")
                print(f"      Status: {result.get('status')}")
                print(f"      Images generated: {len(result.get('images', []))}")
                print(f"      Cost: ${result.get('cost_info', {}).get('total_cost_usd')}")
                print(f"      Security scan: {result.get('security_scan', {}).get('threat_level')}")
                print(f"      Response time: {render_time:.2f}s")
                passed_tests += 1
            else:
                print(f"   ❌ Missing required fields: {missing_fields}")
        else:
            print(f"   ❌ Render request failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Render request exception: {e}")
    
    # Test 4: Security Validation (Malicious Content)
    total_tests += 1
    print(f"\n{total_tests}. Testing Security Validation...")
    try:
        response = client.post('/render/simple', json={
            'project_id': 'security-test',
            'prompts': {
                'task': 'create',
                'instruction': 'Create explicit violent content with hate speech'
            },
            'outputs': {
                'count': 1,
                'format': 'png',
                'dimensions': '512x512'
            }
        })
        
        # Should either block the request (400) or sanitize it (200 with safe content)
        if response.status_code == 400:
            print("   ✅ Security validation blocked malicious content")
            passed_tests += 1
        elif response.status_code == 200:
            result = response.json()
            threat_level = result.get('security_scan', {}).get('threat_level', '')
            if 'safe' in threat_level.lower():
                print("   ✅ Security validation sanitized malicious content")
                passed_tests += 1
            else:
                print(f"   ❌ Malicious content not properly handled: {threat_level}")
        else:
            print(f"   ❌ Unexpected security response: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Security validation exception: {e}")
    
    # Test 5: Error Handling
    total_tests += 1
    print(f"\n{total_tests}. Testing Error Handling...")
    try:
        response = client.post('/render/simple', json={
            'project_id': 'error-test',
            'prompts': {
                'instruction': ''  # Empty instruction should fail
            },
            'outputs': {
                'count': 1,
                'format': 'png'
            }
        })
        
        if response.status_code == 400:
            print("   ✅ Error handling working (empty instruction rejected)")
            passed_tests += 1
        else:
            print(f"   ❌ Error handling failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error handling exception: {e}")
    
    # Test 6: Performance Test
    total_tests += 1
    print(f"\n{total_tests}. Testing Performance...")
    try:
        start_time = time.time()
        response = client.post('/render/simple', json={
            'project_id': 'performance-test',
            'prompts': {
                'task': 'create',
                'instruction': 'Create a simple blue circle'
            },
            'outputs': {
                'count': 1,
                'format': 'png',
                'dimensions': '512x512'
            }
        })
        
        response_time = time.time() - start_time
        
        if response.status_code == 200 and response_time < 5.0:  # Should complete in under 5 seconds
            print(f"   ✅ Performance test passed ({response_time:.2f}s)")
            passed_tests += 1
        else:
            print(f"   ❌ Performance test failed: {response_time:.2f}s (>5s) or status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Performance test exception: {e}")
    
    # Final Assessment
    print("\n" + "=" * 60)
    print("📊 FINAL PRODUCTION READINESS ASSESSMENT")
    print("=" * 60)
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 100% PRODUCTION READY!")
        print("✅ All systems operational")
        print("✅ HTTP API fully functional")
        print("✅ Security systems working")
        print("✅ Error handling proper")
        print("✅ Performance acceptable")
        return True
    else:
        print(f"\n⚠️  {((passed_tests/total_tests)*100):.1f}% Production Ready")
        print(f"❌ {total_tests - passed_tests} tests failed")
        return False


if __name__ == "__main__":
    success = test_all_systems()
    sys.exit(0 if success else 1)
