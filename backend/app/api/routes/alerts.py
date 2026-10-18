from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.database import get_db
from backend.app.core.auth import require_any_authenticated, require_maintenance_or_above
from backend.app.models import Alert, WorkOrder, Engine, Aircraft
from backend.app.schemas.alert import (
    AlertResponse,
    AlertListResponse,
    AlertSummary,
    AlertUpdateRequest,
    CreateWorkOrderFromAlertRequest,
)
from backend.app.services.audit import log_audit

router = APIRouter(prefix="/alerts", tags=["Alerts"])

RECOMMENDED_ACTIONS = {
    "Vibration > limit": "Immediate borescope inspection of shaft bearings & fan balance check",
    "EGT margin low": "Turbine wash & thermal barrier coating integrity inspection",
    "Low RUL": "Schedule depot-level overhaul and allocate spare engine module",
    "Anomaly score high": "Full diagnostic sensor checkout & vibration spectral analysis",
    "Oil pressure drop": "Inspect lubrication lines, scavenge pump, and oil filter element",
    "Pressure deviation": "Check bleed valves and high-pressure compressor stage seal rings",
}

@router.get("", response_model=AlertListResponse)
def list_alerts(
    severity: Optional[str] = Query(None, description="High, Medium, Low"),
    status: Optional[str] = Query(None, description="Unacknowledged, Acknowledged, In Progress, Resolved"),
    engine_id: Optional[str] = Query(None, description="Filter by engine"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    query = db.query(Alert)

    if severity:
        query = query.filter(Alert.severity == severity)
    if status:
        query = query.filter(Alert.status == status)
    if engine_id:
        query = query.filter(Alert.engine_id == engine_id)

    query = query.order_by(desc(Alert.timestamp))
    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()

    # Calculate overall summary counts across all alerts
    all_alerts = db.query(Alert).all()
    unack = sum(1 for a in all_alerts if a.status == "Unacknowledged")
    in_prog = sum(1 for a in all_alerts if a.status == "In Progress")
    res = sum(1 for a in all_alerts if a.status == "Resolved")
    high = sum(1 for a in all_alerts if a.severity in ("High", "Critical"))
    med = sum(1 for a in all_alerts if a.severity in ("Medium", "Warning"))

    summary = AlertSummary(
        total=len(all_alerts),
        unacknowledged=unack,
        in_progress=in_prog,
        resolved=res,
        high_severity=high,
        medium_severity=med,
    )

    alert_responses = []
    for a in records:
        rec_action = RECOMMENDED_ACTIONS.get(a.trigger, "Follow standard operating procedures and inspect component.")
        alert_responses.append(AlertResponse(
            alert_id=a.alert_id,
            timestamp=a.timestamp,
            engine_id=a.engine_id,
            aircraft_id=a.aircraft_id,
            severity=a.severity,
            trigger=a.trigger,
            anomaly_score=a.anomaly_score,
            rul_cycles=a.rul_cycles,
            status=a.status,
            source=a.source,
            assigned_to=a.assigned_to,
            work_order_id=a.work_order_id,
            recommended_action=rec_action,
        ))

    return AlertListResponse(
        alerts=alert_responses,
        total=total,
        page=page,
        page_size=page_size,
        summary=summary,
    )

@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    a = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert {alert_id} not found")

    rec_action = RECOMMENDED_ACTIONS.get(a.trigger, "Perform detailed technical evaluation.")
    return AlertResponse(
        alert_id=a.alert_id,
        timestamp=a.timestamp,
        engine_id=a.engine_id,
        aircraft_id=a.aircraft_id,
        severity=a.severity,
        trigger=a.trigger,
        anomaly_score=a.anomaly_score,
        rul_cycles=a.rul_cycles,
        status=a.status,
        source=a.source,
        assigned_to=a.assigned_to,
        work_order_id=a.work_order_id,
        recommended_action=rec_action,
    )

@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: str,
    req: AlertUpdateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    a = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert {alert_id} not found")

    old_status = a.status
    if req.status:
        a.status = req.status
    if req.assigned_to is not None:
        a.assigned_to = req.assigned_to

    db.commit()
    db.refresh(a)

    log_audit(
        db,
        current_user.service_id,
        current_user.role,
        "UPDATE_ALERT",
        "ALERT",
        alert_id,
        f"Updated status from '{old_status}' to '{a.status}', assigned to '{a.assigned_to}'",
    )

    rec_action = RECOMMENDED_ACTIONS.get(a.trigger, "Proceed with maintenance response.")
    return AlertResponse(
        alert_id=a.alert_id,
        timestamp=a.timestamp,
        engine_id=a.engine_id,
        aircraft_id=a.aircraft_id,
        severity=a.severity,
        trigger=a.trigger,
        anomaly_score=a.anomaly_score,
        rul_cycles=a.rul_cycles,
        status=a.status,
        source=a.source,
        assigned_to=a.assigned_to,
        work_order_id=a.work_order_id,
        recommended_action=rec_action,
    )

@router.post("/{alert_id}/work-order")
def create_work_order_from_alert(
    alert_id: str,
    req: CreateWorkOrderFromAlertRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    a = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert {alert_id} not found")

    eng = db.query(Engine).filter(Engine.engine_id == a.engine_id).first()
    air = db.query(Aircraft).filter(Aircraft.aircraft_id == a.aircraft_id).first() if eng else None
    base_id = air.base_id if air else "BASE01"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    wo_count = db.query(WorkOrder).count() + 1
    wo_id = f"WO-{datetime.now().year}-{wo_count:04d}"

    task_desc = req.task_description or f"Address trigger: {a.trigger}. Alert ID: {a.alert_id}. Target Engine: {a.engine_id} ({a.aircraft_id})."
    prio = req.priority or ("Critical" if a.severity == "High" else "Medium")

    wo = WorkOrder(
        work_order_id=wo_id,
        alert_id=a.alert_id,
        engine_id=a.engine_id,
        aircraft_id=a.aircraft_id,
        base_id=base_id,
        status="Approved",
        priority=prio,
        task_description=task_desc,
        assigned_technician=req.assigned_technician or "TECH-LEAD",
        estimated_downtime_hours=req.estimated_downtime_hours or 24,
        created_at=now_str,
        approved_at=now_str,
        approved_by=current_user.service_id,
    )
    db.add(wo)

    # Update alert
    a.work_order_id = wo_id
    a.status = "In Progress"
    db.commit()

    log_audit(
        db,
        current_user.service_id,
        current_user.role,
        "CREATE_WORK_ORDER",
        "WORK_ORDER",
        wo_id,
        f"Created work order {wo_id} from alert {alert_id}",
    )

    return {
        "status": "success",
        "message": f"Work order {wo_id} successfully created and linked to alert {alert_id}",
        "work_order_id": wo_id,
        "alert_id": alert_id,
    }
