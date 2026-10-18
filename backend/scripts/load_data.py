"""
VAJRA Data Loader Script
Builds vajra.db from CSV source files, applies demo overrides,
ensures 42 engines / 27 Healthy / 12 Watch / 3 Critical invariants,
and seeds initial administrative users and system state.
Idempotent: safe to re-run at any time.
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd
from sqlalchemy import text

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import (
    BaseAgency,
    Aircraft,
    Engine,
    EngineHealthStatus,
    ComponentHealth,
    Alert,
    RuleEngineThreshold,
    MaintenanceHistory,
    SparesInventory,
    SpareOrder,
    FleetAvailabilityHistory,
    MissionDemand,
    User,
    AuditLog,
    WorkOrder,
    MaintenanceTask,
    Setting,
    Report,
    SimulatorState,
)
from backend.app.core.security import get_password_hash
from backend.app.services.audit import log_audit

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("load_data")

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = WORKSPACE_DIR / settings.DATA_DIR
SEED_DIR = WORKSPACE_DIR / "backend" / "seed"

def parse_date(val):
    if pd.isna(val) or val is None or str(val).strip() == "":
        return None
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            pass
    return None

def load_all_data():
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1;"))
            conn.commit()
        except Exception:
            pass
    db = SessionLocal()

    try:
        # Clear existing tables in reverse dependency order for clean idempotent reload
        logger.info("Purging old records for idempotent reload...")
        for table in [
            "simulator_state", "reports", "settings", "spare_orders", "work_orders",
            "maintenance_tasks", "audit_log", "users", "mission_demand",
            "fleet_availability_history", "spares_inventory", "maintenance_history",
            "rule_engine_thresholds", "alerts", "component_health",
            "engine_health_status", "engines", "aircraft", "bases"
        ]:
            db.execute(text(f"DELETE FROM {table};"))
        db.commit()

        # Generic naming mappings (PS 26249 strict requirement)
        BASE_NAME_MAP = {
            "BASE01": "Base 01",
            "BASE02": "Base 02",
            "BASE03": "Base 03",
            "BASE04": "Base 04",
            "BASE05": "Base 05",
        }
        AIRCRAFT_TYPE_MAP = {
            "C-17 Globemaster": "Transport-A",
            "Su-30MKI": "Fighter-B",
            "Hawk Mk132": "Trainer-C",
            "LCH Prachand": "Heli-D",
        }
        ENGINE_MODEL_MAP = {
            "AL-31FP": "Turbofan-TF1",
            "Shakti-1H1": "Turboshaft-TS1",
        }

        STATE_MAP = {
            "Haryana": "Sector 01",
            "Maharashtra": "Sector 02",
            "Rajasthan": "Sector 03",
            "Assam": "Sector 04",
            "Karnataka": "Sector 05",
        }
        SUPPLIER_MAP = {
            "GTRE": "Depot-Alpha",
            "HAL": "Depot-Beta",
            "BEL": "Depot-Gamma",
            "Imported OEM": "OEM Supplier",
        }

        # 1. Bases
        logger.info("Loading bases_maintenance_agencies.csv...")
        bases_df = pd.read_csv(DATA_DIR / "bases_maintenance_agencies.csv")
        for _, r in bases_df.iterrows():
            bid = r["base_id"]
            db.add(BaseAgency(
                base_id=bid,
                base_name=BASE_NAME_MAP.get(bid, f"Base {bid[-2:]}"),
                state=STATE_MAP.get(r["state"], r["state"]),
                daily_maintenance_slots=int(r["daily_maintenance_slots"]),
                hangar_bays=int(r["hangar_bays"]),
            ))
        db.commit()

        # 2. Aircraft
        logger.info("Loading fleet_aircraft.csv...")
        aircraft_df = pd.read_csv(DATA_DIR / "fleet_aircraft.csv")
        for _, r in aircraft_df.iterrows():
            orig_atype = r["aircraft_type"]
            db.add(Aircraft(
                aircraft_id=r["aircraft_id"],
                aircraft_type=AIRCRAFT_TYPE_MAP.get(orig_atype, orig_atype),
                engine_config=r["engine_config"],
                num_engines=int(r["num_engines"]),
                base_id=r["base_id"],
                commission_year=int(r["commission_year"]),
                total_flight_hours=int(r["total_flight_hours"]),
                mission_role=r["mission_role"],
                last_inspection_date=parse_date(r["last_inspection_date"]),
            ))
        db.commit()

        # 3. Engines
        logger.info("Loading engines.csv...")
        engines_df = pd.read_csv(DATA_DIR / "engines.csv")
        for _, r in engines_df.iterrows():
            orig_model = r["engine_model"]
            db.add(Engine(
                engine_id=r["engine_id"],
                aircraft_id=r["aircraft_id"],
                position=int(r["position"]),
                engine_model=ENGINE_MODEL_MAP.get(orig_model, orig_model),
                install_date=parse_date(r["install_date"]),
                cycles_since_new=int(r["cycles_since_new"]),
                hours_since_overhaul=int(r["hours_since_overhaul"]),
            ))
        db.commit()

        # 4. Engine Health Status & Invariants
        logger.info("Loading and reconciling engine_health_status.csv with demo_overrides.json...")
        health_df = pd.read_csv(DATA_DIR / "engine_health_status.csv")
        
        # Load overrides
        overrides_file = SEED_DIR / "demo_overrides.json"
        overrides_map = {}
        if overrides_file.exists():
            with open(overrides_file, "r") as f:
                data = json.load(f)
                for item in data.get("overrides", []):
                    overrides_map[item["engine_id"]] = item

        # Apply demo overrides to dataframe
        for idx, row in health_df.iterrows():
            eid = row["engine_id"]
            if eid in overrides_map:
                for k, v in overrides_map[eid].items():
                    health_df.at[idx, k] = v

        # Enforce exact 3 Critical engines: ENG-003, ENG-019, ENG-007
        target_criticals = {"ENG-003", "ENG-019", "ENG-007"}
        for idx, row in health_df.iterrows():
            eid = row["engine_id"]
            if eid not in target_criticals and row["status"] == "Critical":
                # Swap previously critical engines into Healthy
                health_df.at[idx, "health_score"] = 76.5
                health_df.at[idx, "status"] = "Healthy"
                health_df.at[idx, "predicted_rul_cycles"] = 148
                health_df.at[idx, "anomaly_score"] = 0.165
                health_df.at[idx, "failure_risk_7d"] = 0.075

        # Rebalance Watch count to exactly 12
        demo_watch = {"ENG-031", "ENG-014", "ENG-022", "ENG-038"}
        current_watch = health_df[health_df["status"] == "Watch"]
        excess_watch_count = len(current_watch) - 12
        if excess_watch_count > 0:
            candidates = [eid for eid in current_watch["engine_id"] if eid not in demo_watch]
            to_promote = candidates[:excess_watch_count]
            for eid in to_promote:
                idx = health_df[health_df["engine_id"] == eid].index[0]
                health_df.at[idx, "health_score"] = 79.2
                health_df.at[idx, "status"] = "Healthy"
                health_df.at[idx, "predicted_rul_cycles"] = 165
                health_df.at[idx, "anomaly_score"] = 0.145
                health_df.at[idx, "failure_risk_7d"] = 0.055

        # Validate invariants
        counts = health_df["status"].value_counts()
        healthy_count = counts.get("Healthy", 0)
        watch_count = counts.get("Watch", 0)
        critical_count = counts.get("Critical", 0)
        logger.info(f"Engine status invariant check: Healthy={healthy_count}, Watch={watch_count}, Critical={critical_count}, Total={len(health_df)}")
        assert len(health_df) == 42, f"Expected 42 engines, got {len(health_df)}"
        assert healthy_count == 27, f"Expected 27 Healthy engines, got {healthy_count}"
        assert watch_count == 12, f"Expected 12 Watch engines, got {watch_count}"
        assert critical_count == 3, f"Expected 3 Critical engines, got {critical_count}"

        final_engine_states = {}
        for _, r in health_df.iterrows():
            eid = r["engine_id"]
            final_engine_states[eid] = {
                "health_score": float(r["health_score"]),
                "status": str(r["status"]),
                "predicted_rul_cycles": int(r["predicted_rul_cycles"]),
                "anomaly_score": float(r["anomaly_score"]),
                "failure_risk_7d": float(r["failure_risk_7d"]),
            }
            db.add(EngineHealthStatus(
                engine_id=eid,
                aircraft_id=r["aircraft_id"],
                health_score=float(r["health_score"]),
                status=str(r["status"]),
                predicted_rul_cycles=int(r["predicted_rul_cycles"]),
                anomaly_score=float(r["anomaly_score"]),
                failure_risk_7d=float(r["failure_risk_7d"]),
                last_updated=str(r["last_updated"]),
            ))
        db.commit()

        # 5. Component Health (synchronized with final statuses)
        logger.info("Loading component_health.csv and synchronizing component scores...")
        comp_df = pd.read_csv(DATA_DIR / "component_health.csv")
        for _, r in comp_df.iterrows():
            eid = r["engine_id"]
            comp_name = r["component"]
            eng_state = final_engine_states.get(eid)
            
            orig_h = float(r["health_score"])
            orig_shap = float(r["shap_contribution"])
            
            if eng_state:
                eng_h = eng_state["health_score"]
                eng_status = eng_state["status"]
                
                if eng_status == "Critical":
                    # Featured critical engines component distribution
                    if comp_name in ("Turbine", "Combustion Chamber"):
                        comp_h = max(10.0, min(eng_h - 4.0, 35.0))
                        colour = "Red"
                        shap = round(orig_shap * 1.8 + 0.15, 3)
                    elif comp_name == "Compressor":
                        comp_h = max(20.0, min(eng_h + 8.0, 39.0))
                        colour = "Red"
                        shap = round(orig_shap * 1.4 + 0.08, 3)
                    else:
                        comp_h = max(38.0, min(eng_h + 18.0, 55.0))
                        colour = "Yellow" if comp_h < 70 else "Green"
                        shap = round(orig_shap * 0.7, 3)
                elif eng_status == "Healthy":
                    comp_h = max(72.0, min(99.0, eng_h + (orig_h - 75.0) * 0.4))
                    colour = "Green"
                    shap = round(min(0.20, orig_shap * 0.5), 3)
                else: # Watch
                    comp_h = max(42.0, min(68.0, eng_h + (orig_h - 55.0) * 0.3))
                    colour = "Yellow"
                    shap = round(orig_shap, 3)
            else:
                comp_h = orig_h
                colour = str(r["colour"])
                shap = orig_shap

            db.add(ComponentHealth(
                engine_id=eid,
                component=comp_name,
                health_score=round(comp_h, 1),
                colour=colour,
                shap_contribution=shap,
            ))
        db.commit()

        # 6. Alerts (aligned with final status)
        logger.info("Loading alerts.csv and aligning severity/status...")
        alerts_df = pd.read_csv(DATA_DIR / "alerts.csv")
        
        # Keep track of alert IDs to avoid duplicates
        existing_alert_ids = set()
        for _, r in alerts_df.iterrows():
            aid = str(r["alert_id"])
            existing_alert_ids.add(aid)
            eid = r["engine_id"]
            eng_state = final_engine_states.get(eid)
            status = str(r["status"])
            severity = str(r["severity"])

            if eng_state:
                if eng_state["status"] == "Healthy":
                    status = "Resolved"
                    severity = "Low"
                elif eng_state["status"] == "Critical":
                    severity = "High"
                    if status == "Resolved":
                        status = "In Progress"

            db.add(Alert(
                alert_id=aid,
                timestamp=str(r["timestamp"]),
                engine_id=eid,
                aircraft_id=r["aircraft_id"],
                severity=severity,
                trigger=str(r["trigger"]),
                anomaly_score=float(r["anomaly_score"]),
                rul_cycles=int(r["rul_cycles"]),
                status=status,
                source="ml",
            ))

        # Add explicit critical alerts for our 3 Critical demo engines if not already present
        now_str = datetime(2026, 10, 11, 8, 30).strftime("%Y-%m-%d %H:%M")
        crit_configs = [
            ("ENG-003", "VJ-102", "Turbine EGT margin critical & vibration exceedance", 0.885, 8, "Unacknowledged"),
            ("ENG-019", "VJ-111", "Severe vibration spike on high-pressure shaft", 0.812, 14, "In Progress"),
            ("ENG-007", "VJ-104", "Combustion chamber pressure instability", 0.760, 22, "Acknowledged"),
        ]
        for idx, (eid, aid_tail, trig, anom, rul, st) in enumerate(crit_configs, 1):
            crit_aid = f"ALT-CRIT-{idx:02d}"
            if crit_aid not in existing_alert_ids:
                db.add(Alert(
                    alert_id=crit_aid,
                    timestamp=now_str,
                    engine_id=eid,
                    aircraft_id=aid_tail,
                    severity="High",
                    trigger=trig,
                    anomaly_score=anom,
                    rul_cycles=rul,
                    status=st,
                    source="ml",
                ))
        db.commit()

        # 7. Rule Engine Thresholds
        logger.info("Loading rule_engine_thresholds.csv...")
        rules_df = pd.read_csv(DATA_DIR / "rule_engine_thresholds.csv")
        for _, r in rules_df.iterrows():
            db.add(RuleEngineThreshold(
                parameter=r["parameter"],
                operator=r["operator"],
                threshold=float(r["threshold"]),
                severity=r["severity"],
                recommended_action=r["recommended_action"],
            ))
        db.commit()

        # 8. Maintenance History
        logger.info("Loading maintenance_history.csv...")
        maint_df = pd.read_csv(DATA_DIR / "maintenance_history.csv")
        for _, r in maint_df.iterrows():
            db.add(MaintenanceHistory(
                record_id=r["record_id"],
                engine_id=r["engine_id"],
                aircraft_id=r["aircraft_id"],
                date=parse_date(r["date"]),
                maintenance_type=r["maintenance_type"],
                category=r["category"],
                downtime_hours=int(r["downtime_hours"]),
                technician_id=r["technician_id"],
                base_id=r["base_id"],
                fault_found=str(r["fault_found"]) if pd.notna(r["fault_found"]) else None,
                cost_inr_lakh=float(r["cost_inr_lakh"]),
            ))
        db.commit()

        # 9. Spares Inventory
        logger.info("Loading spares_inventory.csv...")
        spares_df = pd.read_csv(DATA_DIR / "spares_inventory.csv")
        for _, r in spares_df.iterrows():
            db.add(SparesInventory(
                part_id=r["part_id"],
                part_name=r["part_name"],
                component=r["component"],
                base_id=r["base_id"],
                qty_in_stock=int(r["qty_in_stock"]),
                reorder_level=int(r["reorder_level"]),
                lead_time_days=int(r["lead_time_days"]),
                unit_cost_inr_lakh=float(r["unit_cost_inr_lakh"]),
                supplier=SUPPLIER_MAP.get(r["supplier"], r["supplier"]),
            ))
        db.commit()

        # 10. Fleet Availability History
        logger.info("Loading fleet_availability_history.csv...")
        avail_df = pd.read_csv(DATA_DIR / "fleet_availability_history.csv")
        for _, r in avail_df.iterrows():
            db.add(FleetAvailabilityHistory(
                date=parse_date(r["date"]),
                base_id=r["base_id"],
                total_aircraft=int(r["total_aircraft"]),
                mission_ready=int(r["mission_ready"]),
                under_scheduled_maintenance=int(r["under_scheduled_maintenance"]),
                under_unscheduled_maintenance=int(r["under_unscheduled_maintenance"]),
                availability_pct=float(r["availability_pct"]),
            ))
        db.commit()

        # 11. Mission Demand
        logger.info("Loading mission_demand_next14d.csv...")
        demand_df = pd.read_csv(DATA_DIR / "mission_demand_next14d.csv")
        for _, r in demand_df.iterrows():
            db.add(MissionDemand(
                date=parse_date(r["date"]),
                base_id=r["base_id"],
                aircraft_required=int(r["aircraft_required"]),
            ))
        db.commit()

        # 12. Seed Users
        logger.info("Seeding authenticated users (Fleet Commander, Maintenance Officer, Analyst)...")
        users_seed = [
            ("IAF-001", "Fleet Commander", "Fleet Commander", "Commander@123", "BASE01"),
            ("IAF-002", "Maintenance Officer", "Maintenance Officer", "Officer@123", "BASE01"),
            ("IAF-003", "Analyst", "Analyst", "Analyst@123", "BASE05"),
        ]
        created_now = datetime(2026, 10, 11, 0, 0).strftime("%Y-%m-%d %H:%M:%S")
        for s_id, name, role, plain_pwd, b_id in users_seed:
            db.add(User(
                service_id=s_id,
                name=name,
                role=role,
                password_hash=get_password_hash(plain_pwd),
                base_id=b_id,
                created_at=created_now,
            ))
        db.commit()

        # 13. Seed Work Orders & Maintenance Tasks
        logger.info("Seeding maintenance tasks and work orders...")
        tasks_seed = [
            ("TSK-001", "ENG-003", "VJ-102", "BASE01", "Turbine", "PRT-004", "Turbine Blade Repair", "Immediate", "Scheduled", date(2026, 10, 12), 48),
            ("TSK-002", "ENG-019", "VJ-111", "BASE02", "Shaft", "PRT-005", "Bearing Replacement", "Immediate", "Scheduled", date(2026, 10, 13), 36),
            ("TSK-003", "ENG-007", "VJ-104", "BASE03", "Combustion Chamber", "PRT-003", "Combustor Liner Replacement", "Within 7 Days", "Suggested", date(2026, 10, 15), 24),
            ("TSK-004", "ENG-031", "VJ-118", "BASE04", "Compressor", "PRT-002", "Compressor Wash & Inspection", "Within 14 Days", "Suggested", date(2026, 10, 18), 12),
            ("TSK-005", "ENG-014", "VJ-108", "BASE05", "Fan", "PRT-001", "Fan Blade Inspection", "Within 14 Days", "Suggested", date(2026, 10, 20), 10),
        ]
        for t_id, eid, aid, bid, comp, part, m_type, urg, st, s_date, dt in tasks_seed:
            db.add(MaintenanceTask(
                task_id=t_id,
                engine_id=eid,
                aircraft_id=aid,
                base_id=bid,
                component=comp,
                required_part_id=part,
                maintenance_type=m_type,
                urgency=urg,
                status=st,
                scheduled_date=s_date,
                estimated_downtime_hours=dt,
                created_at=created_now,
            ))

        db.add(WorkOrder(
            work_order_id="WO-2026-001",
            alert_id="ALT-CRIT-01",
            engine_id="ENG-003",
            aircraft_id="VJ-102",
            base_id="BASE01",
            status="In Progress",
            priority="Critical",
            task_description="Immediate teardown inspection of turbine stage 1 blades; replacement kit PRT-004 allocated.",
            assigned_technician="TECH-002",
            estimated_downtime_hours=48,
            created_at=created_now,
            approved_at=created_now,
            approved_by="IAF-001",
        ))

        # 14. Seed Spare Orders
        db.add(SpareOrder(
            order_id="ORD-2026-001",
            part_id="PRT-004",
            base_id="BASE01",
            quantity=3,
            status="In Transit",
            order_date=created_now,
            expected_delivery=(datetime(2026, 10, 11) + timedelta(days=14)).strftime("%Y-%m-%d"),
            supplier="Depot-Alpha",
            total_cost_inr_lakh=42.0,
        ))

        # 15. Seed Settings
        default_settings = [
            ("health_bands", json.dumps({"Healthy": [70, 100], "Watch": [40, 69], "Critical": [0, 39]}), "Fleet Health Categorisation Thresholds"),
            ("offline_mode", "true", "Air-gapped offline operations mode"),
            ("data_retention_days", "365", "Sensor telemetry and audit retention days"),
            ("auto_work_order_threshold", "30", "Health score threshold for automatic work order suggestion"),
            ("notification_dispatch", json.dumps({"sms": False, "email": False, "console_banner": True}), "Notification channels"),
        ]
        for k, v, desc in default_settings:
            db.add(Setting(key=k, value=v, description=desc, updated_at=created_now))

        # 16. Seed Simulator State
        db.add(SimulatorState(
            id=1,
            is_running=False,
            speed=1.0,
            current_step=0,
            total_steps=720,
            active_faults=json.dumps({}),
            updated_at=created_now,
        ))

        # 17. Audit Log
        db.commit()
        log_audit(
            db=db,
            user_id="SYSTEM",
            user_role="System Administrator",
            action="INITIAL_DATA_LOAD",
            entity_type="DATABASE",
            entity_id="vajra.db",
            details="Loaded 24 aircraft, 42 engines (27 Healthy, 12 Watch, 3 Critical), 5 bases, and initialized system state."
        )
        logger.info("Successfully built vajra.db with all models, constraints, and invariants!")

    except Exception as e:
        db.rollback()
        logger.error(f"Error loading data: {e}", exc_info=True)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    load_all_data()
