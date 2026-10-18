from backend.app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from backend.app.schemas.dashboard import DashboardSummaryResponse, AlertCounts, EngineRiskSummary
from backend.app.schemas.engine import EngineListItem, EngineDetailResponse, ComponentHealthItem
from backend.app.schemas.alert import AlertResponse, AlertListResponse, AlertUpdateRequest, CreateWorkOrderFromAlertRequest
from backend.app.schemas.maintenance import MaintenanceTaskResponse, CreateMaintenanceTaskRequest, MaintenanceScheduleResponse, MaintenanceOptimiseResponse
from backend.app.schemas.spare import SparesOverviewResponse, ReorderSparesRequest, TransferSparesRequest, SparesDemandForecastResponse
from backend.app.schemas.fleet import FleetAvailabilityResponse
from backend.app.schemas.report import CreateReportRequest, ReportResponse
from backend.app.schemas.system import SystemStatusResponse, SimulatorStateResponse, InjectFaultRequest, AuditLogItem

__all__ = [
    "LoginRequest", "TokenResponse", "UserResponse",
    "DashboardSummaryResponse", "AlertCounts", "EngineRiskSummary",
    "EngineListItem", "EngineDetailResponse", "ComponentHealthItem",
    "AlertResponse", "AlertListResponse", "AlertUpdateRequest", "CreateWorkOrderFromAlertRequest",
    "MaintenanceTaskResponse", "CreateMaintenanceTaskRequest", "MaintenanceScheduleResponse", "MaintenanceOptimiseResponse",
    "SparesOverviewResponse", "ReorderSparesRequest", "TransferSparesRequest", "SparesDemandForecastResponse",
    "FleetAvailabilityResponse",
    "CreateReportRequest", "ReportResponse",
    "SystemStatusResponse", "SimulatorStateResponse", "InjectFaultRequest", "AuditLogItem",
]
