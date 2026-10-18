from typing import Optional, List, Dict, Any
from pathlib import Path
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from backend.app.database import get_db
from backend.app.core.auth import require_any_authenticated
from backend.app.models import (
    Engine,
    Aircraft,
    BaseAgency,
    EngineHealthStatus,
    ComponentHealth,
    MaintenanceHistory,
    SparesInventory,
)
from backend.app.schemas.engine import (
    EngineListItem,
    EngineDetailResponse,
    ComponentHealthItem,
    ShapFeatureItem,
    RulTrendPoint,
    MaintenanceRecordItem,
)
from ml.inference import explain_engine
from backend.app.config import settings

router = APIRouter(prefix="/engines", tags=["Engines"])

# Linked spare parts for each component
COMPONENT_PART_MAP = {
    "Fan": "PRT-001",                 # Fan Blade Set
    "Compressor": "PRT-002",          # Compressor Rotor
    "Combustion Chamber": "PRT-003",  # Combustor Liner
    "Turbine": "PRT-004",             # Turbine Blade Set
    "Shaft": "PRT-005",               # Main Shaft Bearing
}

@router.get("", response_model=Dict[str, Any])
def list_engines(
    status: Optional[str] = Query(None, description="Filter by status: Healthy, Watch, Critical"),
    base_id: Optional[str] = Query(None, description="Filter by Base ID"),
    aircraft_type: Optional[str] = Query(None, description="Filter by Aircraft Type"),
    q: Optional[str] = Query(None, description="Search engine ID or aircraft tail"),
    sort_by: Optional[str] = Query("health_score", description="Sort by field"),
    sort_order: Optional[str] = Query("asc", description="asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    query = (
        db.query(Engine, EngineHealthStatus, Aircraft, BaseAgency)
        .join(EngineHealthStatus, Engine.engine_id == EngineHealthStatus.engine_id)
        .join(Aircraft, Engine.aircraft_id == Aircraft.aircraft_id)
        .join(BaseAgency, Aircraft.base_id == BaseAgency.base_id)
    )

    if status:
        query = query.filter(EngineHealthStatus.status == status)
    if base_id:
        query = query.filter(Aircraft.base_id == base_id)
    if aircraft_type:
        query = query.filter(Aircraft.aircraft_type == aircraft_type)
    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            (Engine.engine_id.ilike(search_pattern)) | (Aircraft.aircraft_id.ilike(search_pattern))
        )

    # Sorting
    if sort_by == "health_score":
        sort_col = EngineHealthStatus.health_score
    elif sort_by == "predicted_rul_cycles":
        sort_col = EngineHealthStatus.predicted_rul_cycles
    elif sort_by == "anomaly_score":
        sort_col = EngineHealthStatus.anomaly_score
    else:
        sort_col = Engine.engine_id

    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(asc(sort_col))

    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for eng, h_status, air, base in records:
        items.append(EngineListItem(
            engine_id=eng.engine_id,
            aircraft_id=eng.aircraft_id,
            aircraft_type=air.aircraft_type,
            base_id=air.base_id,
            base_name=base.base_name,
            position=eng.position,
            engine_model=eng.engine_model,
            health_score=h_status.health_score,
            status=h_status.status,
            predicted_rul_cycles=h_status.predicted_rul_cycles,
            anomaly_score=h_status.anomaly_score,
            failure_risk_7d=h_status.failure_risk_7d,
            cycles_since_new=eng.cycles_since_new,
            hours_since_overhaul=eng.hours_since_overhaul,
            last_updated=h_status.last_updated,
        ))

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }

@router.get("/{engine_id}", response_model=EngineDetailResponse)
def get_engine_detail(
    engine_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    eng = db.query(Engine).filter(Engine.engine_id == engine_id).first()
    if not eng:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Engine {engine_id} not found")

    h_status = db.query(EngineHealthStatus).filter(EngineHealthStatus.engine_id == engine_id).first()
    air = db.query(Aircraft).filter(Aircraft.aircraft_id == eng.aircraft_id).first()
    base = db.query(BaseAgency).filter(BaseAgency.base_id == air.base_id).first() if air else None

    # Fetch Components & Spares at base
    comps = db.query(ComponentHealth).filter(ComponentHealth.engine_id == engine_id).all()
    spares = db.query(SparesInventory).filter(SparesInventory.base_id == air.base_id).all() if air else []
    spares_by_part = {s.part_id: s for s in spares}

    comp_items = []
    for c in comps:
        part_id = COMPONENT_PART_MAP.get(c.component)
        part = spares_by_part.get(part_id)
        comp_items.append(ComponentHealthItem(
            component=c.component,
            health_score=c.health_score,
            colour=c.colour,
            shap_contribution=c.shap_contribution,
            spare_part_id=part_id,
            spare_part_name=part.part_name if part else None,
            qty_in_stock_at_base=part.qty_in_stock if part else 0,
            lead_time_days=part.lead_time_days if part else 0,
        ))

    # Maintenance History
    m_records = db.query(MaintenanceHistory).filter(MaintenanceHistory.engine_id == engine_id).order_by(desc(MaintenanceHistory.date)).limit(10).all()
    maint_items = [
        MaintenanceRecordItem(
            record_id=m.record_id,
            date=m.date.strftime("%Y-%m-%d"),
            maintenance_type=m.maintenance_type,
            category=m.category,
            downtime_hours=m.downtime_hours,
            fault_found=m.fault_found,
            cost_inr_lakh=m.cost_inr_lakh,
            technician_id=m.technician_id,
        )
        for m in m_records
    ]

    # RUL Trend projection points
    current_rul = h_status.predicted_rul_cycles if h_status else 100
    rul_trend = []
    # 10 historical cycles + 10 future projected cycles
    for i in range(-10, 11):
        c_num = max(1, eng.cycles_since_new + i)
        proj_rul = max(0, current_rul - i * 2)
        rul_trend.append(RulTrendPoint(
            cycle=c_num,
            predicted_rul=proj_rul,
            critical_threshold=15,
            warning_threshold=40,
        ))

    # SHAP Top features
    shap_explanation = explain_engine(pd.DataFrame())
    shap_items = [
        ShapFeatureItem(
            sensor=s["sensor"],
            contribution=s["contribution"],
            component=s["component"]
        )
        for s in shap_explanation.get("top_5_sensors", [])
    ]

    # Recent sensor history from live simulation or generated series
    live_csv = Path(__file__).resolve().parent.parent.parent.parent / settings.DATA_DIR / "live_stream_simulation.csv"
    sensor_history = []
    if live_csv.exists():
        try:
            live_df = pd.read_csv(live_csv)
            eng_live = live_df[live_df["engine_id"] == engine_id].tail(30)
            if not eng_live.empty:
                sensor_history = eng_live.to_dict(orient="records")
        except Exception:
            pass

    if not sensor_history:
        # Generate nominal points for visualization
        base_h = h_status.health_score if h_status else 80.0
        sev = (100.0 - base_h) / 100.0
        for k in range(20):
            sensor_history.append({
                "timestamp": f"2026-10-11 09:{k:02d}:00",
                "engine_id": engine_id,
                "temp_c": round(480.0 + 50.0 * sev + (k * 0.2), 1),
                "pressure_kpa": round(98.5 + 20.0 * sev, 1),
                "vibration_mm_s": round(2.0 + 4.5 * sev, 2),
                "fan_rpm": 8950 + (k % 5),
                "oil_pressure_psi": round(55.0 - 10.0 * sev, 1),
                "egt_c": round(620.0 + 65.0 * sev, 1),
            })

    return EngineDetailResponse(
        engine_id=eng.engine_id,
        aircraft_id=eng.aircraft_id,
        aircraft_type=air.aircraft_type if air else "Unknown",
        engine_config=air.engine_config if air else "Unknown",
        base_id=air.base_id if air else "Unknown",
        base_name=base.base_name if base else "Unknown",
        position=eng.position,
        engine_model=eng.engine_model,
        install_date=eng.install_date.strftime("%Y-%m-%d") if eng.install_date else "",
        cycles_since_new=eng.cycles_since_new,
        hours_since_overhaul=eng.hours_since_overhaul,
        health_score=h_status.health_score if h_status else 75.0,
        status=h_status.status if h_status else "Healthy",
        predicted_rul_cycles=h_status.predicted_rul_cycles if h_status else 100,
        anomaly_score=h_status.anomaly_score if h_status else 0.15,
        failure_risk_7d=h_status.failure_risk_7d if h_status else 0.05,
        last_updated=h_status.last_updated if h_status else "",
        components=comp_items,
        shap_top_features=shap_items,
        rul_trend=rul_trend,
        recent_sensor_history=sensor_history,
        maintenance_history=maint_items,
    )

@router.get("/{engine_id}/components", response_model=List[ComponentHealthItem])
def get_engine_components(
    engine_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    eng = db.query(Engine).filter(Engine.engine_id == engine_id).first()
    if not eng:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Engine {engine_id} not found")

    air = db.query(Aircraft).filter(Aircraft.aircraft_id == eng.aircraft_id).first()
    comps = db.query(ComponentHealth).filter(ComponentHealth.engine_id == engine_id).all()
    spares = db.query(SparesInventory).filter(SparesInventory.base_id == air.base_id).all() if air else []
    spares_by_part = {s.part_id: s for s in spares}

    comp_items = []
    for c in comps:
        part_id = COMPONENT_PART_MAP.get(c.component)
        part = spares_by_part.get(part_id)
        comp_items.append(ComponentHealthItem(
            component=c.component,
            health_score=c.health_score,
            colour=c.colour,
            shap_contribution=c.shap_contribution,
            spare_part_id=part_id,
            spare_part_name=part.part_name if part else None,
            qty_in_stock_at_base=part.qty_in_stock if part else 0,
            lead_time_days=part.lead_time_days if part else 0,
        ))

    return comp_items
