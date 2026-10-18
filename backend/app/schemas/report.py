from pydantic import BaseModel
from typing import Optional, List

class CreateReportRequest(BaseModel):
    report_type: str  # daily_fleet_health, weekly_maintenance, alert_log, spares_risk
    format: str = "pdf"  # pdf, csv
    base_id: Optional[str] = None
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None

class ReportResponse(BaseModel):
    report_id: str
    report_type: str
    title: str
    format: str
    base_id: Optional[str] = None
    date_range_start: str
    date_range_end: str
    generated_by: str
    created_at: str
    file_path: str
