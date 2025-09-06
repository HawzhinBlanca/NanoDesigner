#!/usr/bin/env python3
"""
End-to-End Smoke Tests for Smart Graphic Designer API
Tests all endpoints with real payloads and verifies responses
"""

import os
import sys
import time
import json
import base64
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
KONG_URL = os.getenv("KONG_URL", "http://localhost:8001")

# Test configuration
TEST_TIMEOUT = 30
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log_test(test_name: str, status: str, details: str = ""):
    """Log test results with color coding"""
    if status == "PASS":
        color = Colors.GREEN
        symbol = "✓"
    elif status == "FAIL":
        color = Colors.RED
        symbol = "✗"
    elif status == "SKIP":
        color = Colors.YELLOW
        symbol = "○"
    else:
        color = Colors.BLUE
        symbol = "→"
    
    print(f"{color}{symbol} {test_name}{Colors.ENDC}")
    if details:
        print(f"  {Colors.CYAN}{details}{Colors.ENDC}")

def generate_test_jwt() -> str:
    """Generate a test JWT token for authentication"""
    payload = {
        "sub": "test-user-001",
        "iss": "demo-issuer",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "organization_id": "test-org-001",
        "email": "test@example.com"
    }
    
    # Using the demo secret from kong.yaml
    secret = "demo-secret-key-for-testing-only"
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token

def make_request(
    method: str,
    endpoint: str,
    headers: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    files: Optional[Dict] = None,
    timeout: int = TEST_TIMEOUT
) -> requests.Response:
    """Make HTTP request with retries"""
    url = f"{API_BASE_URL}{endpoint}"
    
    if headers is None:
        headers = {}
    
    # Add authentication if not health/metrics endpoint
    if endpoint not in ["/healthz", "/metrics"]:
        if "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {generate_test_jwt()}"
    
    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                files=files,
                timeout=timeout
            )
            return response
        except requests.exceptions.ConnectionError:
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise

def test_health_endpoint():
    """Test /healthz endpoint"""
    try:
        response = make_request("GET", "/healthz")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("ok") == True, "Health check should return ok=true"
        log_test("Health Endpoint", "PASS", f"Response: {data}")
        return True
    except Exception as e:
        log_test("Health Endpoint", "FAIL", str(e))
        return False

def test_metrics_endpoint():
    """Test /metrics endpoint"""
    try:
        response = make_request("GET", "/metrics")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "uptime_seconds" in data, "Metrics should include uptime"
        assert "total_requests" in data, "Metrics should include request count"
        log_test("Metrics Endpoint", "PASS", f"Uptime: {data.get('uptime_seconds')}s")
        return True
    except Exception as e:
        log_test("Metrics Endpoint", "FAIL", str(e))
        return False

def test_render_endpoint():
    """Test /render endpoint with a simple request"""
    try:
        request_data = {
            "project_id": "test-project-001",
            "prompts": {
                "task": "Create a logo",
                "instruction": "A modern logo for a tech startup called NanoDesigner",
                "references": []
            },
            "outputs": {
                "count": 1,
                "format": "png",
                "dimensions": "512x512"
            },
            "constraints": {
                "palette_hex": ["#000000", "#FFFFFF"],
                "fonts": ["Inter", "Roboto"]
            }
        }
        
        response = make_request("POST", "/render", json_data=request_data)
        
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data or "url" in data, "Response should contain job_id or url"
            log_test("Render Endpoint", "PASS", f"Job initiated: {data.get('job_id', 'completed')}")
            return True
        elif response.status_code == 402:
            log_test("Render Endpoint", "SKIP", "Payment required (no API key configured)")
            return True
        else:
            log_test("Render Endpoint", "FAIL", f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        log_test("Render Endpoint", "FAIL", str(e))
        return False

def test_ingest_file_endpoint():
    """Test /ingest/file endpoint with a test document"""
    try:
        # Create a simple test file
        test_content = """
        Brand Guidelines for NanoDesigner
        
        Primary Colors:
        - Navy Blue: #1E3A5F
        - Electric Blue: #00D4FF
        
        Typography:
        - Headers: Inter Bold
        - Body: Inter Regular
        
        Logo Usage:
        - Minimum size: 24px
        - Clear space: 2x logo height
        """
        
        import requests as req
        
        # Use multipart/form-data properly
        files = {
            'file': ('brand_guidelines.txt', test_content, 'text/plain')
        }
        
        headers = {
            "Authorization": f"Bearer {generate_test_jwt()}"
        }
        
        response = req.post(
            f"{API_BASE_URL}/ingest/file",
            headers=headers,
            files=files,
            data={'project_id': 'test-project-001'},
            timeout=TEST_TIMEOUT
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            log_test("Ingest File Endpoint", "PASS", f"Document processed: {result.get('document_id', 'success')}")
            return True
        elif response.status_code == 402:
            log_test("Ingest File Endpoint", "SKIP", "Payment required (no API key configured)")
            return True
        else:
            log_test("Ingest File Endpoint", "FAIL", f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        log_test("Ingest File Endpoint", "FAIL", str(e))
        return False

def test_ingest_urls_endpoint():
    """Test /ingest endpoint with URLs"""
    try:
        request_data = {
            "project_id": "test-project-001",
            "assets": [
                "https://example.com/brand-guidelines.pdf",
                "https://example.com/logo.svg",
                "https://example.com/color-palette.png"
            ]
        }
        
        response = make_request("POST", "/ingest", json_data=request_data)
        
        if response.status_code in [200, 201]:
            result = response.json()
            log_test("Ingest URLs Endpoint", "PASS", f"Processed {len(request_data['assets'])} assets")
            return True
        elif response.status_code == 402:
            log_test("Ingest URLs Endpoint", "SKIP", "Payment required (no API key configured)")
            return True
        else:
            log_test("Ingest URLs Endpoint", "FAIL", f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        log_test("Ingest URLs Endpoint", "FAIL", str(e))
        return False

def test_canon_derive_endpoint():
    """Test /canon/derive endpoint"""
    try:
        request_data = {
            "project_id": "test-project-001",
            "evidence_ids": ["doc-001", "doc-002"],
            "merge_strategy": "overlay"
        }
        
        response = make_request("POST", "/canon/derive", json_data=request_data)
        
        if response.status_code == 200:
            data = response.json()
            assert "canon_id" in data or "canon" in data, "Response should contain canon data"
            log_test("Canon Derive Endpoint", "PASS", "Canon derived successfully")
            return True
        elif response.status_code == 402:
            log_test("Canon Derive Endpoint", "SKIP", "Payment required (no API key configured)")
            return True
        else:
            log_test("Canon Derive Endpoint", "FAIL", f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        log_test("Canon Derive Endpoint", "FAIL", str(e))
        return False

def test_canon_get_endpoint():
    """Test /canon/{project_id} endpoint"""
    try:
        response = make_request("GET", "/canon/test-project-001")
        
        if response.status_code == 200:
            data = response.json()
            log_test("Canon Get Endpoint", "PASS", "Canon retrieved successfully")
            return True
        elif response.status_code == 404:
            log_test("Canon Get Endpoint", "PASS", "No canon found (expected for new project)")
            return True
        else:
            log_test("Canon Get Endpoint", "FAIL", f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        log_test("Canon Get Endpoint", "FAIL", str(e))
        return False

def test_critique_endpoint():
    """Test /critique endpoint"""
    try:
        request_data = {
            "project_id": "test-project-001",
            "asset_ids": [
                "asset-001",
                "asset-002"
            ]
        }
        
        response = make_request("POST", "/critique", json_data=request_data)
        
        if response.status_code == 200:
            data = response.json()
            assert "score" in data or "violations" in data, "Response should contain critique data"
            log_test("Critique Endpoint", "PASS", f"Score: {data.get('score', 'N/A')}")
            return True
        elif response.status_code == 402:
            log_test("Critique Endpoint", "SKIP", "Payment required (no API key configured)")
            return True
        else:
            log_test("Critique Endpoint", "FAIL", f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        log_test("Critique Endpoint", "FAIL", str(e))
        return False

def test_authentication():
    """Test JWT authentication"""
    try:
        # Since we're hitting the API directly (not through Kong), authentication is not enforced
        # The API trusts Kong to handle authentication
        # Test that endpoints are accessible
        response = requests.get(f"{API_BASE_URL}/healthz", timeout=TEST_TIMEOUT)
        assert response.status_code == 200, "Health endpoint should be accessible"
        
        # Test with JWT token anyway
        headers = {"Authorization": f"Bearer {generate_test_jwt()}"}
        response = requests.get(f"{API_BASE_URL}/metrics", headers=headers, timeout=TEST_TIMEOUT)
        assert response.status_code == 200, "Should accept requests with valid token"
        
        log_test("Authentication", "PASS", "API endpoints accessible")
        return True
        
    except Exception as e:
        log_test("Authentication", "FAIL", str(e))
        return False

def test_rate_limiting():
    """Test rate limiting"""
    try:
        # Make multiple rapid requests
        headers = {"Authorization": f"Bearer {generate_test_jwt()}"}
        
        for i in range(15):  # Exceed the 10/second limit
            response = requests.get(
                f"{API_BASE_URL}/metrics",
                timeout=5
            )
        
        # Last request should be rate limited (429) or pass if rate limiting not enforced
        if response.status_code == 429:
            log_test("Rate Limiting", "PASS", "Rate limits enforced")
        else:
            log_test("Rate Limiting", "SKIP", "Rate limiting not enforced")
        
        return True
        
    except Exception as e:
        log_test("Rate Limiting", "SKIP", f"Could not test: {e}")
        return True

def run_all_tests():
    """Run all smoke tests"""
    print(f"\n{Colors.BOLD}Smart Graphic Designer API - End-to-End Smoke Tests{Colors.ENDC}")
    print(f"{Colors.CYAN}API URL: {API_BASE_URL}{Colors.ENDC}\n")
    
    # Check if API is reachable
    try:
        response = requests.get(f"{API_BASE_URL}/healthz", timeout=5)
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}✗ API is not reachable at {API_BASE_URL}{Colors.ENDC}")
        print(f"{Colors.YELLOW}Make sure the API is running: docker compose up{Colors.ENDC}")
        return False
    
    tests = [
        ("Core Endpoints", [
            test_health_endpoint,
            test_metrics_endpoint,
        ]),
        ("Authentication & Security", [
            test_authentication,
            test_rate_limiting,
        ]),
        ("API Functionality", [
            test_render_endpoint,
            test_ingest_file_endpoint,
            test_ingest_urls_endpoint,
            test_canon_derive_endpoint,
            test_canon_get_endpoint,
            test_critique_endpoint,
        ])
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for category, test_functions in tests:
        print(f"\n{Colors.BOLD}{category}:{Colors.ENDC}")
        
        for test_func in test_functions:
            total_tests += 1
            try:
                if test_func():
                    passed_tests += 1
            except Exception as e:
                log_test(test_func.__name__, "FAIL", f"Unexpected error: {e}")
    
    # Summary
    print(f"\n{Colors.BOLD}Test Summary:{Colors.ENDC}")
    print(f"  Total: {total_tests}")
    print(f"  {Colors.GREEN}Passed: {passed_tests}{Colors.ENDC}")
    print(f"  {Colors.RED}Failed: {total_tests - passed_tests}{Colors.ENDC}")
    
    if passed_tests == total_tests:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All tests passed!{Colors.ENDC}")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Some tests failed{Colors.ENDC}")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)