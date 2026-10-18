from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class SystemStatusResponse(BaseModel):
    database_connected: bool
    live_feed_status: str
    models_loaded: bool
    ml_enabled: bool
    offline_mode: bool
    last_sync: str
    total_engines: int
    total_aircraft: int
    active_alerts: int

class SimulatorStateResponse(BaseModel):
    is_running: bool
    speed: float
    current_step: int
    total_steps: int
    active_faults: Dict[str, Any]
    last_updated: str

class InjectFaultRequest(BaseModel):
    type: str  # vibration_spike, egt_rise, oil_pressure_drop
    engine_id: str
    severity: str = "critical"  # low, medium, critical

class SimulatorSpeedRequest(BaseModel):
    speed: float = 1.0

class RuleThresholdItem(BaseModel):
    id: Optional[int] = None
    parameter: str
    operator: str
    threshold: float
    severity: str
    recommended_action: str

class AuditLogItem(BaseModel):
    id: int
    timestamp: str
    user_id: str
    user_role: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    details: Optional[str] = None
    prev_hash: Optional[str] = None
    entry_hash: Optional[str] = None

class AuditVerificationResponse(BaseModel):
    verified: bool
    status: str
    total_records: int
    genesis_hash: str
    latest_hash: Optional[str] = None
    failed_at_id: Optional[int] = None
    detail: Optional[str] = None

