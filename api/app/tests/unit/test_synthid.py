"""Unit tests for SynthID verification service."""

import pytest
from unittest.mock import Mock, patch

from app.services.synthid import (
    SynthIDResult,
    SynthIDVerifier,
    get_synthid_verifier,
    verify_image_synthid,
    get_verification_status
)


class TestSynthIDResult:
    """Test cases for SynthIDResult dataclass."""

    def test_synthid_result_creation(self):
        """Test SynthIDResult creation and attributes."""
        result = SynthIDResult(
            present=True,
            payload="test_payload",
            confidence=0.95,
            verification_method="external"
        )
        
        assert result.present is True
        assert result.payload == "test_payload"
        assert result.confidence == 0.95
        assert result.verification_method == "external"

    def test_synthid_result_to_dict(self):
        """Test converting SynthIDResult to dictionary."""
        result = SynthIDResult(
            present=True,
            payload="test_payload",
            confidence=0.95,
            verification_method="external"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict == {
            "present": True,
            "payload": "test_payload"
        }
        # Note: confidence and verification_method are not included in API response

    def test_synthid_result_false_case(self):
        """Test SynthIDResult for negative case."""
        result = SynthIDResult(
            present=False,
            payload="",
            confidence=0.0,
            verification_method="none"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict == {
            "present": False,
            "payload": ""
        }


class TestSynthIDVerifier:
    """Test cases for SynthIDVerifier class."""

    def test_verifier_initialization(self):
        """Test SynthIDVerifier initialization."""
        verifier = SynthIDVerifier()
        
        assert verifier.enabled is False

    def test_verify_image_disabled(self):
        """Test image verification when disabled."""
        verifier = SynthIDVerifier()
        test_image_data = b"fake_image_data"
        
        result = verifier.verify_image(test_image_data, "openrouter/gemini-2.5-flash-image")
        
        assert result.present is False
        assert result.payload == ""
        assert result.confidence == 0.0
        assert result.verification_method == "none"

    def test_get_verification_status_disabled(self):
        """Test verification status when disabled."""
        verifier = SynthIDVerifier()
        
        status = verifier.get_verification_status()
        
        assert status == "none"

    def test_supports_model_gemini(self):
        """Test model support check for Gemini models."""
        verifier = SynthIDVerifier()
        
        # Should return False because verifier is disabled
        assert verifier.supports_model("openrouter/gemini-2.5-flash-image") is False
        assert verifier.supports_model("openrouter/gemini-pro-vision") is False

    def test_supports_model_unsupported(self):
        """Test model support check for unsupported models."""
        verifier = SynthIDVerifier()
        
        assert verifier.supports_model("openrouter/gpt-4") is False
        assert verifier.supports_model("openrouter/claude-3") is False
        assert verifier.supports_model("unknown-model") is False

    def test_supports_model_enabled_hypothetical(self):
        """Test model support when verifier is hypothetically enabled."""
        verifier = SynthIDVerifier()
        verifier.enabled = True  # Simulate enabled state
        
        # Now should return True for supported models
        assert verifier.supports_model("openrouter/gemini-2.5-flash-image") is True
        assert verifier.supports_model("openrouter/gemini-pro-vision") is True
        
        # Still False for unsupported models
        assert verifier.supports_model("openrouter/gpt-4") is False


class TestGlobalFunctions:
    """Test cases for global convenience functions."""

    def test_get_synthid_verifier_singleton(self):
        """Test that get_synthid_verifier returns singleton instance."""
        verifier1 = get_synthid_verifier()
        verifier2 = get_synthid_verifier()
        
        # Should be the same instance
        assert verifier1 is verifier2
        assert isinstance(verifier1, SynthIDVerifier)

    def test_verify_image_synthid_convenience(self):
        """Test convenience function for image verification."""
        test_image_data = b"fake_image_data"
        
        present, payload = verify_image_synthid(test_image_data, "openrouter/gemini-2.5-flash-image")
        
        assert present is False
        assert payload == ""

    def test_get_verification_status_global(self):
        """Test global verification status function."""
        status = get_verification_status()
        
        assert status == "none"

    def test_verify_image_synthid_different_models(self):
        """Test image verification with different models."""
        test_image_data = b"fake_image_data"
        
        # Test with supported model (when implemented)
        present1, payload1 = verify_image_synthid(test_image_data, "openrouter/gemini-2.5-flash-image")
        assert present1 is False
        assert payload1 == ""
        
        # Test with unsupported model
        present2, payload2 = verify_image_synthid(test_image_data, "openrouter/gpt-4")
        assert present2 is False
        assert payload2 == ""

    @patch('app.services.synthid._verifier', None)
    def test_verifier_recreation(self):
        """Test that verifier is recreated if global instance is None."""
        # Clear global verifier
        import app.services.synthid
        app.services.synthid._verifier = None
        
        verifier = get_synthid_verifier()
        
        assert verifier is not None
        assert isinstance(verifier, SynthIDVerifier)


class TestFutureImplementation:
    """Test cases for future implementation considerations."""

    def test_synthid_result_with_confidence(self):
        """Test SynthIDResult with confidence scoring (future feature)."""
        # High confidence positive result
        result_high = SynthIDResult(
            present=True,
            payload="verified_payload",
            confidence=0.95,
            verification_method="external"
        )
        
        assert result_high.confidence == 0.95
        assert result_high.verification_method == "external"
        
        # Low confidence result
        result_low = SynthIDResult(
            present=False,
            payload="",
            confidence=0.3,
            verification_method="declared"
        )
        
        assert result_low.confidence == 0.3
        assert result_low.verification_method == "declared"

    def test_model_support_expansion(self):
        """Test that model support can be expanded in the future."""
        verifier = SynthIDVerifier()
        verifier.enabled = True  # Simulate future enabled state
        
        # Current supported models
        current_models = [
            "openrouter/gemini-2.5-flash-image",
            "openrouter/gemini-pro-vision"
        ]
        
        for model in current_models:
            assert verifier.supports_model(model) is True
        
        # Future models could be added to the supports_model method
        # This test documents the expected behavior

    def test_verification_methods(self):
        """Test different verification methods (future implementation)."""
        # Test all possible verification statuses
        possible_statuses = ["none", "declared", "external"]
        
        for status in possible_statuses:
            result = SynthIDResult(
                present=status != "none",
                payload="test" if status != "none" else "",
                confidence=0.9 if status == "external" else (0.5 if status == "declared" else 0.0),
                verification_method=status
            )
            
            assert result.verification_method == status
            
            # External verification should have higher confidence
            if status == "external":
                assert result.confidence >= 0.8
            elif status == "declared":
                assert result.confidence >= 0.3
            else:  # none
                assert result.confidence == 0.0
