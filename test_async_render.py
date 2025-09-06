#!/usr/bin/env python3
"""
Comprehensive test for async render system with Redis Streams, WebSockets, and Prometheus metrics
"""

import asyncio
import aiohttp
import json
import time
import websockets
from datetime import datetime
import sys

API_BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"

async def test_prometheus_metrics():
    """Test Prometheus metrics endpoint"""
    print("\n🔍 Testing Prometheus metrics...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/metrics") as resp:
            if resp.status == 200:
                content = await resp.text()
                print(f"✅ Prometheus metrics available ({len(content.splitlines())} lines)")
                
                # Check for key metrics
                if "api_requests_total" in content:
                    print("✅ API request metrics found")
                if "queue_depth_current" in content:
                    print("✅ Queue metrics found")
                if "application_uptime_seconds" in content:
                    print("✅ Application metrics found")
                    
                return True
            else:
                print(f"❌ Prometheus metrics failed: {resp.status}")
                return False

async def test_admin_endpoints():
    """Test admin worker management endpoints"""
    print("\n🔧 Testing admin endpoints...")
    
    async with aiohttp.ClientSession() as session:
        # Get worker stats
        async with session.get(f"{API_BASE}/admin/workers") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Worker stats: {data['running_workers']}/{data['max_workers']} workers")
            else:
                print(f"❌ Worker stats failed: {resp.status}")
                return False
                
        # Get system stats  
        async with session.get(f"{API_BASE}/admin/system") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ System stats - Queue: {data['queue']['depth']}, CPU: {data['system']['cpu_percent']:.1f}%")
            else:
                print(f"❌ System stats failed: {resp.status}")
                return False
                
        return True

async def test_async_render():
    """Test async render endpoints"""
    print("\n🎨 Testing async render system...")
    
    # Test payload
    payload = {
        "project_id": "test-async-001",
        "prompts": {
            "task": "Create a logo",
            "instruction": "A simple modern logo for NanoDesigner with clean typography"
        },
        "outputs": {
            "count": 1,
            "format": "png", 
            "dimensions": "1024x1024"
        },
        "constraints": {
            "palette_hex": ["#000000", "#FFFFFF"],
            "fonts": ["Inter"]
        }
    }
    
    async with aiohttp.ClientSession() as session:
        # Submit async render job
        async with session.post(f"{API_BASE}/render/async", json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Async render submitted: {data}")
                
                if data.get("cached"):
                    print("✅ Result was cached")
                    return True
                    
                job_id = data.get("job_id")
                if not job_id:
                    print("❌ No job_id returned")
                    return False
                    
                print(f"📝 Job ID: {job_id}")
                
                # Poll job status
                for i in range(10):  # Poll for up to 10 seconds
                    await asyncio.sleep(1)
                    
                    async with session.get(f"{API_BASE}/render/jobs/{job_id}") as status_resp:
                        if status_resp.status == 200:
                            status_data = await status_resp.json()
                            status = status_data.get("status")
                            print(f"🔄 Status: {status} (progress: {status_data.get('progress', 0)}%)")
                            
                            if status == "completed":
                                print(f"✅ Job completed! URL: {status_data.get('url', 'N/A')}")
                                return True
                            elif status == "failed":
                                print(f"❌ Job failed: {status_data.get('error', 'Unknown error')}")
                                return False
                        else:
                            print(f"❌ Status check failed: {status_resp.status}")
                            
                print("⏰ Job did not complete within timeout")
                return False
            else:
                print(f"❌ Async render failed: {resp.status}")
                return False

async def test_websocket():
    """Test WebSocket job updates"""
    print("\n🔌 Testing WebSocket functionality...")
    
    try:
        # Test health WebSocket first
        async with websockets.connect(f"{WS_BASE}/ws/health") as websocket:
            print("✅ WebSocket health connection established")
            
            # Wait for ping message
            message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            data = json.loads(message)
            
            if data.get("type") == "ping":
                print("✅ WebSocket ping received")
                return True
            else:
                print(f"❌ Unexpected WebSocket message: {data}")
                return False
                
    except asyncio.TimeoutError:
        print("❌ WebSocket timeout")
        return False
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        return False

async def test_queue_stats():
    """Test render queue statistics"""
    print("\n📊 Testing queue statistics...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/render/queue/stats") as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Queue stats: {data['queue_depth']} jobs, status: {data['status']}")
                print(f"   Estimated wait: {data['estimated_wait_minutes']} minutes")
                return True
            else:
                print(f"❌ Queue stats failed: {resp.status}")
                return False

async def test_complete_system():
    """Run comprehensive system test"""
    print("🚀 Starting comprehensive async render system test...")
    print(f"⏰ Test started at {datetime.now()}")
    
    tests = [
        ("Prometheus Metrics", test_prometheus_metrics),
        ("Admin Endpoints", test_admin_endpoints),
        ("Queue Statistics", test_queue_stats),
        ("WebSocket Health", test_websocket),
        ("Async Render System", test_async_render)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if await test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\n📈 Test Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All async render system tests PASSED!")
        return True
    else:
        print("⚠️  Some tests failed")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_complete_system())
    sys.exit(0 if success else 1)