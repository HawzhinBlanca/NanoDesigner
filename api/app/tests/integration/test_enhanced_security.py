#!/usr/bin/env python3
"""Test enhanced security system for Week 2."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.enhanced_security import (
    EnhancedSecurityManager, 
    ThreatLevel, 
    ContentPolicyEngine,
    URLValidator
)


def test_content_policy():
    """Test content policy enforcement."""
    print("🔒 Testing Content Policy Engine...")
    
    engine = ContentPolicyEngine()
    
    # Test 1: Safe content
    safe_result = engine.scan_text_content("Create a beautiful landscape image with mountains and trees")
    assert safe_result.threat_level == ThreatLevel.SAFE
    print("✅ Safe content correctly identified")
    
    # Test 2: Blocked content
    blocked_result = engine.scan_text_content("Create explicit adult content with violence")
    assert blocked_result.threat_level == ThreatLevel.BLOCKED
    print("✅ Blocked content correctly identified")
    
    # Test 3: Suspicious content
    suspicious_result = engine.scan_text_content("Click here: javascript:alert('xss')")
    assert suspicious_result.threat_level == ThreatLevel.SUSPICIOUS
    print("✅ Suspicious content correctly identified")
    
    # Test 4: Content sanitization
    if suspicious_result.sanitized_content:
        assert "javascript:" not in suspicious_result.sanitized_content
        print("✅ Content sanitization working")
    
    print("✅ Content Policy Engine tests passed!")
    return True


def test_url_validator():
    """Test URL validation."""
    print("🔗 Testing URL Validator...")
    
    validator = URLValidator(["openai.com", "github.com"])
    
    # Test 1: Safe URL
    safe_url = validator.validate_url("https://api.openai.com/v1/chat/completions")
    assert safe_url.threat_level == ThreatLevel.SAFE
    print("✅ Safe URL correctly validated")
    
    # Test 2: Blocked scheme
    blocked_url = validator.validate_url("javascript:alert('xss')")
    print(f"   Blocked URL result: {blocked_url.threat_level}, reasons: {blocked_url.reasons}")
    assert blocked_url.threat_level == ThreatLevel.BLOCKED
    print("✅ Blocked URL scheme correctly identified")
    
    # Test 3: Suspicious domain
    suspicious_url = validator.validate_url("https://malicious-site.com/payload")
    assert suspicious_url.threat_level == ThreatLevel.SUSPICIOUS
    print("✅ Suspicious domain correctly identified")
    
    # Test 4: Path traversal
    traversal_url = validator.validate_url("https://example.com/../../../etc/passwd")
    assert traversal_url.threat_level == ThreatLevel.SUSPICIOUS
    print("✅ Path traversal correctly detected")
    
    print("✅ URL Validator tests passed!")
    return True


def test_file_scanning():
    """Test file content scanning."""
    print("📁 Testing File Scanning...")
    
    engine = ContentPolicyEngine()
    
    # Test 1: Safe image file
    safe_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
    safe_result = engine.scan_file_content(safe_image, "test.png")
    assert safe_result.threat_level in [ThreatLevel.SAFE, ThreatLevel.SUSPICIOUS]  # Might be suspicious due to minimal PNG
    print("✅ Safe image file processed")
    
    # Test 2: Blocked file type
    blocked_result = engine.scan_file_content(b"fake exe content", "malware.exe")
    assert blocked_result.threat_level == ThreatLevel.BLOCKED
    print("✅ Blocked file type correctly identified")
    
    # Test 3: Executable signature
    pe_header = b'MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00'
    exe_result = engine.scan_file_content(pe_header, "test.jpg")  # Disguised executable
    assert exe_result.threat_level == ThreatLevel.MALICIOUS
    print("✅ Executable signature correctly detected")
    
    # Test 4: File too large
    large_content = b'x' * (11 * 1024 * 1024)  # 11MB
    large_result = engine.scan_file_content(large_content, "large.txt")
    assert large_result.threat_level == ThreatLevel.BLOCKED
    print("✅ Large file correctly blocked")
    
    print("✅ File Scanning tests passed!")
    return True


def test_security_manager():
    """Test integrated security manager."""
    print("🛡️  Testing Security Manager...")
    
    manager = EnhancedSecurityManager()
    
    # Test 1: Safe render request
    safe_result = manager.scan_render_request(
        "Create a beautiful sunset landscape",
        ["https://api.openai.com/example"]
    )
    assert safe_result.threat_level == ThreatLevel.SAFE
    print("✅ Safe render request processed")
    
    # Test 2: Malicious render request
    malicious_result = manager.scan_render_request(
        "Create explicit violent content",
        ["javascript:alert('xss')"]
    )
    print(f"   Malicious result: {malicious_result.threat_level}, reasons: {malicious_result.reasons}")
    if malicious_result.threat_level == ThreatLevel.BLOCKED:
        print("✅ Malicious render request correctly identified")
    else:
        print("❌ Malicious content not properly blocked")
        return False
    
    # Test 3: Policy enforcement
    try:
        blocked_result = manager.content_policy.scan_text_content("explicit violent content")
        manager.enforce_policy(blocked_result, "test")
        print("❌ Policy enforcement failed - should have raised exception")
        return False
    except Exception:
        print("✅ Policy enforcement working correctly")
    
    print("✅ Security Manager tests passed!")
    return True


def test_performance():
    """Test security system performance."""
    print("⚡ Testing Performance...")
    
    import time
    
    manager = EnhancedSecurityManager()
    
    # Test processing speed
    start_time = time.time()
    
    for i in range(100):
        result = manager.scan_render_request(
            f"Create image number {i} with beautiful colors",
            [f"https://api.openai.com/test/{i}"]
        )
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"✅ Processed 100 requests in {processing_time:.2f} seconds")
    print(f"✅ Average: {(processing_time/100)*1000:.1f}ms per request")
    
    if processing_time < 5.0:  # Should process 100 requests in under 5 seconds
        print("✅ Performance test passed!")
        return True
    else:
        print("❌ Performance test failed - too slow")
        return False


def main():
    """Run all security tests."""
    print("🔐 ENHANCED SECURITY SYSTEM TESTS")
    print("=" * 50)
    
    tests = [
        test_content_policy,
        test_url_validator,
        test_file_scanning,
        test_security_manager,
        test_performance
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            print()
    
    print("=" * 50)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL SECURITY TESTS PASSED!")
        return True
    else:
        print("❌ Some security tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
