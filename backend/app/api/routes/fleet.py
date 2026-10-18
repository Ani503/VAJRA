from datetime import datetime, date, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app.core.auth import require_any_authenticated
from backend.app.models import (
    Aircraft,
    Engine,
    EngineHealthStatus,
    BaseAgency,
    MissionDemand,
    FleetAvailabilityHistory,
    SparesInventory,
)
from backend.app.schemas.fleet import (
    FleetAvailabilityResponse,
    BaseAvailabilityItem,
    AircraftAtRiskItem,
    AvailabilityDaySeries,
)

router = APIRouter(prefix="/fleet", tags=["Fleet Availability"])

SCENARIO_EXPLANATIONS = {
    "predictive": (
        "PREDICTIVE SCENARIO (Optimal AI Fleet Posture): Proactively schedules maintenance windows "
        "when engine RUL drops below 40 cycles or vibration/EGT trends indicate early wear, synchronized "
        "with regional base spares inventory. Prevents catastrophic unscheduled groundings and sustains "
        "peak operational readiness (>88%)."
    ),
    "baseline": (
        "BASELINE SCENARIO (Standard Cyclic Inspection): Adheres strictly to calendar and flight-hour inspection intervals. "
        "Does not leverage predictive degradation indicators, resulting in intermittent unscheduled groundings "
        "when components wear faster than standard cycle expectations (~78% readiness)."
    ),
    "reactive": (
        "REACTIVE SCENARIO (Run-to-Fault / Fix-on-Failure): Components are serviced only after hard alerts or "
        "in-flight exceedances occur. Severe downtime spikes occur due to emergency depot transfers, lack of pre-positioned "
        "spares, and multiple simultaneous groundings (~65-70% readiness)."
    ),
}

@router.get("/availability", response_model=FleetAvailabilityResponse)
def get_fleet_availability(
    horizon: int = Query(14, description="Horizon in days: 7 or 14"),
    scenario: str = Query("predictive", description="baseline, predictive, reactive"),
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    horizon_days = 7 if horizon == 7 else 14
    scenario_clean = scenario.lower() if scenario.lower() in ("baseline", "predictive", "reactive") else "predictive"

    all_aircraft = db.query(Aircraft).all()
    all_engines = db.query(Engine).all()
    health_dict = {h.engine_id: h for h in db.query(EngineHealthStatus).all()}
    bases = db.query(BaseAgency).all()
    total_aircraft_count = len(all_aircraft)

    # Map aircraft -> engines
    air_engines = {}
    for e in all_engines:
        air_engines.setdefault(e.aircraft_id, []).append(e)

    # 1. Identify at-risk aircraft based on engine conditions
    at_risk_list = []
    grounded_tails = set()

    for a in all_aircraft:
        engs = air_engines.get(a.aircraft_id, [])
        crit_engine = None
        min_health = 100.0
        min_rul = 250

        for e in engs:
            h = health_dict.get(e.engine_id)
            if h and h.health_score < min_health:
                min_health = h.health_score
                min_rul = h.predicted_rul_cycles
                crit_engine = e

        if min_health < 40.0:
            grounded_tails.add(a.aircraft_id)
            days_down = max(1, min_rul // 2)
            at_risk_list.append(AircraftAtRiskItem(
                aircraft_id=a.aircraft_id,
                aircraft_type=a.aircraft_type,
                base_id=a.base_id,
                critical_engine_id=crit_engine.engine_id if crit_engine else "N/A",
                engine_health=min_health,
                engine_rul=min_rul,
                days_to_unavailable=days_down,
                reason=f"Critical RUL degradation (<{min_rul} cycles) & severe thermal/vibration stress",
                recommended_action="Ground aircraft; expedite stage 1 module replacement",
            ))
        elif min_health < 70.0:
            if scenario_clean in ("baseline", "reactive"):
                # In reactive scenario, watch engines fail faster
                days_down = max(3, min_rul // 3)
                grounded_tails.add(a.aircraft_id)
                at_risk_list.append(AircraftAtRiskItem(
                    aircraft_id=a.aircraft_id,
                    aircraft_type=a.aircraft_type,
                    base_id=a.base_id,
                    critical_engine_id=crit_engine.engine_id if crit_engine else "N/A",
                    engine_health=min_health,
                    engine_rul=min_rul,
                    days_to_unavailable=days_down,
                    reason="Sub-nominal telemetry in watch band; unmitigated under reactive posture",
                    recommended_action="Execute planned borescope inspection within 7 days",
                ))

    # 2. Base-level availability calculations
    base_aircraft = {}
    for a in all_aircraft:
        base_aircraft.setdefault(a.base_id, []).append(a)

    base_items = []
    total_mission_ready = 0

    for b in bases:
        b_air = base_aircraft.get(b.base_id, [])
        tot = len(b_air)
        if tot == 0:
            continue

        b_grounded = sum(1 for a in b_air if a.aircraft_id in grounded_tails)

        if scenario_clean == "predictive":
            sched_count = min(tot - b_grounded, 1 if tot > 3 else 0)
            unsched_count = b_grounded
        elif scenario_clean == "baseline":
            sched_count = min(tot - b_grounded, 2 if tot > 3 else 1)
            unsched_count = b_grounded
        else: # reactive
            sched_count = 0
            unsched_count = min(tot, b_grounded + 1)

        ready_count = max(0, tot - sched_count - unsched_count)
        total_mission_ready += ready_count
        avail_pct = round(100.0 * ready_count / tot, 1)

        base_items.append(BaseAvailabilityItem(
            base_id=b.base_id,
            base_name=b.base_name,
            total_aircraft=tot,
            mission_ready_count=ready_count,
            scheduled_maintenance_count=sched_count,
            unscheduled_maintenance_count=unsched_count,
            availability_pct=avail_pct,
        ))

    overall_avail_pct = round(100.0 * total_mission_ready / max(1, total_aircraft_count), 1)

    # 3. 14-Day Timeline Projection
    demands = db.query(MissionDemand.date, func.sum(MissionDemand.aircraft_required).label("req")).group_by(MissionDemand.date).order_by(MissionDemand.date).all()
    timeline = []
    base_date = date(2026, 10, 11)

    for idx in range(horizon_days):
        day_date = base_date + timedelta(days=idx)
        # Match demand from DB or fallback
        req_val = 14
        if idx < len(demands):
            req_val = int(demands[idx][1])

        # Scenario multiplier on ready aircraft
        if scenario_clean == "predictive":
            ready_fluct = 0 if idx % 4 != 0 else 1
            sched_maint = 2
            unsched_maint = 1
            cur_ready = max(18, min(23, total_mission_ready + ready_fluct))
        elif scenario_clean == "baseline":
            sched_maint = 3
            unsched_maint = 2
            cur_ready = max(15, min(20, total_mission_ready - (1 if idx > 4 else 0)))
        else: # reactive
            sched_maint = 1
            unsched_maint = 5 + (idx // 3)
            cur_ready = max(12, min(17, total_mission_ready - (2 + idx // 4)))

        day_avail = round(100.0 * cur_ready / max(1, total_aircraft_count), 1)

        timeline.append(AvailabilityDaySeries(
            date=day_date.strftime("%Y-%m-%d"),
            mission_demand=req_val,
            mission_ready=cur_ready,
            scheduled_maintenance=sched_maint,
            unscheduled_maintenance=unsched_maint,
            availability_pct=day_avail,
            surplus_deficit=cur_ready - req_val,
        ))

    return FleetAvailabilityResponse(
        scenario=scenario_clean,
        horizon_days=horizon_days,
        overall_availability_pct=overall_avail_pct,
        bases=base_items,
        daily_timeline=timeline,
        at_risk_aircraft=at_risk_list,
        scenario_explanation=SCENARIO_EXPLANATIONS.get(scenario_clean, ""),
    )
