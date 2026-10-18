import pytest
from backend.app.core.rule_engine import RuleEngine, rule_engine
from backend.app.config import settings

def test_rule_engine_evaluation(db_session):
    engine = RuleEngine()
    engine.load_rules(db_session)
    assert len(engine.rules) > 0

    # Reading exceeding vibration critical threshold (threshold = 5.0)
    high_vib_reading = {"vibration_mm_s": 6.2, "egt_c": 630.0}
    alerts = engine.evaluate(high_vib_reading, engine_id="ENG-001", aircraft_id="VJ-101")

    assert len(alerts) >= 1
    crit_alert = [a for a in alerts if a["parameter"] == "vibration_mm_s" and a["severity"] == "High"][0]
    assert crit_alert["severity"] == "High"
    assert crit_alert["source"] == "rule_engine"
    assert "Immediate inspection" in crit_alert["recommended_action"]

def test_rule_engine_warning_mapping(db_session):
    engine = RuleEngine()
    engine.load_rules(db_session)

    # Reading exceeding warning threshold (vibration > 3.5, but <= 5.0)
    warn_vib_reading = {"vibration_mm_s": 4.1}
    alerts = engine.evaluate(warn_vib_reading, engine_id="ENG-002", aircraft_id="VJ-101")

    assert len(alerts) == 1
    assert alerts[0]["severity"] == "Medium"
    assert alerts[0]["source"] == "rule_engine"

def test_rule_engine_with_ml_disabled(db_session):
    # Temporarily set ML_ENABLED to False
    orig_ml_state = settings.ML_ENABLED
    try:
        settings.ML_ENABLED = False
        assert settings.ML_ENABLED is False

        # Evaluation continues working seamlessly
        reading = {"oil_pressure_psi": 35.0}  # < 40 Critical limit
        alerts = rule_engine.evaluate(reading, engine_id="ENG-005", aircraft_id="VJ-103")

        assert len(alerts) >= 1
        oil_alert = alerts[0]
        assert oil_alert["severity"] == "High"
        assert oil_alert["source"] == "rule_engine"
        assert "Ground aircraft" in oil_alert["recommended_action"]
    finally:
        settings.ML_ENABLED = orig_ml_state
