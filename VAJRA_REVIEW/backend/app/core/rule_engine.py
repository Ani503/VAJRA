"""
Rule Engine Safety Fallback for VAJRA.
Evaluates manufacturer physical operating thresholds and safety limits independently of ML.
Maps Warning -> Medium severity, Critical -> High severity.
Stores alert source as 'rule_engine' or 'ml'.
"""

import operator
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.models.health import RuleEngineThreshold

logger = logging.getLogger("rule_engine")

OPERATOR_MAP = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}

SEVERITY_MAP = {
    "Critical": "High",
    "Warning": "Medium",
    "High": "High",
    "Medium": "Medium",
    "Low": "Low",
}

class RuleEngine:
    def __init__(self):
        self.rules: List[Dict[str, Any]] = []

    def load_rules(self, db: Session):
        """Loads rules from database table rule_engine_thresholds."""
        try:
            records = db.query(RuleEngineThreshold).all()
            self.rules = [
                {
                    "id": r.id,
                    "parameter": r.parameter,
                    "operator": r.operator,
                    "threshold": float(r.threshold),
                    "severity": r.severity,
                    "recommended_action": r.recommended_action,
                }
                for r in records
            ]
            logger.info(f"Loaded {len(self.rules)} safety rules from database.")
        except Exception as e:
            logger.error(f"Error loading rule engine thresholds: {e}")
            self.rules = []

    def evaluate(self, telemetry: Dict[str, Any], engine_id: str, aircraft_id: str) -> List[Dict[str, Any]]:
        """
        Evaluates incoming telemetry values against active rules.
        Returns list of triggered alerts.
        """
        triggered_alerts = []

        for rule in self.rules:
            param = rule["parameter"]
            op_sym = rule["operator"]
            thresh = rule["threshold"]
            rule_sev = rule["severity"]
            rec_action = rule["recommended_action"]

            if param not in telemetry or telemetry[param] is None:
                continue

            try:
                val = float(telemetry[param])
                op_func = OPERATOR_MAP.get(op_sym)
                if op_func and op_func(val, thresh):
                    mapped_severity = SEVERITY_MAP.get(rule_sev, "Medium")
                    trigger_text = f"{param} {op_sym} {thresh} (Current: {val:.2f}) - {rec_action}"
                    triggered_alerts.append({
                        "engine_id": engine_id,
                        "aircraft_id": aircraft_id,
                        "parameter": param,
                        "current_value": val,
                        "threshold": thresh,
                        "operator": op_sym,
                        "rule_severity": rule_sev,
                        "severity": mapped_severity,
                        "trigger": trigger_text,
                        "recommended_action": rec_action,
                        "source": "rule_engine",
                    })
            except (ValueError, TypeError):
                continue

        return triggered_alerts

rule_engine = RuleEngine()
