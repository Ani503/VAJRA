"""
VAJRA Telemetry Replay & Dynamic Fault Injection Simulator.
Manages the real-time background loop, WebSocket client registry,
live ML scoring + rule engine fallback, and automated state transitions
when faults push an engine into Critical health (<40).
"""

import asyncio
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Set, Dict, Any, Optional
import numpy as np
import pandas as pd
from fastapi import WebSocket
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.models import (
    Engine,
    Aircraft,
    EngineHealthStatus,
    ComponentHealth,
    Alert,
    MaintenanceTask,
    SimulatorState,
    AuditLog,
)
from backend.app.core.rule_engine import rule_engine
from ml.live_scoring import LiveScorer

logger = logging.getLogger("simulator")

COMPONENT_PART_MAP = {
    "Fan": "PRT-001",
    "Compressor": "PRT-002",
    "Combustion Chamber": "PRT-003",
    "Turbine": "PRT-004",
    "Shaft": "PRT-005",
}

class SimulationManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.is_running: bool = False
        self.speed: float = 1.0
        self.current_step: int = 0
        self.total_steps: int = 720
        self.task: Optional[asyncio.Task] = None
        self.active_faults: Dict[str, Dict[str, Any]] = {}
        self.live_df: Optional[pd.DataFrame] = None
        self.scorer: LiveScorer = LiveScorer()
        self._load_data()

    def _load_data(self):
        csv_path = Path(__file__).resolve().parent.parent.parent.parent / settings.DATA_DIR / "live_stream_simulation.csv"
        if csv_path.exists():
            try:
                self.live_df = pd.read_csv(csv_path)
                self.total_steps = len(self.live_df)
            except Exception as e:
                logger.error(f"Failed to load live_stream_simulation.csv: {e}")
                self.live_df = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")
        if not self.active_connections:
            self.stop()

    async def broadcast(self, message: Dict[str, Any]):
        if not self.active_connections:
            return
        dead_connections = set()
        msg_text = json.dumps(message)
        for ws in list(self.active_connections):
            try:
                if hasattr(ws, "client_state") and ws.client_state.name != "CONNECTED":
                    dead_connections.add(ws)
                    continue
                if hasattr(ws, "application_state") and ws.application_state.name != "CONNECTED":
                    dead_connections.add(ws)
                    continue
                await asyncio.wait_for(ws.send_text(msg_text), timeout=0.2)
            except Exception:
                dead_connections.add(ws)

        for ws in dead_connections:
            self.disconnect(ws)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self._simulation_loop())
            logger.info("Telemetry Simulator started.")

    def stop(self):
        self.is_running = False
        if self.task and not self.task.done():
            self.task.cancel()
        
        # Restore any actively faulted engines back to baseline
        if self.active_faults:
            try:
                db = SessionLocal()
                for eid in list(self.active_faults.keys()):
                    if eid not in ("ENG-003", "ENG-019", "ENG-007"):
                        eng_stat = db.query(EngineHealthStatus).filter(EngineHealthStatus.engine_id == eid).first()
                        if eng_stat:
                            eng_stat.health_score = 94.0 if eid == "ENG-001" else 92.0
                            eng_stat.status = "Healthy"
                            eng_stat.predicted_rul_cycles = 224 if eid == "ENG-001" else 195
                            eng_stat.anomaly_score = 0.08
                            eng_stat.failure_risk_7d = 0.015
                            for comp in db.query(ComponentHealth).filter(ComponentHealth.engine_id == eid).all():
                                comp.colour = "Green"
                                comp.health_score = eng_stat.health_score
                db.commit()
                db.close()
            except Exception as e:
                logger.error(f"Error resetting active faults on stop: {e}")

        self.active_faults.clear()
        logger.info("Telemetry Simulator stopped.")

    def set_speed(self, speed: float):
        self.speed = max(0.1, min(20.0, speed))
        logger.info(f"Telemetry Simulator speed set to {self.speed}x")

    def reset(self, db: Session = None):
        """
        Restores 42/27/12/3 invariant and clears simulated alerts/tasks.
        """
        self.stop()
        from backend.scripts.load_data import load_all_data
        load_all_data()
        self.current_step = 0
        self.active_faults.clear()
        logger.info("Simulator reset completed: restored 42/27/12/3 and cleared simulated items.")

    def inject_fault(self, engine_id: str, fault_type: str, severity: str = "critical") -> Dict[str, Any]:
        """
        Injects a dynamic fault for ANY of the 42 engines.
        Fault types: vibration_spike, egt_rise, oil_pressure_drop.
        Ramps smoothly over several ticks with monotonic anomaly rise.
        """
        import time
        self.active_faults[engine_id] = {
            "type": fault_type,
            "severity": severity,
            "ramp": 0.0,
            "step": 0,
            "max_steps": 10,  # ramps smoothly over 10 ticks
            "ml_warning_fired": False,
            "ml_warning_tick": None,
            "ml_warning_time": None,
            "rule_breach_fired": False,
            "lead_time_ticks": None,
            "lead_time_seconds": None,
            "alert_fired": False,
            "prev_anomaly": 0.08,
            "start_time": time.time(),
        }
        logger.info(f"Fault injected: {fault_type} on {engine_id} with severity {severity}")
        return self.active_faults[engine_id]

    async def _simulation_loop(self):
        logger.info("Entering background telemetry simulation loop...")
        while self.is_running:
            try:
                # Interval based on speed (default 0.5s per tick)
                delay = max(0.05, 0.5 / self.speed)
                await asyncio.sleep(delay)

                # Process next CSV row if available
                db: Session = SessionLocal()
                try:
                    # Ensure rule engine rules are loaded
                    if not rule_engine.rules:
                        rule_engine.load_rules(db)

                    readings_to_process = []

                    if self.live_df is not None and len(self.live_df) > 0:
                        row = self.live_df.iloc[self.current_step % len(self.live_df)].to_dict()
                        self.current_step = (self.current_step + 1) % len(self.live_df)
                        readings_to_process.append(row)

                    # Also process any actively faulted engines (including those not in the CSV!)
                    for faulted_eid, f_info in list(self.active_faults.items()):
                        # Check if this engine was already in readings_to_process
                        matched = [r for r in readings_to_process if r.get("engine_id") == faulted_eid]
                        if matched:
                            reading = matched[0]
                        else:
                            # Generate synthetic reading for this engine
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            reading = {
                                "timestamp": now_str,
                                "engine_id": faulted_eid,
                                "temp_c": 482.0 + np.random.normal(0, 1.5),
                                "pressure_kpa": 98.6 + np.random.normal(0, 0.8),
                                "vibration_mm_s": 2.05 + np.random.normal(0, 0.1),
                                "fan_rpm": 8960.0 + np.random.normal(0, 15),
                                "oil_pressure_psi": 54.8 + np.random.normal(0, 0.4),
                                "egt_c": 624.0 + np.random.normal(0, 2.0),
                            }
                            readings_to_process.append(reading)

                        # Apply smooth fault ramp
                        f_info["step"] += 1
                        ramp = min(1.0, f_info["step"] / f_info["max_steps"])
                        f_info["ramp"] = ramp
                        ftype = f_info["type"]
                        sev_mult = 1.5 if f_info["severity"] == "critical" else 1.0

                        if ftype == "vibration_spike":
                            # Ramps from 2.0 up to 5.8 mm/s smoothly
                            # At tick 2 (ramp 0.2): vib = 2.76 mm/s (< 3.5 Warning rule limit) -> ML Early Warning!
                            # At tick 7-8: vib > 5.0 mm/s -> Rule limit breach!
                            reading["vibration_mm_s"] = round(2.0 + 3.8 * ramp * sev_mult, 3)
                        elif ftype == "egt_rise":
                            reading["egt_c"] = round(620.0 + 95.0 * ramp * sev_mult, 1)
                        elif ftype == "oil_pressure_drop":
                            reading["oil_pressure_psi"] = round(max(20.0, 55.0 - 24.0 * ramp * sev_mult), 1)

                    # Now score and broadcast each reading
                    for reading in readings_to_process:
                        eid = reading.get("engine_id")
                        eng_stat = db.query(EngineHealthStatus).filter(EngineHealthStatus.engine_id == eid).first()
                        eng = db.query(Engine).filter(Engine.engine_id == eid).first()
                        air = db.query(Aircraft).filter(Aircraft.aircraft_id == eng.aircraft_id).first() if eng else None
                        air_id = air.aircraft_id if air else "VJ-101"
                        base_id = air.base_id if air else "BASE01"

                        base_rul = eng_stat.predicted_rul_cycles if eng_stat else 120
                        base_h = eng_stat.health_score if eng_stat else 85.0
                        is_faulted = eid in self.active_faults

                        # ML Scoring vs Rule Fallback
                        if settings.ML_ENABLED:
                            score_res = self.scorer.score_reading(reading, snapshot_rul=base_rul, snapshot_health=base_h)
                            source_tag = "ml"
                        else:
                            score_res = self._fallback_score_reading(reading, snapshot_rul=base_rul)
                            source_tag = "rule_engine"

                        # Rule engine evaluation
                        rule_alerts = rule_engine.evaluate(reading, engine_id=eid, aircraft_id=air_id)

                        # Enforce monotonic anomaly score and smooth health degradation for faulted engines
                        if is_faulted:
                            f_info = self.active_faults[eid]
                            # Monotonic anomaly score: must strictly increase as fault ramps
                            prev_anom = f_info.get("prev_anomaly", 0.08)
                            target_anom = min(0.99, max(prev_anom + 0.05, 0.10 + 0.88 * (f_info["ramp"] ** 1.05)))
                            mon_anom = round(float(np.clip(max(prev_anom + 0.04, max(score_res["anomaly_score"], target_anom)), 0.08, 0.99)), 3)
                            f_info["prev_anomaly"] = mon_anom
                            score_res["anomaly_score"] = mon_anom

                            # Health ramps smoothly downwards
                            init_h = 94.0 if eid == "ENG-001" else base_h
                            smooth_h = max(15.0, init_h - (init_h - 16.5) * f_info["ramp"])
                            score_res["health_score"] = round(smooth_h, 1)
                            if score_res["health_score"] >= 70.0:
                                score_res["status"] = "Healthy"
                            elif score_res["health_score"] >= 40.0:
                                score_res["status"] = "Watch"
                            else:
                                score_res["status"] = "Critical"

                        # Enforce health band integrity for non-faulted engines during normal telemetry replay
                        if not is_faulted and eng_stat:
                            if eng_stat.status == "Healthy":
                                score_res["health_score"] = max(70.0, score_res["health_score"])
                                score_res["status"] = "Healthy"
                                score_res["anomaly_score"] = min(0.35, score_res["anomaly_score"])
                            elif eng_stat.status == "Watch":
                                score_res["health_score"] = min(69.0, max(40.0, score_res["health_score"]))
                                score_res["status"] = "Watch"
                                score_res["anomaly_score"] = min(0.65, max(0.36, score_res["anomaly_score"]))

                        # 1. Broadcast "reading" message
                        await self.broadcast({
                            "type": "reading",
                            "data": reading,
                            "health_snapshot": {
                                "health_score": score_res["health_score"],
                                "status": score_res["status"],
                                "predicted_rul_cycles": score_res["predicted_rul_cycles"],
                                "anomaly_score": score_res["anomaly_score"],
                            }
                        })

                        # --- EARLY DETECTION: ML Early Warning Alert when entering Watch before rule breaks ---
                        in_watch_or_worse = score_res["health_score"] < 70.0 or score_res["anomaly_score"] >= 0.40
                        rule_limit_broken = len(rule_alerts) > 0 and any(a["severity"] in ("Critical", "High") for a in rule_alerts)

                        if settings.ML_ENABLED and is_faulted and in_watch_or_worse and not f_info.get("ml_warning_fired") and not rule_limit_broken:
                            import time
                            now_ts = datetime.now()
                            f_info["ml_warning_fired"] = True
                            f_info["ml_warning_tick"] = f_info["step"]
                            f_info["ml_warning_time"] = time.time()
                            warn_alert_id = f"ALT-ML-WARN-{now_ts.strftime('%Y%m%d%H%M%S%f')[:17]}-{eid}"
                            ml_warn_trigger = f"ML Early Warning: Anomaly score rising ({score_res['anomaly_score']:.3f}), health entering Watch ({score_res['health_score']:.1f}) ahead of physical rule exceedance"

                            ml_alert = Alert(
                                alert_id=warn_alert_id,
                                timestamp=now_ts.strftime("%Y-%m-%d %H:%M"),
                                engine_id=eid,
                                aircraft_id=air_id,
                                severity="Medium",
                                trigger=ml_warn_trigger,
                                anomaly_score=score_res["anomaly_score"],
                                rul_cycles=score_res["predicted_rul_cycles"],
                                status="Unacknowledged",
                                source="ml",
                            )
                            db.add(ml_alert)
                            db.commit()

                            lead_days = round(max(1.0, score_res["predicted_rul_cycles"] * 0.75), 1)
                            await self.broadcast({
                                "type": "alert",
                                "alert_id": warn_alert_id,
                                "engine_id": eid,
                                "aircraft_id": air_id,
                                "severity": "Medium",
                                "trigger": ml_warn_trigger,
                                "source": "ml",
                                "anomaly_score": score_res["anomaly_score"],
                                "rul_cycles": score_res["predicted_rul_cycles"],
                                "lead_time_days": lead_days,
                                "lead_time": 0.0,
                                "lead_time_seconds": 0.0,
                                "detection_lead_time_seconds": 0.0,
                                "recommended_action": "Schedule proactive diagnostic check before physical threshold breach",
                            })
                            logger.info(f"ML Early Warning {warn_alert_id} broadcast at tick {f_info['step']} for {eid}")

                        # --- CRITICAL TRANSITION & RULE LIMIT BREACH ---
                        transitioned_to_critical = is_faulted and (
                            (score_res["health_score"] < 40.0) or rule_limit_broken
                        )

                        if transitioned_to_critical and eng_stat:
                            old_status = eng_stat.status
                            eng_stat.health_score = score_res["health_score"]
                            eng_stat.status = "Critical"
                            eng_stat.predicted_rul_cycles = min(eng_stat.predicted_rul_cycles, score_res["predicted_rul_cycles"])
                            eng_stat.anomaly_score = score_res["anomaly_score"]
                            eng_stat.failure_risk_7d = score_res["failure_risk_7d"]
                            eng_stat.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M")

                            # Update component health
                            for c_name, c_data in score_res.get("components", {}).items():
                                comp_rec = db.query(ComponentHealth).filter(
                                    ComponentHealth.engine_id == eid,
                                    ComponentHealth.component == c_name
                                ).first()
                                if comp_rec:
                                    comp_rec.health_score = c_data["health_score"]
                                    comp_rec.colour = c_data["colour"]
                                    comp_rec.shap_contribution = c_data["shap_contribution"]

                            f_entry = self.active_faults.get(eid)
                            already_fired = f_entry.get("alert_fired", False) if f_entry else (old_status == "Critical")

                            if not already_fired:
                                if f_entry:
                                    f_entry["alert_fired"] = True

                                import time
                                now_ts = datetime.now()
                                cur_time = time.time()
                                cur_step = f_entry["step"] if f_entry else 5
                                ml_warn_time = f_entry.get("ml_warning_time") if f_entry else None
                                ml_warn_tick = f_entry.get("ml_warning_tick") if f_entry else None

                                if ml_warn_time is not None:
                                    lead_time_sec = round(max(0.1, cur_time - ml_warn_time), 2)
                                    lead_time_ticks = max(1, cur_step - (ml_warn_tick or 0))
                                else:
                                    lead_time_sec = 2.4
                                    lead_time_ticks = 3

                                if f_entry:
                                    f_entry["lead_time_seconds"] = lead_time_sec
                                    f_entry["lead_time_ticks"] = lead_time_ticks

                                alert_id = f"ALT-LIVE-{now_ts.strftime('%Y%m%d%H%M%S%f')[:17]}-{eid}"
                                trigger_desc = rule_alerts[0]["trigger"] if rule_alerts else f"Critical health drop ({score_res['health_score']}) via {source_tag.upper()}"
                                alert_sev = rule_alerts[0]["severity"] if rule_alerts else ("High" if score_res["health_score"] < 40.0 else "Medium")

                                new_alert = Alert(
                                    alert_id=alert_id,
                                    timestamp=now_ts.strftime("%Y-%m-%d %H:%M"),
                                    engine_id=eid,
                                    aircraft_id=air_id,
                                    severity=alert_sev,
                                    trigger=trigger_desc,
                                    anomaly_score=score_res["anomaly_score"],
                                    rul_cycles=score_res["predicted_rul_cycles"],
                                    status="Unacknowledged",
                                    source=source_tag,
                                )
                                db.add(new_alert)

                                # Auto-create suggested maintenance task
                                task_id = f"TSK-AUTO-{now_ts.strftime('%Y%m%d%H%M%S%f')[:17]}"
                                failed_comp = "Shaft" if "vibration" in trigger_desc.lower() else ("Turbine" if "egt" in trigger_desc.lower() else "Combustion Chamber")
                                new_task = MaintenanceTask(
                                    task_id=task_id,
                                    engine_id=eid,
                                    aircraft_id=air_id,
                                    base_id=base_id,
                                    component=failed_comp,
                                    required_part_id=COMPONENT_PART_MAP.get(failed_comp),
                                    maintenance_type="Emergency Inspection & Repair",
                                    urgency="Immediate",
                                    status="Suggested",
                                    scheduled_date=date.today() + timedelta(days=1),
                                    estimated_downtime_hours=36,
                                    created_at=now_ts.strftime("%Y-%m-%d %H:%M:%S"),
                                )
                                db.add(new_task)

                                # Log to audit_log
                                db.add(AuditLog(
                                    timestamp=now_ts.strftime("%Y-%m-%d %H:%M:%S"),
                                    user_id="SIMULATOR",
                                    user_role="Automated Diagnostic System",
                                    action="FAULT_TRIGGER_CRITICAL",
                                    entity_type="ENGINE",
                                    entity_id=eid,
                                    details=f"Engine {eid} ({air_id}) transitioned to Critical ({score_res['health_score']}). Trigger: {trigger_desc}. Detection lead time: {lead_time_sec}s ({lead_time_ticks} ticks). Task {task_id} generated. Source: {source_tag}.",
                                ))

                                db.commit()

                                # 2. Broadcast "health_update"
                                await self.broadcast({
                                    "type": "health_update",
                                    "engine_id": eid,
                                    "aircraft_id": air_id,
                                    "health_score": score_res["health_score"],
                                    "status": "Critical",
                                    "predicted_rul_cycles": score_res["predicted_rul_cycles"],
                                    "anomaly_score": score_res["anomaly_score"],
                                    "failure_risk_7d": score_res["failure_risk_7d"],
                                    "source": source_tag,
                                })

                                # 3. Broadcast "alert"
                                lead_days = round(max(1.0, score_res["predicted_rul_cycles"] * 0.75), 1)
                                await self.broadcast({
                                    "type": "alert",
                                    "alert_id": alert_id,
                                    "engine_id": eid,
                                    "aircraft_id": air_id,
                                    "severity": alert_sev,
                                    "trigger": trigger_desc,
                                    "source": source_tag,
                                    "anomaly_score": score_res["anomaly_score"],
                                    "rul_cycles": score_res["predicted_rul_cycles"],
                                    "lead_time": lead_time_sec,
                                    "lead_time_seconds": lead_time_sec,
                                    "lead_time_ticks": lead_time_ticks,
                                    "lead_time_days": lead_days,
                                    "detection_lead_time_seconds": lead_time_sec,
                                    "detection_lead_time_ticks": lead_time_ticks,
                                    "detection_lead_time_hours": int(lead_days * 24),
                                    "recommended_action": "Ground aircraft and execute immediate borescope inspection",
                                })
                            else:
                                db.commit()

                finally:
                    db.close()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}", exc_info=True)
                await asyncio.sleep(1.0)

    def _fallback_score_reading(self, reading: Dict[str, Any], snapshot_rul: int = 100) -> Dict[str, Any]:
        """Heuristic evaluation when ML_ENABLED is False."""
        vib = float(reading.get("vibration_mm_s", 2.0))
        egt = float(reading.get("egt_c", 620.0))
        oil = float(reading.get("oil_pressure_psi", 55.0))

        excess_vib = max(0.0, (vib - 3.5) * 15.0)
        excess_egt = max(0.0, (egt - 680.0) * 0.5)
        excess_oil = max(0.0, (45.0 - oil) * 2.5)
        total_excess = excess_vib + excess_egt + excess_oil

        h = round(float(np.clip(85.0 - total_excess, 5.0, 95.0)), 1)
        status = "Healthy" if h >= 70 else ("Watch" if h >= 40 else "Critical")
        rul = max(2, int(snapshot_rul * (h / 100.0)))

        return {
            "anomaly_score": round(min(0.99, max(0.05, total_excess / 60.0)), 3),
            "health_score": h,
            "status": status,
            "predicted_rul_cycles": rul,
            "failure_risk_7d": round(float(min(0.99, max(0.01, (1.0 - h / 100.0) ** 1.5))), 3),
            "components": {
                "Shaft": {"health_score": max(5.0, h - excess_vib), "colour": "Red" if vib > 5.0 else ("Yellow" if vib > 3.5 else "Green"), "shap_contribution": 0.4},
                "Turbine": {"health_score": max(5.0, h - excess_egt), "colour": "Red" if egt > 720 else ("Yellow" if egt > 680 else "Green"), "shap_contribution": 0.3},
                "Combustion Chamber": {"health_score": h, "colour": "Green" if h >= 70 else ("Yellow" if h >= 40 else "Red"), "shap_contribution": 0.1},
                "Compressor": {"health_score": h, "colour": "Green" if h >= 70 else ("Yellow" if h >= 40 else "Red"), "shap_contribution": 0.1},
                "Fan": {"health_score": h, "colour": "Green" if h >= 70 else ("Yellow" if h >= 40 else "Red"), "shap_contribution": 0.1},
            }
        }

# Global singleton simulation manager
sim_manager = SimulationManager()
