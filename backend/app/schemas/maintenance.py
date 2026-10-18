from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class MaintenanceTaskResponse(BaseModel):
    task_id: str
    engine_id: str
    aircraft_id: str
    base_id: str
    component: str
    required_part_id: Optional[str] = None
    maintenance_type: str
    urgency: str
    status: str
    scheduled_date: Optional[str] = None
    estimated_downtime_hours: int
    created_at: str

class CreateMaintenanceTaskRequest(BaseModel):
    engine_id: str
    component: str
    maintenance_type: str
    urgency: str
    required_part_id: Optional[str] = None
    scheduled_date: Optional[str] = None
    estimated_downtime_hours: Optional[int] = 12

class BaseScheduleDay(BaseModel):
    date: str
    daily_slots_total: int
    daily_slots_used: int
    hangar_bays_total: int
    hangar_bays_used: int
    tasks: List[MaintenanceTaskResponse]

class BaseScheduleView(BaseModel):
    base_id: str
    base_name: str
    days: List[BaseScheduleDay]

class MaintenanceScheduleResponse(BaseModel):
    week_start: str
    week_end: str
    bases: List[BaseScheduleView]

class TaskAssignment(BaseModel):
    task_id: str
    engine_id: str
    base_id: str
    component: str
    scheduled_date: str
    part_available: bool
    part_id: Optional[str] = None
    urgency: str
    priority_score: float

class MaintenanceOptimiseResponse(BaseModel):
    assignments: List[TaskAssignment]
    conflicts: List[str]
    capacity_utilization_pct: float
    summary: str

class ApproveMaintenanceRequest(BaseModel):
    task_ids: List[str]
    notes: Optional[str] = None
