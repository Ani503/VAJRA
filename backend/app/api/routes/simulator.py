from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.auth import require_maintenance_or_above, require_any_authenticated
from backend.app.services.simulator import sim_manager
from backend.app.schemas.system import SimulatorStateResponse, InjectFaultRequest, SimulatorSpeedRequest
from backend.app.services.audit import log_audit
from backend.app.models import Engine

router = APIRouter(prefix="/simulator", tags=["Simulator"])

@router.post("/start")
def start_simulator(
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    sim_manager.start()
    log_audit(db, current_user.service_id, current_user.role, "START_SIMULATOR", "SIMULATOR", "LIVE_FEED", "Started telemetry replay")
    return {"status": "success", "message": "Telemetry simulation started"}

@router.post("/stop")
def stop_simulator(
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    sim_manager.stop()
    log_audit(db, current_user.service_id, current_user.role, "STOP_SIMULATOR", "SIMULATOR", "LIVE_FEED", "Stopped telemetry replay")
    return {"status": "success", "message": "Telemetry simulation stopped"}

@router.post("/speed")
def set_simulator_speed(
    req: SimulatorSpeedRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    sim_manager.set_speed(req.speed)
    log_audit(db, current_user.service_id, current_user.role, "SET_SIMULATOR_SPEED", "SIMULATOR", "SPEED", f"Set speed to {req.speed}x")
    return {"status": "success", "speed": sim_manager.speed}

@router.post("/inject-fault")
def inject_fault(
    req: InjectFaultRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    valid_types = ("vibration_spike", "egt_rise", "oil_pressure_drop")
    if req.type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid fault type '{req.type}'. Allowed: {valid_types}"
        )

    # Check that engine exists
    eng = db.query(Engine).filter(Engine.engine_id == req.engine_id).first()
    if not eng:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engine {req.engine_id} not found in fleet (must be one of 42 fleet engines)"
        )

    fault_info = sim_manager.inject_fault(
        engine_id=req.engine_id,
        fault_type=req.type,
        severity=req.severity,
    )

    log_audit(
        db,
        current_user.service_id,
        current_user.role,
        "INJECT_FAULT",
        "ENGINE",
        req.engine_id,
        f"Injected {req.type} ({req.severity}) on {req.engine_id}",
    )

    return {
        "status": "success",
        "engine_id": req.engine_id,
        "fault": fault_info,
        "message": f"Successfully injected {req.type} fault into {req.engine_id}",
    }

@router.get("/state", response_model=SimulatorStateResponse)
def get_simulator_state(
    current_user = Depends(require_any_authenticated),
):
    return SimulatorStateResponse(
        is_running=sim_manager.is_running,
        speed=sim_manager.speed,
        current_step=sim_manager.current_step,
        total_steps=sim_manager.total_steps,
        active_faults=sim_manager.active_faults,
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

@router.post("/reset")
def reset_simulator(
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    """
    Restores the 42/27/12/3 fleet health invariants, clears active simulated faults,
    and removes synthetic live alerts and tasks.
    """
    sim_manager.reset(db)
    log_audit(
        db,
        current_user.service_id,
        current_user.role,
        "RESET_SIMULATOR",
        "FLEET_HEALTH",
        "42_ENGINES",
        "Restored baseline invariants (27 Healthy, 12 Watch, 3 Critical) and purged simulated items",
    )
    return {
        "status": "success",
        "message": "Fleet state reset to baseline invariants (27 Healthy, 12 Watch, 3 Critical)",
        "invariants": {
            "total_engines": 42,
            "healthy_engines": 27,
            "watch_engines": 12,
            "critical_engines": 3,
            "total_aircraft": 24,
            "total_bases": 5,
        }
    }
