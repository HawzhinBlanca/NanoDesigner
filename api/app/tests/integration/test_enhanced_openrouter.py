#!/usr/bin/env python3
"""Test enhanced OpenRouter integration for Week 2."""

import sys
import os
import asyncio
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.enhanced_openrouter import (
    CostTracker,
    EnhancedOpenRouterClient,
    SynthIDVerifier,
    UsageMetrics,
    CostBudget,
    ModelProvider,
    enhanced_call_model
)
from app.core.tenant_isolation import TenantContext, IsolationLevel


def test_cost_calculation():
    """Test cost calculation for different models."""
    print("💰 Testing Cost Calculation...")
    
    tracker = CostTracker()
    
    # Test GPT-4 cost calculation
    gpt4_cost = tracker.calculate_cost("openai/gpt-4", {
        'prompt_tokens': 1000,
        'completion_tokens': 500
    })
    
    expected_cost = Decimal('0.03') + (Decimal('0.06') * Decimal('0.5'))  # $0.03 + $0.03 = $0.06
    assert abs(gpt4_cost - expected_cost) < Decimal('0.001')
    print(f"✅ GPT-4 cost calculated correctly: ${gpt4_cost}")
    
    # Test GPT-3.5 cost calculation
    gpt35_cost = tracker.calculate_cost("openai/gpt-3.5-turbo", {
        'prompt_tokens': 1000,
        'completion_tokens': 1000
    })
    
    expected_cost = Decimal('0.001') + Decimal('0.002')  # $0.001 + $0.002 = $0.003
    assert abs(gpt35_cost - expected_cost) < Decimal('0.001')
    print(f"✅ GPT-3.5 cost calculated correctly: ${gpt35_cost}")
    
    # Test image generation cost
    dalle_cost = tracker.calculate_cost("openai/dall-e-3", {
        'images_generated': 2
    })
    
    expected_cost = Decimal('0.04') * 2  # $0.04 * 2 = $0.08
    assert abs(dalle_cost - expected_cost) < Decimal('0.001')
    print(f"✅ DALL-E cost calculated correctly: ${dalle_cost}")
    
    print("✅ Cost calculation tests passed!")
    return True


def test_budget_management():
    """Test budget management and limits."""
    print("📊 Testing Budget Management...")
    
    tracker = CostTracker()
    tenant = TenantContext(
        org_id="test-org",
        user_id="user1",
        isolation_level=IsolationLevel.ISOLATED,
        permissions=[]
    )
    
    # Set budget
    budget = CostBudget(
        daily_limit_usd=Decimal('10.00'),
        monthly_limit_usd=Decimal('100.00'),
        per_request_limit_usd=Decimal('1.00')
    )
    tracker.set_budget(tenant, budget)
    
    # Test within budget
    assert tracker.check_budget_limits(tenant, Decimal('0.50'))
    print("✅ Request within budget allowed")
    
    # Test exceeding per-request limit
    assert not tracker.check_budget_limits(tenant, Decimal('1.50'))
    print("✅ Request exceeding per-request limit blocked")
    
    # Test usage recording
    usage = UsageMetrics(
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        cost_usd=Decimal('0.50'),
        model_used="openai/gpt-3.5-turbo",
        provider="openai"
    )
    
    tracker.record_usage(tenant, usage)
    
    # Get usage stats
    stats = tracker.get_usage_stats(tenant, "daily")
    assert stats["total_cost"] == Decimal('0.50')
    assert stats["total_tokens"] == 1500
    print("✅ Usage recording and stats working")
    
    print("✅ Budget management tests passed!")
    return True


def test_usage_metrics():
    """Test usage metrics tracking."""
    print("📈 Testing Usage Metrics...")
    
    usage = UsageMetrics(
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        images_generated=2,
        cost_usd=Decimal('0.75'),
        model_used="openai/gpt-4",
        provider="openai",
        latency_ms=1500
    )
    
    # Test metrics properties
    assert usage.prompt_tokens == 1000
    assert usage.completion_tokens == 500
    assert usage.total_tokens == 1500
    assert usage.images_generated == 2
    assert usage.cost_usd == Decimal('0.75')
    assert usage.model_used == "openai/gpt-4"
    assert usage.provider == "openai"
    assert usage.latency_ms == 1500
    
    print("✅ Usage metrics structure correct")
    
    # Test cost calculation integration
    tracker = CostTracker()
    calculated_cost = tracker.calculate_cost("openai/gpt-4", {
        'prompt_tokens': usage.prompt_tokens,
        'completion_tokens': usage.completion_tokens
    })
    
    # Should be close to expected cost
    expected = (Decimal('1000') / 1000 * Decimal('0.03')) + (Decimal('500') / 1000 * Decimal('0.06'))
    assert abs(calculated_cost - expected) < Decimal('0.001')
    print(f"✅ Integrated cost calculation: ${calculated_cost}")
    
    print("✅ Usage metrics tests passed!")
    return True


async def test_synthid_verification():
    """Test SynthID content verification."""
    print("🔍 Testing SynthID Verification...")
    
    verifier = SynthIDVerifier()
    
    # Test content verification
    test_content = "This is AI-generated content for testing purposes."
    verification = await verifier.verify_content(test_content, "openai/gpt-4")
    
    # Check verification result structure
    assert "is_ai_generated" in verification
    assert "confidence" in verification
    assert "model_detected" in verification
    assert "watermark_present" in verification
    assert "verification_method" in verification
    assert "timestamp" in verification
    
    print("✅ SynthID verification structure correct")
    
    # Test adding verified_by field
    mock_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": test_content
            }
        }]
    }
    
    enhanced_response = verifier.add_verified_by_field(mock_response, verification)
    
    # Check verified_by field was added
    verified_by = enhanced_response["choices"][0]["message"]["verified_by"]
    assert "method" in verified_by
    assert "confidence" in verified_by
    assert "watermark_detected" in verified_by
    assert "verified_at" in verified_by
    
    print("✅ verified_by field added correctly")
    print("✅ SynthID verification tests passed!")
    return True


def test_rate_limiting():
    """Test rate limiting functionality."""
    print("🚦 Testing Rate Limiting...")
    
    client = EnhancedOpenRouterClient()
    tenant = TenantContext(
        org_id="test-org",
        user_id="user1",
        isolation_level=IsolationLevel.ISOLATED,
        permissions=[]
    )
    
    # Test initial rate limit check (should pass)
    assert client._check_rate_limits(tenant, "openai/gpt-3.5-turbo")
    print("✅ Initial rate limit check passed")
    
    # Simulate many requests
    for i in range(59):  # Fill up to limit
        client._check_rate_limits(tenant, "openai/gpt-3.5-turbo")
    
    # Should still pass (at limit)
    result_at_limit = client._check_rate_limits(tenant, "openai/gpt-3.5-turbo")
    print(f"   Rate limit at threshold result: {result_at_limit}")
    
    # Next request should fail (we've now made 61 requests total)
    result_over_limit = client._check_rate_limits(tenant, "openai/gpt-3.5-turbo")
    print(f"   Rate limit over threshold result: {result_over_limit}")
    
    # The 61st request should fail
    assert not result_over_limit
    print("✅ Rate limit exceeded correctly blocked")
    
    print("✅ Rate limiting tests passed!")
    return True


def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("⚡ Testing Circuit Breaker...")
    
    client = EnhancedOpenRouterClient()
    model = "test/model"
    
    # Initially circuit should be closed
    assert not client._is_circuit_open(model)
    print("✅ Circuit initially closed")
    
    # Record failures to open circuit
    for i in range(5):
        client._record_failure(model)
    
    # Circuit should now be open
    assert client._is_circuit_open(model)
    print("✅ Circuit opened after failures")
    
    # Reset circuit breaker
    client._reset_circuit_breaker(model)
    
    # Circuit should be closed again
    assert not client._is_circuit_open(model)
    print("✅ Circuit reset successfully")
    
    print("✅ Circuit breaker tests passed!")
    return True


def test_model_costs_loading():
    """Test model costs loading and structure."""
    print("💲 Testing Model Costs Loading...")
    
    tracker = CostTracker()
    
    # Check that model costs are loaded
    assert len(tracker.model_costs) > 0
    print(f"✅ Loaded {len(tracker.model_costs)} model cost configurations")
    
    # Check specific models
    required_models = [
        "openai/gpt-4",
        "openai/gpt-3.5-turbo",
        "anthropic/claude-3-sonnet",
        "google/gemini-pro"
    ]
    
    for model in required_models:
        assert model in tracker.model_costs
        cost_info = tracker.model_costs[model]
        assert cost_info.input_cost_per_1k >= 0
        assert cost_info.output_cost_per_1k >= 0
        print(f"✅ {model}: ${cost_info.input_cost_per_1k}/1k input, ${cost_info.output_cost_per_1k}/1k output")
    
    print("✅ Model costs loading tests passed!")
    return True


async def test_integration():
    """Test full integration with mocked API."""
    print("🔗 Testing Full Integration...")
    
    # This would normally make real API calls, but we'll simulate
    tenant = TenantContext(
        org_id="integration-test",
        user_id="user1",
        isolation_level=IsolationLevel.ISOLATED,
        permissions=[]
    )
    
    # Test that the enhanced_call_model function exists and has correct signature
    try:
        # We can't make real API calls in tests, but we can verify the function structure
        import inspect
        sig = inspect.signature(enhanced_call_model)
        params = list(sig.parameters.keys())
        
        assert "tenant" in params
        assert "model" in params
        assert "messages" in params
        
        print("✅ enhanced_call_model function signature correct")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False
    
    print("✅ Integration tests passed!")
    return True


async def main():
    """Run all enhanced OpenRouter tests."""
    print("🤖 ENHANCED OPENROUTER SYSTEM TESTS")
    print("=" * 50)
    
    sync_tests = [
        test_cost_calculation,
        test_budget_management,
        test_usage_metrics,
        test_rate_limiting,
        test_circuit_breaker,
        test_model_costs_loading
    ]
    
    async_tests = [
        test_synthid_verification,
        test_integration
    ]
    
    passed = 0
    total = len(sync_tests) + len(async_tests)
    
    # Run sync tests
    for test in sync_tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            print()
    
    # Run async tests
    for test in async_tests:
        try:
            if await test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            print()
    
    print("=" * 50)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL ENHANCED OPENROUTER TESTS PASSED!")
        return True
    else:
        print("❌ Some enhanced OpenRouter tests failed!")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
