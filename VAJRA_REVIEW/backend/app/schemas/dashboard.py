from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class EngineRiskSummary(BaseModel):
    engine_id: str
    aircraft_id: str
    aircraft_type: str
    base_id: str
    health_score: float
    status: str
    predicted_rul_cycles: int
    anomaly_score: float
    failure_risk_7d: float

class AlertCounts(BaseModel):
    total: int
    unacknowledged: int
    in_progress: int
    resolved: int
    high_critical: int
    medium_warning: int

class MissionReadyDay(BaseModel):
    date: str
    required: int
    predicted_ready: int
    deficit: int

class TelemetryAggregate(BaseModel):
    parameter: str
    current_avg: float
    min: float
    max: float
    unit: str
    status: str

class DigitalTwinComponent(BaseModel):
    component: str
    health_score: float
    colour: str
    shap_contribution: float

class DashboardSummaryResponse(BaseModel):
    total_engines: int
    healthy_engines: int
    watch_engines: int
    critical_engines: int
    total_aircraft: int
    total_bases: int
    fleet_readiness_pct: float
    mean_health: float
    mean_rul: float
    top_5_engines_at_risk: List[EngineRiskSummary]
    active_alert_counts: AlertCounts
    mission_ready_14d_projection: List[MissionReadyDay]
    telemetry_60m_aggregates: List[TelemetryAggregate]
    digital_twin_preview: Dict[str, Any]
