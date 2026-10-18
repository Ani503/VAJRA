from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class AlertResponse(BaseModel):
    alert_id: str
    timestamp: str
    engine_id: str
    aircraft_id: str
    severity: str
    trigger: str
    anomaly_score: float
    rul_cycles: int
    status: str
    source: str
    assigned_to: Optional[str] = None
    work_order_id: Optional[str] = None
    recommended_action: Optional[str] = None

class AlertSummary(BaseModel):
    unacknowledged: int
    in_progress: int
    resolved: int
    total: int
    high_severity: int
    medium_severity: int

class AlertListResponse(BaseModel):
    alerts: List[AlertResponse]
    total: int
    page: int
    page_size: int
    summary: AlertSummary

class AlertUpdateRequest(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None

class CreateWorkOrderFromAlertRequest(BaseModel):
    task_description: Optional[str] = None
    assigned_technician: Optional[str] = None
    estimated_downtime_hours: Optional[int] = 24
    priority: Optional[str] = None
