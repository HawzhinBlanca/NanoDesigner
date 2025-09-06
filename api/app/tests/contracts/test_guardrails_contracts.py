from app.services.guardrails import validate_contract


def test_render_plan_contract_ok():
    plan = {
        "goal": "Make a clean banner",
        "ops": ["text_overlay"],
        "safety": {"respect_logo_safe_zone": True, "palette_only": False},
    }
    validate_contract("render_plan.json", plan)


def test_canon_contract_ok():
    canon = {
        "palette_hex": ["#FF0000", "#00FF00"],
        "fonts": ["Inter"],
        "voice": {"tone": "professional", "dos": [], "donts": []},
    }
    validate_contract("canon.json", canon)


def test_critique_contract_ok():
    critique = {"score": 0.8, "violations": [], "repair_suggestions": []}
    validate_contract("critique.json", critique)

