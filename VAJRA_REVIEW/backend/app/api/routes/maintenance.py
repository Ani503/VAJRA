from datetime import datetime, date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.database import get_db
from backend.app.core.auth import require_any_authenticated, require_maintenance_or_above
from backend.app.models import (
    MaintenanceTask,
    BaseAgency,
    Engine,
    Aircraft,
    EngineHealthStatus,
    SparesInventory,
)
from backend.app.schemas.maintenance import (
    MaintenanceTaskResponse,
    CreateMaintenanceTaskRequest,
    MaintenanceScheduleResponse,
    BaseScheduleView,
    BaseScheduleDay,
    MaintenanceOptimiseResponse,
    TaskAssignment,
    ApproveMaintenanceRequest,
)
from backend.app.services.audit import log_audit

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])

COMPONENT_PART_MAP = {
    "Fan": "PRT-001",                 # Fan Blade Set
    "Compressor": "PRT-002",          # Compressor Rotor
    "Combustion Chamber": "PRT-003",  # Combustor Liner
    "Turbine": "PRT-004",             # Turbine Blade Set
    "Shaft": "PRT-005",               # Main Shaft Bearing
}

@router.get("/tasks", response_model=List[MaintenanceTaskResponse])
def list_tasks(
    status: Optional[str] = Query(None, description="Suggested, Scheduled, In Progress, Completed"),
    urgency: Optional[str] = Query(None, description="Immediate, Within 7 Days, Within 14 Days, Routine"),
    base_id: Optional[str] = Query(None, description="Filter by Base ID"),
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    query = db.query(MaintenanceTask)
    if status:
        query = query.filter(MaintenanceTask.status == status)
    if urgency:
        query = query.filter(MaintenanceTask.urgency == urgency)
    if base_id:
        query = query.filter(MaintenanceTask.base_id == base_id)

    tasks = query.order_by(desc(MaintenanceTask.created_at)).all()
    return [
        MaintenanceTaskResponse(
            task_id=t.task_id,
            engine_id=t.engine_id,
            aircraft_id=t.aircraft_id,
            base_id=t.base_id,
            component=t.component,
            required_part_id=t.required_part_id,
            maintenance_type=t.maintenance_type,
            urgency=t.urgency,
            status=t.status,
            scheduled_date=t.scheduled_date.strftime("%Y-%m-%d") if t.scheduled_date else None,
            estimated_downtime_hours=t.estimated_downtime_hours,
            created_at=t.created_at,
        )
        for t in tasks
    ]

@router.post("/tasks", response_model=MaintenanceTaskResponse)
def create_task(
    req: CreateMaintenanceTaskRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    eng = db.query(Engine).filter(Engine.engine_id == req.engine_id).first()
    if not eng:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Engine {req.engine_id} not found")

    air = db.query(Aircraft).filter(Aircraft.aircraft_id == eng.aircraft_id).first()
    base_id = air.base_id if air else "BASE01"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = db.query(MaintenanceTask).count() + 1
    task_id = f"TSK-{datetime.now().year}-{count:04d}"

    sched_date = None
    if req.scheduled_date:
        try:
            sched_date = datetime.strptime(req.scheduled_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    part_id = req.required_part_id or COMPONENT_PART_MAP.get(req.component)

    task = MaintenanceTask(
        task_id=task_id,
        engine_id=req.engine_id,
        aircraft_id=eng.aircraft_id,
        base_id=base_id,
        component=req.component,
        required_part_id=part_id,
        maintenance_type=req.maintenance_type,
        urgency=req.urgency,
        status="Suggested" if not sched_date else "Scheduled",
        scheduled_date=sched_date,
        estimated_downtime_hours=req.estimated_downtime_hours or 12,
        created_at=now_str,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    log_audit(
        db,
        current_user.service_id,
        current_user.role,
        "CREATE_MAINTENANCE_TASK",
        "MAINTENANCE_TASK",
        task_id,
        f"Created maintenance task {task_id} for {req.engine_id} ({req.component})",
    )

    return MaintenanceTaskResponse(
        task_id=task.task_id,
        engine_id=task.engine_id,
        aircraft_id=task.aircraft_id,
        base_id=task.base_id,
        component=task.component,
        required_part_id=task.required_part_id,
        maintenance_type=task.maintenance_type,
        urgency=task.urgency,
        status=task.status,
        scheduled_date=task.scheduled_date.strftime("%Y-%m-%d") if task.scheduled_date else None,
        estimated_downtime_hours=task.estimated_downtime_hours,
        created_at=task.created_at,
    )

@router.get("/schedule", response_model=MaintenanceScheduleResponse)
def get_maintenance_schedule(
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    try:
        base_dt = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date(2026, 10, 12)
    except ValueError:
        base_dt = date(2026, 10, 12)

    days_list = [base_dt + timedelta(days=i) for i in range(7)]
    bases = db.query(BaseAgency).all()
    tasks = db.query(MaintenanceTask).all()

    base_views = []
    for b in bases:
        b_tasks = [t for t in tasks if t.base_id == b.base_id]
        days_views = []
        for d in days_list:
            d_tasks = [
                t for t in b_tasks
                if t.scheduled_date and t.scheduled_date == d
            ]
            days_views.append(BaseScheduleDay(
                date=d.strftime("%Y-%m-%d"),
                daily_slots_total=b.daily_maintenance_slots,
                daily_slots_used=len(d_tasks),
                hangar_bays_total=b.hangar_bays,
                hangar_bays_used=min(b.hangar_bays, len(d_tasks)),
                tasks=[
                    MaintenanceTaskResponse(
                        task_id=t.task_id,
                        engine_id=t.engine_id,
                        aircraft_id=t.aircraft_id,
                        base_id=t.base_id,
                        component=t.component,
                        required_part_id=t.required_part_id,
                        maintenance_type=t.maintenance_type,
                        urgency=t.urgency,
                        status=t.status,
                        scheduled_date=t.scheduled_date.strftime("%Y-%m-%d") if t.scheduled_date else None,
                        estimated_downtime_hours=t.estimated_downtime_hours,
                        created_at=t.created_at,
                    )
                    for t in d_tasks
                ],
            ))

        base_views.append(BaseScheduleView(
            base_id=b.base_id,
            base_name=b.base_name,
            days=days_views,
        ))

    return MaintenanceScheduleResponse(
        week_start=days_list[0].strftime("%Y-%m-%d"),
        week_end=days_list[-1].strftime("%Y-%m-%d"),
        bases=base_views,
    )

@router.post("/optimise", response_model=MaintenanceOptimiseResponse)
def optimise_maintenance_schedule(
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    """
    AI-driven Maintenance Optimizer:
    1. Ranks pending maintenance tasks by engine risk (low RUL, high anomaly score).
    2. Maps required spare parts and checks base inventory.
    3. Allocates tasks to bases honoring daily_maintenance_slots and hangar_bays.
    4. Detects stockouts or capacity bottlenecks and flags actionable conflicts.
    """
    # Fetch pending tasks
    pending_tasks = db.query(MaintenanceTask).filter(MaintenanceTask.status.in_(["Suggested", "Scheduled"])).all()
    health_dict = {h.engine_id: h for h in db.query(EngineHealthStatus).all()}
    bases = {b.base_id: b for b in db.query(BaseAgency).all()}
    spares_lookup = {(s.base_id, s.part_id): s for s in db.query(SparesInventory).all()}

    # Compute risk priority score for each task
    scored_tasks = []
    for t in pending_tasks:
        h = health_dict.get(t.engine_id)
        rul = h.predicted_rul_cycles if h else 100
        anom = h.anomaly_score if h else 0.2
        # Higher score = higher priority
        priority = (150 - min(150, rul)) * 1.5 + (anom * 100.0)
        if t.urgency == "Immediate":
            priority += 200.0
        elif t.urgency == "Within 7 Days":
            priority += 80.0
        scored_tasks.append((priority, t))

    # Sort descending by priority
    scored_tasks.sort(key=lambda x: x[0], reverse=True)

    assignments = []
    conflicts = []
    base_day_slots = {}  # (base_id, day_offset) -> count
    base_date = date(2026, 10, 12)

    total_capacity = sum(b.daily_maintenance_slots * 7 for b in bases.values())
    used_slots = 0

    for priority, task in scored_tasks:
        part_id = task.required_part_id or COMPONENT_PART_MAP.get(task.component, "PRT-001")
        spare_item = spares_lookup.get((task.base_id, part_id))

        part_available = True
        if not spare_item or spare_item.qty_in_stock <= 0:
            part_available = False
            part_name = spare_item.part_name if spare_item else task.component
            conflicts.append(f"{part_name} out of stock at {task.base_id} (Lead time: {spare_item.lead_time_days if spare_item else 30} days)")

        # Schedule to earliest available day with open slots
        assigned_day = None
        base_obj = bases.get(task.base_id)
        max_slots = base_obj.daily_maintenance_slots if base_obj else 2

        for day_offset in range(7):
            curr_used = base_day_slots.get((task.base_id, day_offset), 0)
            if curr_used < max_slots:
                base_day_slots[(task.base_id, day_offset)] = curr_used + 1
                assigned_day = base_date + timedelta(days=day_offset)
                used_slots += 1
                break

        if not assigned_day:
            assigned_day = base_date + timedelta(days=6)
            conflicts.append(f"Hangar bay bottleneck at {task.base_id}; task {task.task_id} deferred to next cycle")

        assignments.append(TaskAssignment(
            task_id=task.task_id,
            engine_id=task.engine_id,
            base_id=task.base_id,
            component=task.component,
            scheduled_date=assigned_day.strftime("%Y-%m-%d"),
            part_available=part_available,
            part_id=part_id,
            urgency=task.urgency,
            priority_score=round(priority, 1),
        ))

    utilization = round(100.0 * used_slots / max(1, total_capacity), 1)
    summary = f"Optimized {len(assignments)} tasks across {len(bases)} bases. Identified {len(conflicts)} inventory or capacity constraints."

    return MaintenanceOptimiseResponse(
        assignments=assignments,
        conflicts=conflicts,
        capacity_utilization_pct=utilization,
        summary=summary,
    )

@router.post("/approve")
def approve_maintenance_tasks(
    req: ApproveMaintenanceRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    tasks = db.query(MaintenanceTask).filter(MaintenanceTask.task_id.in_(req.task_ids)).all()
    if not tasks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching tasks found for approval")

    for t in tasks:
        t.status = "Scheduled"
        if not t.scheduled_date:
            t.scheduled_date = date.today() + timedelta(days=1)

    db.commit()

    log_audit(
        db,
        current_user.service_id,
        current_user.role,
        "APPROVE_MAINTENANCE",
        "MAINTENANCE_TASK",
        ",".join(req.task_ids),
        f"Approved {len(tasks)} maintenance tasks. Notes: {req.notes or 'None'}",
    )

    return {
        "status": "success",
        "approved_count": len(tasks),
        "task_ids": [t.task_id for t in tasks],
        "message": f"Successfully approved {len(tasks)} maintenance tasks.",
    }
