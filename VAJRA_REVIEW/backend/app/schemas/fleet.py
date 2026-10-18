from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class BaseAvailabilityItem(BaseModel):
    base_id: str
    base_name: str
    total_aircraft: int
    mission_ready_count: int
    scheduled_maintenance_count: int
    unscheduled_maintenance_count: int
    availability_pct: float

class AircraftAtRiskItem(BaseModel):
    aircraft_id: str
    aircraft_type: str
    base_id: str
    critical_engine_id: str
    engine_health: float
    engine_rul: int
    days_to_unavailable: int
    reason: str  # "Critical RUL degradation (<15 cycles)", "Awaiting Turbine Spares at BASE03", "Periodic Scheduled Inspection Due"
    recommended_action: str

class AvailabilityDaySeries(BaseModel):
    date: str
    mission_demand: int
    mission_ready: int
    scheduled_maintenance: int
    unscheduled_maintenance: int
    availability_pct: float
    surplus_deficit: int

class FleetAvailabilityResponse(BaseModel):
    scenario: str  # baseline, predictive, reactive
    horizon_days: int  # 7, 14
    overall_availability_pct: float
    bases: List[BaseAvailabilityItem]
    daily_timeline: List[AvailabilityDaySeries]
    at_risk_aircraft: List[AircraftAtRiskItem]
    scenario_explanation: str
