"""Unit tests for brand canon enforcement service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

from app.services.brand_canon_enforcer import (
    CanonEnforcementResult,
    BrandCanonEnforcer,
    get_brand_canon_enforcer,
    enforce_brand_canon
)
from app.models.schemas import RenderRequest


class MockConstraints:
    """Mock constraints object for testing."""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def model_dump(self, exclude_none=True):
        result = {}
        for key, value in self.__dict__.items():
            if not exclude_none or value is not None:
                result[key] = value
        return result


class TestCanonEnforcementResult:
    """Test cases for CanonEnforcementResult dataclass."""

    def test_canon_enforcement_result_creation(self):
        """Test CanonEnforcementResult creation and attributes."""
        result = CanonEnforcementResult(
            enforced=True,
            canon_used={"palette_hex": ["#FF0000", "#00FF00"]},
            violations=["Color not in palette"],
            enhanced_prompt="Enhanced prompt text",
            confidence_score=0.85
        )
        
        assert result.enforced is True
        assert result.canon_used == {"palette_hex": ["#FF0000", "#00FF00"]}
        assert result.violations == ["Color not in palette"]
        assert result.enhanced_prompt == "Enhanced prompt text"
        assert result.confidence_score == 0.85

    def test_canon_enforcement_result_to_audit_dict(self):
        """Test converting CanonEnforcementResult to audit dictionary."""
        result = CanonEnforcementResult(
            enforced=True,
            canon_used={"palette_hex": ["#FF0000"], "fonts": ["Arial"]},
            violations=["Violation 1", "Violation 2"],
            enhanced_prompt="Test prompt",
            confidence_score=0.75
        )
        
        audit_dict = result.to_audit_dict()
        
        assert audit_dict["canon_enforced"] is True
        assert audit_dict["violations_count"] == 2
        assert audit_dict["confidence_score"] == 0.75
        assert set(audit_dict["canon_elements"]) == {"palette_hex", "fonts"}

    def test_canon_enforcement_result_empty_canon(self):
        """Test CanonEnforcementResult with empty canon."""
        result = CanonEnforcementResult(
            enforced=False,
            canon_used={},
            violations=[],
            enhanced_prompt="Base prompt",
            confidence_score=0.0
        )
        
        audit_dict = result.to_audit_dict()
        
        assert audit_dict["canon_enforced"] is False
        assert audit_dict["violations_count"] == 0
        assert audit_dict["canon_elements"] == []


class TestBrandCanonEnforcer:
    """Test cases for BrandCanonEnforcer class."""

    def test_enforcer_initialization(self):
        """Test BrandCanonEnforcer initialization."""
        enforcer = BrandCanonEnforcer()
        
        assert enforcer.enabled is True

    def test_get_default_canon(self):
        """Test default canon generation."""
        enforcer = BrandCanonEnforcer()
        
        default_canon = enforcer._get_default_canon()
        
        assert "palette_hex" in default_canon
        assert "fonts" in default_canon
        assert "voice" in default_canon
        assert "logo_safe_zone_pct" in default_canon
        assert isinstance(default_canon["palette_hex"], list)
        assert isinstance(default_canon["fonts"], list)

    @patch('app.services.brand_canon_enforcer.derive_canon_from_project')
    @patch('app.services.brand_canon_enforcer.cache_get_set')
    def test_get_project_canon_success(self, mock_cache, mock_derive):
        """Test successful project canon retrieval."""
        enforcer = BrandCanonEnforcer()
        
        # Mock canon data
        canon_data = {
            "palette_hex": ["#1E3A8A", "#FFFFFF"],
            "fonts": ["Inter", "Roboto"],
            "voice": {"tone": "professional"}
        }
        
        import json
        mock_cache.return_value = json.dumps(canon_data).encode("utf-8")
        
        result = enforcer._get_project_canon("test_project")
        
        assert result == canon_data
        mock_cache.assert_called_once()

    @patch('app.services.brand_canon_enforcer.derive_canon_from_project')
    @patch('app.services.brand_canon_enforcer.cache_get_set')
    def test_get_project_canon_failure_fallback(self, mock_cache, mock_derive):
        """Test project canon retrieval with fallback to default."""
        enforcer = BrandCanonEnforcer()
        
        # Mock cache failure
        mock_cache.side_effect = Exception("Cache failure")
        
        result = enforcer._get_project_canon("test_project")
        
        # Should return default canon
        assert "palette_hex" in result
        assert "fonts" in result
        assert result == enforcer._get_default_canon()

    def test_merge_constraints_with_canon_no_constraints(self):
        """Test merging with no request constraints."""
        enforcer = BrandCanonEnforcer()
        
        canon = {"palette_hex": ["#FF0000"], "fonts": ["Arial"]}
        
        result = enforcer._merge_constraints_with_canon(None, canon)
        
        assert result == canon

    def test_merge_constraints_with_canon_core_elements(self):
        """Test merging constraints with core brand elements."""
        enforcer = BrandCanonEnforcer()
        
        canon = {
            "palette_hex": ["#FF0000", "#00FF00"],
            "fonts": ["Arial", "Helvetica"],
            "voice": {"tone": "professional"}
        }
        
        constraints = MockConstraints(
            palette_hex=["#0000FF"],  # Should be ignored (core element)
            fonts=["Comic Sans"],     # Should be ignored (core element)
            logo_safe_zone_pct=20.0  # Should be included (non-core)
        )
        
        result = enforcer._merge_constraints_with_canon(constraints, canon)
        
        # Core elements should use canon values
        assert result["palette_hex"] == ["#FF0000", "#00FF00"]
        assert result["fonts"] == ["Arial", "Helvetica"]
        assert result["voice"] == {"tone": "professional"}
        
        # Non-core elements should use constraint values
        assert result["logo_safe_zone_pct"] == 20.0

    def test_validate_constraints_against_canon_no_violations(self):
        """Test constraint validation with no violations."""
        enforcer = BrandCanonEnforcer()
        
        canon = {
            "palette_hex": ["#FF0000", "#00FF00", "#0000FF"],
            "fonts": ["Arial", "Helvetica"],
            "logo_safe_zone_pct": 15.0
        }
        
        constraints = MockConstraints(
            palette_hex=["#FF0000", "#00FF00"],  # Subset of canon
            fonts=["Arial"],                     # Subset of canon
            logo_safe_zone_pct=20.0             # Above minimum
        )
        
        violations = enforcer._validate_constraints_against_canon(constraints, canon)
        
        assert violations == []

    def test_validate_constraints_against_canon_with_violations(self):
        """Test constraint validation with violations."""
        enforcer = BrandCanonEnforcer()
        
        canon = {
            "palette_hex": ["#FF0000", "#00FF00"],
            "fonts": ["Arial", "Helvetica"],
            "logo_safe_zone_pct": 20.0
        }
        
        constraints = MockConstraints(
            palette_hex=["#FF0000", "#0000FF"],  # #0000FF not in canon
            fonts=["Arial", "Comic Sans"],       # Comic Sans not in canon
            logo_safe_zone_pct=10.0             # Below minimum
        )
        
        violations = enforcer._validate_constraints_against_canon(constraints, canon)
        
        assert len(violations) == 3
        assert any("#0000FF" in v for v in violations)
        assert any("Comic Sans" in v for v in violations)
        assert any("safe zone" in v.lower() for v in violations)

    def test_enhance_prompt_with_canon_comprehensive(self):
        """Test prompt enhancement with comprehensive canon."""
        enforcer = BrandCanonEnforcer()
        
        base_prompt = "Create a banner design"
        canon = {
            "palette_hex": ["#1E3A8A", "#FFFFFF"],
            "fonts": ["Inter", "Roboto"],
            "voice": {
                "tone": "professional",
                "dos": ["Be clear", "Be concise"],
                "donts": ["Avoid jargon", "Avoid clutter"]
            },
            "logo_safe_zone_pct": 25.0,
            "style_guidelines": {
                "prefer_minimal": True,
                "avoid_gradients": True,
                "max_colors": 3
            }
        }
        
        enhanced_prompt = enforcer._enhance_prompt_with_canon(base_prompt, canon)
        
        assert base_prompt in enhanced_prompt
        assert "#1E3A8A" in enhanced_prompt
        assert "#FFFFFF" in enhanced_prompt
        assert "Inter" in enhanced_prompt
        assert "Roboto" in enhanced_prompt
        assert "professional" in enhanced_prompt
        assert "Be clear" in enhanced_prompt
        assert "Avoid jargon" in enhanced_prompt
        assert "25.0%" in enhanced_prompt
        assert "minimal" in enhanced_prompt
        assert "gradients" in enhanced_prompt
        assert "maximum 3 colors" in enhanced_prompt
        assert "CRITICAL" in enhanced_prompt

    def test_enhance_prompt_with_canon_minimal(self):
        """Test prompt enhancement with minimal canon."""
        enforcer = BrandCanonEnforcer()
        
        base_prompt = "Create a design"
        canon = {"palette_hex": ["#FF0000"]}
        
        enhanced_prompt = enforcer._enhance_prompt_with_canon(base_prompt, canon)
        
        assert base_prompt in enhanced_prompt
        assert "#FF0000" in enhanced_prompt
        assert "CRITICAL" in enhanced_prompt

    def test_calculate_enforcement_confidence_high(self):
        """Test confidence calculation with high confidence scenario."""
        enforcer = BrandCanonEnforcer()
        
        canon = {
            "palette_hex": ["#FF0000"],
            "fonts": ["Arial"],
            "voice": {"tone": "professional"},
            "logo_safe_zone_pct": 20.0
        }
        violations = []
        
        confidence = enforcer._calculate_enforcement_confidence(canon, violations)
        
        # Should be high confidence (0.9 base + 4 * 0.025 boost = 1.0, capped at 1.0)
        assert confidence == 1.0

    def test_calculate_enforcement_confidence_low(self):
        """Test confidence calculation with low confidence scenario."""
        enforcer = BrandCanonEnforcer()
        
        canon = {}  # No canon elements
        violations = ["Violation 1", "Violation 2", "Violation 3"]
        
        confidence = enforcer._calculate_enforcement_confidence(canon, violations)
        
        # Should be low confidence (0.9 base - 3 * 0.1 = 0.6)
        assert confidence == 0.6

    def test_validate_generated_output_placeholder(self):
        """Test generated output validation (placeholder implementation)."""
        enforcer = BrandCanonEnforcer()
        
        image_data = b"fake_image_data"
        canon = {"palette_hex": ["#FF0000"]}
        
        result = enforcer.validate_generated_output(image_data, canon)
        
        assert result["validation_performed"] is False
        assert "not yet implemented" in result["reason"]
        assert "future_capabilities" in result

    @patch('app.services.brand_canon_enforcer.BrandCanonEnforcer._get_project_canon')
    def test_enforce_canon_in_prompt_disabled(self, mock_get_canon):
        """Test canon enforcement when disabled."""
        enforcer = BrandCanonEnforcer()
        enforcer.enabled = False
        
        request = Mock()
        request.project_id = "test_project"
        request.constraints = None
        
        result = enforcer.enforce_canon_in_prompt(request, "base prompt")
        
        assert result.enforced is False
        assert result.canon_used == {}
        assert result.violations == []
        assert result.enhanced_prompt == "base prompt"
        assert result.confidence_score == 0.0
        
        # Should not call get_project_canon when disabled
        mock_get_canon.assert_not_called()

    @patch('app.services.brand_canon_enforcer.BrandCanonEnforcer._get_project_canon')
    def test_enforce_canon_in_prompt_enabled(self, mock_get_canon):
        """Test canon enforcement when enabled."""
        enforcer = BrandCanonEnforcer()
        
        # Mock canon
        mock_canon = {
            "palette_hex": ["#FF0000"],
            "fonts": ["Arial"],
            "voice": {"tone": "professional"}
        }
        mock_get_canon.return_value = mock_canon
        
        # Mock request
        request = Mock()
        request.project_id = "test_project"
        request.constraints = MockConstraints(palette_hex=["#FF0000"])
        
        result = enforcer.enforce_canon_in_prompt(request, "base prompt")
        
        assert result.enforced is True
        assert result.canon_used is not None
        assert isinstance(result.violations, list)
        assert "base prompt" in result.enhanced_prompt
        assert 0.0 <= result.confidence_score <= 1.0
        
        mock_get_canon.assert_called_once_with("test_project", None)


class TestGlobalFunctions:
    """Test cases for global convenience functions."""

    def test_get_brand_canon_enforcer_singleton(self):
        """Test that get_brand_canon_enforcer returns singleton instance."""
        enforcer1 = get_brand_canon_enforcer()
        enforcer2 = get_brand_canon_enforcer()
        
        assert enforcer1 is enforcer2
        assert isinstance(enforcer1, BrandCanonEnforcer)

    @patch('app.services.brand_canon_enforcer.get_brand_canon_enforcer')
    def test_enforce_brand_canon_convenience(self, mock_get_enforcer):
        """Test convenience function for brand canon enforcement."""
        # Mock enforcer
        mock_enforcer = Mock()
        mock_result = CanonEnforcementResult(
            enforced=True,
            canon_used={"palette_hex": ["#FF0000"]},
            violations=[],
            enhanced_prompt="Enhanced prompt",
            confidence_score=0.9
        )
        mock_enforcer.enforce_canon_in_prompt.return_value = mock_result
        mock_get_enforcer.return_value = mock_enforcer
        
        # Mock request
        request = Mock()
        base_prompt = "Test prompt"
        trace = Mock()
        
        result = enforce_brand_canon(request, base_prompt, trace)
        
        assert result == mock_result
        mock_enforcer.enforce_canon_in_prompt.assert_called_once_with(request, base_prompt, trace)

    @patch('app.services.brand_canon_enforcer._enforcer', None)
    def test_enforcer_recreation(self):
        """Test that enforcer is recreated if global instance is None."""
        # Clear global enforcer
        import app.services.brand_canon_enforcer
        app.services.brand_canon_enforcer._enforcer = None
        
        enforcer = get_brand_canon_enforcer()
        
        assert enforcer is not None
        assert isinstance(enforcer, BrandCanonEnforcer)


class TestIntegrationScenarios:
    """Test cases for realistic integration scenarios."""

    @patch('app.services.brand_canon_enforcer.BrandCanonEnforcer._get_project_canon')
    def test_realistic_brand_enforcement_scenario(self, mock_get_canon):
        """Test realistic brand enforcement scenario."""
        enforcer = BrandCanonEnforcer()
        
        # Mock comprehensive brand canon
        brand_canon = {
            "palette_hex": ["#1E3A8A", "#FFFFFF", "#3B82F6"],
            "fonts": ["Inter", "Roboto"],
            "voice": {
                "tone": "professional",
                "dos": ["Be clear and concise", "Use active voice"],
                "donts": ["Avoid jargon", "Don't use all caps"]
            },
            "logo_safe_zone_pct": 20.0,
            "style_guidelines": {
                "prefer_minimal": True,
                "avoid_gradients": False,
                "max_colors": 4
            }
        }
        mock_get_canon.return_value = brand_canon
        
        # Mock request with some constraint violations
        request = Mock()
        request.project_id = "tech_company"
        request.constraints = MockConstraints(
            palette_hex=["#1E3A8A", "#FF0000"],  # #FF0000 not in brand palette
            fonts=["Inter", "Comic Sans"],       # Comic Sans not in brand fonts
            logo_safe_zone_pct=15.0             # Below brand minimum
        )
        
        base_prompt = "Create a modern tech company banner"
        
        result = enforcer.enforce_canon_in_prompt(request, base_prompt, None)
        
        # Should be enforced
        assert result.enforced is True
        
        # Should have violations
        assert len(result.violations) == 3
        
        # Enhanced prompt should include brand elements
        assert "#1E3A8A" in result.enhanced_prompt
        assert "#FFFFFF" in result.enhanced_prompt
        assert "Inter" in result.enhanced_prompt
        assert "professional" in result.enhanced_prompt
        assert "15.0%" in result.enhanced_prompt  # Uses merged constraint value, not canon value
        assert "minimal" in result.enhanced_prompt
        
        # Should have reasonable confidence despite violations
        assert 0.5 <= result.confidence_score <= 0.8

    def test_no_constraints_scenario(self):
        """Test enforcement with no request constraints."""
        enforcer = BrandCanonEnforcer()
        
        # Mock request with no constraints
        request = Mock()
        request.project_id = "test_project"
        request.constraints = None
        
        with patch.object(enforcer, '_get_project_canon') as mock_get_canon:
            mock_get_canon.return_value = {"palette_hex": ["#FF0000"]}
            
            result = enforcer.enforce_canon_in_prompt(request, "base prompt")
            
            # Should still enforce canon
            assert result.enforced is True
            assert result.violations == []  # No violations since no constraints to validate
            assert "#FF0000" in result.enhanced_prompt
