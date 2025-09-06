"""Unit tests for cost tracking service."""

import pytest
from unittest.mock import Mock

from app.services.cost_tracker import (
    CostInfo,
    CostTracker,
    extract_cost_from_openrouter_response,
    extract_cost_from_image_response,
    estimate_cost_from_tokens,
    estimate_image_cost
)


class TestCostInfo:
    """Test cases for CostInfo dataclass."""

    def test_cost_info_creation(self):
        """Test CostInfo creation and attributes."""
        cost_info = CostInfo(
            total_cost_usd=0.05,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model="openrouter/gpt-4"
        )
        
        assert cost_info.total_cost_usd == 0.05
        assert cost_info.prompt_tokens == 100
        assert cost_info.completion_tokens == 50
        assert cost_info.total_tokens == 150
        assert cost_info.model == "openrouter/gpt-4"

    def test_cost_info_addition(self):
        """Test adding two CostInfo objects."""
        cost1 = CostInfo(
            total_cost_usd=0.02,
            prompt_tokens=50,
            completion_tokens=25,
            total_tokens=75,
            model="gpt-4"
        )
        
        cost2 = CostInfo(
            total_cost_usd=0.03,
            prompt_tokens=60,
            completion_tokens=30,
            total_tokens=90,
            model="claude-3"
        )
        
        combined = cost1 + cost2
        
        assert combined.total_cost_usd == 0.05
        assert combined.prompt_tokens == 110
        assert combined.completion_tokens == 55
        assert combined.total_tokens == 165
        assert combined.model == "gpt-4+claude-3"


class TestCostTracker:
    """Test cases for CostTracker class."""

    def test_cost_tracker_initialization(self):
        """Test CostTracker initialization."""
        tracker = CostTracker()
        
        assert tracker.total_cost == 0.0
        assert len(tracker.calls) == 0

    def test_add_single_call(self):
        """Test adding a single cost call."""
        tracker = CostTracker()
        cost_info = CostInfo(
            total_cost_usd=0.05,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model="gpt-4"
        )
        
        tracker.add_call(cost_info)
        
        assert tracker.total_cost == 0.05
        assert len(tracker.calls) == 1
        assert tracker.calls[0] == cost_info

    def test_add_multiple_calls(self):
        """Test adding multiple cost calls."""
        tracker = CostTracker()
        
        cost1 = CostInfo(0.02, 50, 25, 75, "gpt-4")
        cost2 = CostInfo(0.03, 60, 30, 90, "claude-3")
        cost3 = CostInfo(0.01, 40, 20, 60, "gemini")
        
        tracker.add_call(cost1)
        tracker.add_call(cost2)
        tracker.add_call(cost3)
        
        assert abs(tracker.total_cost - 0.06) < 1e-10
        assert len(tracker.calls) == 3

    def test_get_summary(self):
        """Test getting cost summary."""
        tracker = CostTracker()
        
        cost1 = CostInfo(0.02, 50, 25, 75, "gpt-4")
        cost2 = CostInfo(0.03, 60, 30, 90, "claude-3")
        cost3 = CostInfo(0.01, 40, 20, 60, "gpt-4")  # Same model as cost1
        
        tracker.add_call(cost1)
        tracker.add_call(cost2)
        tracker.add_call(cost3)
        
        summary = tracker.get_summary()
        
        assert abs(summary["total_cost_usd"] - 0.06) < 1e-10
        assert summary["total_calls"] == 3
        assert summary["total_tokens"] == 225  # 75 + 90 + 60
        assert set(summary["models_used"]) == {"gpt-4", "claude-3"}


class TestCostExtraction:
    """Test cases for cost extraction functions."""

    def test_extract_cost_with_direct_cost(self):
        """Test extracting cost when OpenRouter provides direct cost."""
        response = {
            "choices": [{"message": {"content": "test response"}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "cost": 0.045
            }
        }
        
        cost_info = extract_cost_from_openrouter_response(response, "gpt-4")
        
        assert cost_info.total_cost_usd == 0.045
        assert cost_info.prompt_tokens == 100
        assert cost_info.completion_tokens == 50
        assert cost_info.total_tokens == 150
        assert cost_info.model == "gpt-4"

    def test_extract_cost_with_top_level_cost(self):
        """Test extracting cost from top-level cost field."""
        response = {
            "choices": [{"message": {"content": "test response"}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            },
            "cost": 0.035
        }
        
        cost_info = extract_cost_from_openrouter_response(response, "claude-3")
        
        assert cost_info.total_cost_usd == 0.035
        assert cost_info.model == "claude-3"

    def test_extract_cost_fallback_estimation(self):
        """Test cost extraction falls back to estimation when no cost provided."""
        response = {
            "choices": [{"message": {"content": "test response"}}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        
        cost_info = extract_cost_from_openrouter_response(response, "openrouter/gpt-4")
        
        # Should estimate cost based on tokens
        assert cost_info.total_cost_usd > 0
        assert cost_info.prompt_tokens == 100
        assert cost_info.completion_tokens == 50
        assert cost_info.model == "openrouter/gpt-4"

    def test_extract_cost_minimal_response(self):
        """Test extracting cost from minimal response."""
        response = {
            "choices": [{"message": {"content": "test"}}]
        }
        
        cost_info = extract_cost_from_openrouter_response(response, "unknown-model")
        
        # Should handle missing usage gracefully
        assert cost_info.total_cost_usd >= 0
        assert cost_info.prompt_tokens == 0
        assert cost_info.completion_tokens == 0
        assert cost_info.model == "unknown-model"


class TestCostEstimation:
    """Test cases for cost estimation functions."""

    def test_estimate_cost_gpt4(self):
        """Test cost estimation for GPT-4."""
        cost = estimate_cost_from_tokens("openrouter/gpt-4", 1000, 500)
        
        # GPT-4: $0.03 per 1K prompt tokens, $0.06 per 1K completion tokens
        expected = (1000/1000 * 0.03) + (500/1000 * 0.06)
        assert cost == expected

    def test_estimate_cost_claude3_sonnet(self):
        """Test cost estimation for Claude 3 Sonnet."""
        cost = estimate_cost_from_tokens("openrouter/claude-3-sonnet", 2000, 1000)
        
        # Claude 3 Sonnet: $0.003 per 1K prompt, $0.015 per 1K completion
        expected = (2000/1000 * 0.003) + (1000/1000 * 0.015)
        assert cost == expected

    def test_estimate_cost_unknown_model(self):
        """Test cost estimation for unknown model uses fallback."""
        cost = estimate_cost_from_tokens("unknown-model", 1000, 500)
        
        # Should use default fallback pricing
        expected = (1000/1000 * 0.001) + (500/1000 * 0.002)
        assert cost == expected

    def test_estimate_image_cost_gemini(self):
        """Test image cost estimation for Gemini."""
        cost = estimate_image_cost("openrouter/gemini-2.5-flash-image", 3)
        
        # Should be 3 images * per-image cost
        assert cost == 3 * 0.04

    def test_estimate_image_cost_unknown_model(self):
        """Test image cost estimation for unknown model."""
        cost = estimate_image_cost("unknown-image-model", 2)
        
        # Should use default fallback
        assert cost == 2 * 0.05


class TestImageCostExtraction:
    """Test cases for image cost extraction."""

    def test_extract_image_cost_with_direct_cost(self):
        """Test extracting cost from image response with direct cost."""
        response = {
            "data": [
                {"b64_json": "base64data1"},
                {"b64_json": "base64data2"}
            ],
            "cost": 0.08
        }
        
        cost_info = extract_cost_from_image_response(response, "dall-e-3", 2)
        
        assert cost_info.total_cost_usd == 0.08
        assert cost_info.model == "dall-e-3"
        assert cost_info.prompt_tokens == 0  # Images don't use traditional tokens
        assert cost_info.completion_tokens == 0
        assert cost_info.total_tokens == 0

    def test_extract_image_cost_fallback_estimation(self):
        """Test image cost extraction falls back to estimation."""
        response = {
            "data": [
                {"b64_json": "base64data1"},
                {"b64_json": "base64data2"}
            ]
        }
        
        cost_info = extract_cost_from_image_response(response, "openrouter/gemini-2.5-flash-image", 2)
        
        # Should estimate cost
        assert cost_info.total_cost_usd == 2 * 0.04  # 2 images * $0.04 each
        assert cost_info.model == "openrouter/gemini-2.5-flash-image"
