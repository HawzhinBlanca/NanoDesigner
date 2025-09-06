import pytest
from app.services.guardrails import validate_contract


@pytest.mark.contracts
def test_render_plan_contract_ok():
    """Test that a valid render plan passes contract validation."""
    plan = {
        "goal": "Make a clean banner",
        "ops": ["text_overlay"],
        "safety": {"respect_logo_safe_zone": True, "palette_only": False},
    }
    # Should not raise any exception
    validate_contract("render_plan.json", plan)


@pytest.mark.contracts
def test_canon_contract_ok():
    """Test that a valid canon passes contract validation."""
    canon = {
        "palette_hex": ["#FF0000", "#00FF00"],
        "fonts": ["Inter"],
        "voice": {"tone": "professional", "dos": [], "donts": []},
    }
    # Should not raise any exception
    validate_contract("canon.json", canon)


@pytest.mark.contracts
def test_critique_contract_ok():
    """Test that a valid critique passes contract validation."""
    critique = {"score": 0.8, "violations": [], "repair_suggestions": []}
    # Should not raise any exception
    validate_contract("critique.json", critique)


@pytest.mark.contracts
def test_render_plan_contract_invalid():
    """Test that invalid render plans fail contract validation."""
    invalid_plan = {
        "goal": "x",  # Too short
        "ops": ["invalid_op"],  # Invalid operation
        "safety": {"respect_logo_safe_zone": True}
    }
    with pytest.raises(Exception):  # Should raise validation error
        validate_contract("render_plan.json", invalid_plan)


@pytest.mark.contracts
def test_canon_contract_invalid():
    """Test that invalid canons fail contract validation."""
    invalid_canon = {
        "palette_hex": ["invalid_color"],  # Invalid hex format
        "fonts": [],  # Empty fonts array
        "voice": {"tone": "professional"}
    }
    with pytest.raises(Exception):  # Should raise validation error
        validate_contract("canon.json", invalid_canon)

