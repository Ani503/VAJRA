from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class EngineListItem(BaseModel):
    engine_id: str
    aircraft_id: str
    aircraft_type: str
    base_id: str
    base_name: str
    position: int
    engine_model: str
    health_score: float
    status: str
    predicted_rul_cycles: int
    anomaly_score: float
    failure_risk_7d: float
    cycles_since_new: int
    hours_since_overhaul: int
    last_updated: str

class ComponentHealthItem(BaseModel):
    component: str
    health_score: float
    colour: str
    shap_contribution: float
    spare_part_id: Optional[str] = None
    spare_part_name: Optional[str] = None
    qty_in_stock_at_base: Optional[int] = 0
    lead_time_days: Optional[int] = 0

class ShapFeatureItem(BaseModel):
    sensor: str
    contribution: float
    component: str

class RulTrendPoint(BaseModel):
    cycle: int
    predicted_rul: int
    critical_threshold: int = 15
    warning_threshold: int = 40

class MaintenanceRecordItem(BaseModel):
    record_id: str
    date: str
    maintenance_type: str
    category: str
    downtime_hours: int
    fault_found: Optional[str] = None
    cost_inr_lakh: float
    technician_id: str

class EngineDetailResponse(BaseModel):
    engine_id: str
    aircraft_id: str
    aircraft_type: str
    engine_config: str
    base_id: str
    base_name: str
    position: int
    engine_model: str
    install_date: str
    cycles_since_new: int
    hours_since_overhaul: int
    health_score: float
    status: str
    predicted_rul_cycles: int
    anomaly_score: float
    failure_risk_7d: float
    last_updated: str
    components: List[ComponentHealthItem]
    shap_top_features: List[ShapFeatureItem]
    rul_trend: List[RulTrendPoint]
    recent_sensor_history: List[Dict[str, Any]]
    maintenance_history: List[MaintenanceRecordItem]
