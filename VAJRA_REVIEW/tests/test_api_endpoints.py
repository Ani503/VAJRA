import pytest

def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "offline_mode" in data

def test_api_auth_login_and_me(client):
    # Valid login
    res = client.post("/api/auth/login", json={"service_id": "IAF-001", "password": "Commander@123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "Fleet Commander"

    token = data["access_token"]
    # Check /me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["service_id"] == "IAF-001"

    # Invalid login
    bad_res = client.post("/api/auth/login", json={"service_id": "IAF-001", "password": "WrongPassword"})
    assert bad_res.status_code == 401

def test_rbac_permissions(client, analyst_headers, commander_headers):
    # Analyst cannot modify settings or users (403 Forbidden)
    res = client.get("/api/settings/users", headers=analyst_headers)
    assert res.status_code == 403

    # Fleet Commander can view and manage users
    res_cmd = client.get("/api/settings/users", headers=commander_headers)
    assert res_cmd.status_code == 200
    assert len(res_cmd.json()) >= 3

def test_dashboard_summary_invariants(client, commander_headers):
    from backend.scripts.load_data import load_all_data
    load_all_data()
    res = client.get("/api/dashboard/summary", headers=commander_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_engines"] == 42
    assert data["healthy_engines"] == 27
    assert data["watch_engines"] == 12
    assert data["critical_engines"] == 3
    assert data["total_aircraft"] == 24
    assert data["total_bases"] == 5

    assert len(data["top_5_engines_at_risk"]) == 5
    assert "digital_twin_preview" in data
    assert "Turbine" in data["digital_twin_preview"]["components"]

def test_engines_list_and_details(client, commander_headers):
    # List engines with filtering
    res = client.get("/api/engines?status=Critical", headers=commander_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    for it in data["items"]:
        assert it["status"] == "Critical"

    # Engine Detail for ENG-003
    res_eng = client.get("/api/engines/ENG-003", headers=commander_headers)
    assert res_eng.status_code == 200
    eng_data = res_eng.json()
    assert eng_data["engine_id"] == "ENG-003"
    assert eng_data["status"] == "Critical"
    assert eng_data["health_score"] == 18.0
    assert eng_data["predicted_rul_cycles"] == 8
    assert len(eng_data["components"]) == 5
    assert len(eng_data["shap_top_features"]) == 5

    # Components endpoint
    res_comp = client.get("/api/engines/ENG-003/components", headers=commander_headers)
    assert res_comp.status_code == 200
    assert len(res_comp.json()) == 5

def test_alerts_lifecycle_and_work_order(client, maintenance_headers):
    res = client.get("/api/alerts?severity=High", headers=maintenance_headers)
    assert res.status_code == 200
    alerts = res.json()["alerts"]
    assert len(alerts) > 0

    target_alert = alerts[0]
    aid = target_alert["alert_id"]

    # Patch acknowledge
    res_patch = client.patch(f"/api/alerts/{aid}", json={"status": "Acknowledged", "assigned_to": "TECH-001"}, headers=maintenance_headers)
    assert res_patch.status_code == 200
    assert res_patch.json()["status"] == "Acknowledged"

    # Create work order from alert
    res_wo = client.post(f"/api/alerts/{aid}/work-order", json={"task_description": "Urgent stage 1 overhaul", "estimated_downtime_hours": 36}, headers=maintenance_headers)
    assert res_wo.status_code == 200
    assert "work_order_id" in res_wo.json()

def test_maintenance_tasks_and_optimisation(client, maintenance_headers):
    # List tasks
    res = client.get("/api/maintenance/tasks", headers=maintenance_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # Schedule view
    res_sched = client.get("/api/maintenance/schedule", headers=maintenance_headers)
    assert res_sched.status_code == 200
    assert len(res_sched.json()["bases"]) == 5

    # AI Optimizer
    res_opt = client.post("/api/maintenance/optimise", headers=maintenance_headers)
    assert res_opt.status_code == 200
    data = res_opt.json()
    assert "assignments" in data
    assert "conflicts" in data
    assert "capacity_utilization_pct" in data

    # Approve tasks
    if data["assignments"]:
        t_id = data["assignments"][0]["task_id"]
        res_app = client.post("/api/maintenance/approve", json={"task_ids": [t_id], "notes": "Approved by testing"}, headers=maintenance_headers)
        assert res_app.status_code == 200
        assert res_app.json()["approved_count"] == 1

def test_spares_inventory_transfer_and_forecast(client, maintenance_headers):
    # Overview
    res = client.get("/api/spares", headers=maintenance_headers)
    assert res.status_code == 200
    matrix = res.json()["matrix"]
    assert "PRT-001" in matrix

    # Reorder spares
    res_order = client.post("/api/spares/reorder", json={"part_id": "PRT-001", "base_id": "BASE01", "quantity": 2}, headers=maintenance_headers)
    assert res_order.status_code == 200
    assert "order_id" in res_order.json()

    # Valid Transfer
    res_tr = client.post("/api/spares/transfer", json={"part_id": "PRT-001", "source_base_id": "BASE01", "destination_base_id": "BASE02", "quantity": 1}, headers=maintenance_headers)
    assert res_tr.status_code == 200
    assert res_tr.json()["status"] == "success"

    # Invalid Transfer (excessive quantity triggers 400 Bad Request)
    res_bad = client.post("/api/spares/transfer", json={"part_id": "PRT-001", "source_base_id": "BASE01", "destination_base_id": "BASE02", "quantity": 9999}, headers=maintenance_headers)
    assert res_bad.status_code == 400
    assert "Insufficient inventory" in res_bad.json()["detail"]

    # 30-Day Demand forecast
    res_fc = client.get("/api/spares/demand-forecast?horizon_days=30", headers=maintenance_headers)
    assert res_fc.status_code == 200
    assert "forecast" in res_fc.json()

def test_fleet_availability_scenarios(client, commander_headers):
    for scen in ("predictive", "baseline", "reactive"):
        res = client.get(f"/api/fleet/availability?scenario={scen}&horizon=14", headers=commander_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["scenario"] == scen
        assert len(data["bases"]) == 5
        assert len(data["daily_timeline"]) == 14
        assert len(data["scenario_explanation"]) > 20

    # Verify that scenarios differ in readiness levels
    res_pred = client.get("/api/fleet/availability?scenario=predictive", headers=commander_headers).json()
    res_react = client.get("/api/fleet/availability?scenario=reactive", headers=commander_headers).json()
    assert res_pred["daily_timeline"][10]["mission_ready"] > res_react["daily_timeline"][10]["mission_ready"]

def test_reports_generation_and_download(client, commander_headers):
    # PDF report
    res_pdf = client.post("/api/reports", json={"report_type": "daily_fleet_health", "format": "pdf"}, headers=commander_headers)
    assert res_pdf.status_code == 200
    pdf_info = res_pdf.json()
    assert pdf_info["format"] == "pdf"
    assert pdf_info["report_id"].startswith("RPT-")

    # Download PDF
    res_dl = client.get(f"/api/reports/{pdf_info['report_id']}/download", headers=commander_headers)
    assert res_dl.status_code == 200
    assert res_dl.headers["content-type"] == "application/pdf"
    assert len(res_dl.content) > 1000  # valid pdf bytes

    # CSV report
    res_csv = client.post("/api/reports", json={"report_type": "alert_log", "format": "csv"}, headers=commander_headers)
    assert res_csv.status_code == 200
    csv_info = res_csv.json()
    assert csv_info["format"] == "csv"

def test_simulator_controls_and_fault_injection(client, maintenance_headers):
    # Speed
    res_spd = client.post("/api/simulator/speed", json={"speed": 2.5}, headers=maintenance_headers)
    assert res_spd.status_code == 200
    assert res_spd.json()["speed"] == 2.5

    # Inject fault on ENG-001
    res_inj = client.post("/api/simulator/inject-fault", json={"type": "vibration_spike", "engine_id": "ENG-001", "severity": "critical"}, headers=maintenance_headers)
    assert res_inj.status_code == 200
    assert res_inj.json()["engine_id"] == "ENG-001"

    # State
    res_st = client.get("/api/simulator/state", headers=maintenance_headers)
    assert res_st.status_code == 200
    assert "active_faults" in res_st.json()

    # Reset invariants after fault injection test
    from backend.app.services.simulator import sim_manager
    sim_manager.stop()
    from backend.scripts.load_data import load_all_data
    load_all_data()

def test_system_status_and_audit_log(client, commander_headers):
    # System status
    res_sys = client.get("/api/system/status", headers=commander_headers)
    assert res_sys.status_code == 200
    sys_data = res_sys.json()
    assert sys_data["database_connected"] is True
    assert sys_data["total_engines"] == 42
    assert sys_data["total_aircraft"] == 24

    # Audit log JSON
    res_aud = client.get("/api/audit-log", headers=commander_headers)
    assert res_aud.status_code == 200
    assert res_aud.json()["total"] > 0

    # Audit log CSV export
    res_csv = client.get("/api/audit-log?export=csv", headers=commander_headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "Timestamp,User ID" in res_csv.text

def test_3d_model_assets_and_digital_twin_view(client):
    """Verify that 3D glTF/GLB models and digital twin UI are served with correct MIME types and data."""
    # Aircraft GLB (original baseline)
    res_air = client.get("/assets/Models/vajra_aircraft.glb")
    assert res_air.status_code == 200
    assert "model/gltf-binary" in res_air.headers["content-type"]
    assert len(res_air.content) > 50000
    assert res_air.content[:4] == b"glTF"

    # High-Definition Su-30MKI Aircraft GLB (improved model)
    res_hd = client.get("/assets/Models/vajra_aircraft_hd.glb")
    assert res_hd.status_code == 200
    assert "model/gltf-binary" in res_hd.headers["content-type"]
    assert len(res_hd.content) > 150000
    assert res_hd.content[:4] == b"glTF"

    # Engine GLB
    res_eng = client.get("/assets/Models/vajra_engine.glb")
    assert res_eng.status_code == 200
    assert "model/gltf-binary" in res_eng.headers["content-type"]
    assert len(res_eng.content) > 400000
    assert res_eng.content[:4] == b"glTF"

    # Full Airframe Engineering Digital Twin GLB (29 structured assemblies with wing spars & ribs)
    res_twin = client.get("/assets/Models/vajra_aircraft_twin.glb")
    assert res_twin.status_code == 200
    assert "model/gltf-binary" in res_twin.headers["content-type"]
    assert len(res_twin.content) > 300000
    assert res_twin.content[:4] == b"glTF"

    # High-Detail Turbofan Assembly GLB (casing, fan, 3-stage booster, 9-stage HPC, combustor, turbines, TVC)
    res_eng_det = client.get("/assets/Models/vajra_engine_detailed.glb")
    assert res_eng_det.status_code == 200
    assert "model/gltf-binary" in res_eng_det.headers["content-type"]
    assert len(res_eng_det.content) > 400000
    assert res_eng_det.content[:4] == b"glTF"

    # Capitalized /Assets route
    assert client.get("/Assets/Models/vajra_aircraft.glb").status_code == 200
    assert client.get("/Assets/Models/vajra_aircraft_hd.glb").status_code == 200
    assert client.get("/Assets/Models/vajra_aircraft_twin.glb").status_code == 200
    assert client.get("/Assets/Models/vajra_engine.glb").status_code == 200
    assert client.get("/Assets/Models/vajra_engine_detailed.glb").status_code == 200

    # Digital Twin HTML UI page
    res_ui = client.get("/ui/4._3d_digital_twin_expansive_view/code.html")
    assert res_ui.status_code == 200
    assert "vajra-3d-canvas" in res_ui.text

def test_csv_upload_validation_and_row_errors(client, maintenance_headers):
    # 1. Valid spares CSV
    valid_csv = (
        "part_id,part_name,component,base_id,qty_in_stock,reorder_level,lead_time_days,unit_cost_inr_lakh,supplier\n"
        "PRT-001,Fan Blade Set,Fan,BASE01,8,4,45,18.5,HAL Aero\n"
        "PRT-002,HPC Compressor Kit,Compressor,BASE01,5,2,60,24.0,DRDO Depot\n"
    )
    res_valid = client.post(
        "/api/data/upload",
        data={"data_type": "spares"},
        files={"file": ("test_spares.csv", valid_csv.encode("utf-8"), "text/csv")},
        headers=maintenance_headers,
    )
    assert res_valid.status_code == 200
    val_data = res_valid.json()
    assert val_data["status"] == "success"
    assert val_data["ingested_rows"] == 2
    assert val_data["errors_count"] == 0

    # 2. Missing columns (HTTP 422 Unprocessable Entity)
    invalid_cols_csv = (
        "part_id,base_id,qty_in_stock\n"
        "PRT-001,BASE01,8\n"
    )
    res_missing = client.post(
        "/api/data/upload",
        data={"data_type": "spares"},
        files={"file": ("bad_spares.csv", invalid_cols_csv.encode("utf-8"), "text/csv")},
        headers=maintenance_headers,
    )
    assert res_missing.status_code == 422
    assert "missing_columns" in res_missing.json()["detail"]

    # 3. Row-level errors (corrupted data type in row 2)
    row_err_csv = (
        "part_id,part_name,component,base_id,qty_in_stock,reorder_level,lead_time_days,unit_cost_inr_lakh,supplier\n"
        "PRT-001,Fan Blade Set,Fan,BASE01,10,4,45,18.5,HAL Aero\n"
        "PRT-002,HPC Kit,Compressor,BASE01,NOT_A_NUMBER,2,60,24.0,DRDO Depot\n"
    )
    res_row_err = client.post(
        "/api/data/upload",
        data={"data_type": "spares"},
        files={"file": ("row_err_spares.csv", row_err_csv.encode("utf-8"), "text/csv")},
        headers=maintenance_headers,
    )
    assert res_row_err.status_code == 200
    row_data = res_row_err.json()
    assert row_data["status"] == "partial_success"
    assert row_data["ingested_rows"] == 1
    assert row_data["errors_count"] == 1
    assert row_data["row_errors"][0]["row"] == 3

def test_settings_health_bands_and_notifications(client, commander_headers):
    # Health bands GET
    res_hb = client.get("/api/settings/health-bands", headers=commander_headers)
    assert res_hb.status_code == 200
    bands = res_hb.json()
    assert "Healthy" in bands
    assert bands["Healthy"] == [70, 100]

    # Health bands PUT
    res_put_hb = client.put("/api/settings/health-bands", json={"Healthy": [75, 100], "Watch": [45, 74], "Critical": [0, 44]}, headers=commander_headers)
    assert res_put_hb.status_code == 200
    assert res_put_hb.json()["health_bands"]["Healthy"] == [75, 100]

    # Notifications GET & PUT
    res_notif = client.get("/api/settings/notifications", headers=commander_headers)
    assert res_notif.status_code == 200
    assert "console_banner" in res_notif.json()

    res_put_notif = client.put("/api/settings/notifications", json={"console_banner": True, "email": True, "sms": False}, headers=commander_headers)
    assert res_put_notif.status_code == 200
    assert res_put_notif.json()["notification_dispatch"]["email"] is True

def test_settings_user_lifecycle_and_disable(client, commander_headers):
    # Create user
    new_user_payload = {
        "service_id": "TEST-USR-99",
        "name": "Test Engineer",
        "role": "Maintenance Officer",
        "password": "Password@123",
        "base_id": "BASE01"
    }
    res_create = client.post("/api/settings/users", json=new_user_payload, headers=commander_headers)
    assert res_create.status_code == 200
    u_data = res_create.json()["user"]
    uid = u_data["id"]
    assert u_data["service_id"] == "TEST-USR-99"

    # Login works while active
    login_res = client.post("/api/auth/login", json={"service_id": "TEST-USR-99", "password": "Password@123"})
    assert login_res.status_code == 200

    # Disable user
    res_dis = client.post(f"/api/settings/users/{uid}/disable", headers=commander_headers)
    assert res_dis.status_code == 200
    assert res_dis.json()["is_active"] == 0

    # Login fails when disabled (403 Forbidden)
    login_fail = client.post("/api/auth/login", json={"service_id": "TEST-USR-99", "password": "Password@123"})
    assert login_fail.status_code == 403

    # Enable user back
    res_en = client.post(f"/api/settings/users/{uid}/enable", headers=commander_headers)
    assert res_en.status_code == 200
    assert res_en.json()["is_active"] == 1

    # Login works again
    login_again = client.post("/api/auth/login", json={"service_id": "TEST-USR-99", "password": "Password@123"})
    assert login_again.status_code == 200

def test_settings_bases_capacity_updates(client, commander_headers):
    # GET bases
    res_b = client.get("/api/settings/bases", headers=commander_headers)
    assert res_b.status_code == 200
    bases = res_b.json()
    assert len(bases) == 5

    # PUT bases
    updated = [{"base_id": "BASE01", "daily_maintenance_slots": 5, "hangar_bays": 3}]
    res_put = client.put("/api/settings/bases", json=updated, headers=commander_headers)
    assert res_put.status_code == 200

    # Verify update
    res_verify = client.get("/api/settings/bases", headers=commander_headers)
    b01 = next(b for b in res_verify.json() if b["base_id"] == "BASE01")
    assert b01["daily_maintenance_slots"] == 5
    assert b01["hangar_bays"] == 3

def test_simulator_reset_invariants(client, maintenance_headers):
    # Call reset
    res = client.post("/api/simulator/reset", headers=maintenance_headers)
    assert res.status_code == 200
    inv = res.json()["invariants"]
    assert inv["total_engines"] == 42
    assert inv["healthy_engines"] == 27
    assert inv["watch_engines"] == 12
    assert inv["critical_engines"] == 3

def test_audit_verification_and_tamper_detection(client, commander_headers):
    """Test cryptographic SHA-256 hash chaining and tamper detection."""
    from backend.app.database import SessionLocal
    from backend.app.models.user import AuditLog
    from backend.app.services.audit import log_audit, verify_audit_chain

    # 1. Verification of clean database
    res = client.get("/api/audit/verify", headers=commander_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["verified"] is True
    assert data["status"] == "intact"
    assert data["total_records"] >= 1
    assert data["failed_at_id"] is None

    # 2. Add an audit log entry via service and re-verify
    db = SessionLocal()
    try:
        new_entry = log_audit(
            db=db,
            user_id="IAF-001",
            user_role="Fleet Commander",
            action="VERIFICATION_TEST_ACTION",
            entity_type="ENGINE",
            entity_id="ENG-003",
            details="Automated audit verification test record."
        )
        assert new_entry is not None
        assert new_entry.prev_hash is not None
        assert new_entry.entry_hash is not None

        # Verify endpoint returns intact with updated record count
        res_after = client.get("/api/audit/verify", headers=commander_headers)
        assert res_after.status_code == 200
        assert res_after.json()["verified"] is True
        assert res_after.json()["total_records"] == data["total_records"] + 1

        # 3. Deliberately tamper with the entry directly in DB
        new_entry.details = "DELIBERATELY_TAMPERED_DETAILS"
        db.commit()

        # 4. Verify endpoint immediately flags corruption
        res_tampered = client.get("/api/audit/verify", headers=commander_headers)
        assert res_tampered.status_code == 200
        tamper_data = res_tampered.json()
        assert tamper_data["verified"] is False
        assert tamper_data["status"] == "corrupted"
        assert tamper_data["failed_at_id"] == new_entry.id
        assert "tampering detected" in tamper_data["detail"].lower()

        # 5. Clean up tampered record
        db.delete(new_entry)
        db.commit()
    finally:
        db.close()

    # Re-verify back to clean state
    res_restored = client.get("/api/audit/verify", headers=commander_headers)
    assert res_restored.status_code == 200
    assert res_restored.json()["verified"] is True

def test_alerts_lifecycle_and_persistence(client, commander_headers):
    """Test full alert lifecycle: Acknowledge, Assign, Create Work Order, Resolve."""
    # 1. Fetch active alerts
    res_list = client.get("/api/alerts?page=1&page_size=20", headers=commander_headers)
    assert res_list.status_code == 200
    alerts = res_list.json()["alerts"]
    assert len(alerts) > 0

    # Pick first unacknowledged or first alert
    target = alerts[0]
    aid = target["alert_id"]

    # 2. Acknowledge
    res_ack = client.patch(f"/api/alerts/{aid}", json={"status": "Acknowledged"}, headers=commander_headers)
    assert res_ack.status_code == 200
    assert res_ack.json()["status"] == "Acknowledged"

    # Verify persistence via fresh GET
    res_verify_ack = client.get(f"/api/alerts", headers=commander_headers)
    acked_alert = next(a for a in res_verify_ack.json()["alerts"] if a["alert_id"] == aid)
    assert acked_alert["status"] == "Acknowledged"

    # 3. Assign
    res_assign = client.patch(
        f"/api/alerts/{aid}",
        json={"assigned_to": "TECH-014", "status": "In Progress"},
        headers=commander_headers
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["assigned_to"] == "TECH-014"
    assert res_assign.json()["status"] == "In Progress"

    # 4. Create Work Order from Alert
    res_wo = client.post(
        f"/api/alerts/{aid}/work-order",
        json={
            "priority": "High",
            "task_description": f"Scheduled inspection for {target['engine_id']}",
            "assigned_technician": "TECH-014",
            "estimated_downtime_hours": 12
        },
        headers=commander_headers
    )
    assert res_wo.status_code == 200
    wo_data = res_wo.json()
    assert "work_order_id" in wo_data
    assert wo_data["alert_id"] == aid

    # Verify work_order_id is linked to the alert
    res_verify_wo = client.get(f"/api/alerts", headers=commander_headers)
    alert_after_wo = next(a for a in res_verify_wo.json()["alerts"] if a["alert_id"] == aid)
    assert alert_after_wo["work_order_id"] == wo_data["work_order_id"]
    assert alert_after_wo["status"] == "In Progress"

    # 5. Resolve
    res_res = client.patch(f"/api/alerts/{aid}", json={"status": "Resolved"}, headers=commander_headers)
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "Resolved"

def test_engine_reconciliation_and_critical_invariants(client, commander_headers):
    """Test that ENG-003, ENG-019, ENG-007 are the canonical critical engines."""
    res = client.get("/api/engines?status=Critical", headers=commander_headers)
    assert res.status_code == 200
    crit_data = res.json()
    assert crit_data["total"] == 3
    crit_engines = crit_data["items"]
    assert len(crit_engines) == 3

    crit_map = {e["engine_id"]: e for e in crit_engines}
    assert "ENG-003" in crit_map
    assert "ENG-019" in crit_map
    assert "ENG-007" in crit_map

    # Check exact scores and RUL
    e003 = crit_map["ENG-003"]
    assert e003["health_score"] == 18.0
    assert e003["predicted_rul_cycles"] == 8
    assert e003["status"] == "Critical"

    e019 = crit_map["ENG-019"]
    assert e019["health_score"] == 27.0
    assert e019["predicted_rul_cycles"] == 14
    assert e019["status"] == "Critical"

    e007 = crit_map["ENG-007"]
    assert e007["health_score"] == 35.0
    assert e007["predicted_rul_cycles"] == 22
    assert e007["status"] == "Critical"

def test_auth_expired_tokens_and_invalid_credentials(client):
    """Test wrong-password rejection and expired/malformed token handling."""
    # 1. Wrong password rejection
    bad_login = client.post("/api/auth/login", json={"service_id": "IAF-001", "password": "BadPassword999!"})
    assert bad_login.status_code == 401
    assert "invalid" in bad_login.json()["detail"].lower()

    # 2. Non-existent user
    unknown_login = client.post("/api/auth/login", json={"service_id": "NON-EXISTENT", "password": "Password123"})
    assert unknown_login.status_code == 401

    # 3. Expired / Malformed token
    res_bad_token = client.get("/api/auth/me", headers={"Authorization": "Bearer bad.token.value"})
    assert res_bad_token.status_code == 401




