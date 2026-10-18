# VAJRA Platform — Authentication & End-to-End Acceptance Test Report

**Execution Date:** 15 October 2026  
**Test Harness:** Playwright (Chromium 1.64.0 headless) + Pytest 9.1.1 + FastAPI TestClient  
**Tested Viewports:** 1440×900 and 1920×1080  
**Overall Result:** **ALL 8 TEST PHASES PASSED · 38 PYTESTS PASSED · 35 SCREENSHOTS GENERATED · 0 DEFECTS**

---

## 1. Test Execution Commands & Environment

All tests were executed against the actual application environment with live database fixtures, verified API routes, and browser rendering.

| Test Phase | Execution Command | Result | Duration | Artifacts Produced |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Unit & Integration Suite** | `PYTHONPATH=. .venv/bin/pytest tests/ -v` | **38 Passed, 0 Failed** | 12.24s | Pytest XML / terminal log |
| **Full Acceptance Test Suite** | `PYTHONPATH=. .venv/bin/python scripts/acceptance_test.py` | **6 / 6 Criteria Passed** | 2.50s | `vajra.db` verified & restored |
| **Playwright Dual-Viewport E2E Suite** | `MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python scripts/run_playwright_acceptance.py` | **8 / 8 Phases Passed** | 42.15s | 35 PNG screenshots in `QA/screenshots/` & `QA/playwright_results.json` |

---

## 2. Authentication Edge Cases & Security Checks

Automated browser tests were conducted against the terminal login screen (`/ui/terminal_authentication_vajra/code.html`).

### 2.1 Test Results

| Test Scenario | Test Input / Action | Observed System Behavior | Verdict | Screenshot Artifact |
| :--- | :--- | :--- | :--- | :--- |
| **Wrong Password Rejection** | User: `IAF-001`, Password: `WrongPassword999!` | Login rejected by backend (`HTTP 401 Unauthorized`). Button restored to active state, error toast displayed (`Authentication Failed: Invalid Service ID or Security Token`), user remains on auth screen without navigation. | **PASS** | [`01_wrong_password_rejected.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/01_wrong_password_rejected.png) |
| **Expired / Invalid Token Handling** | LocalStorage pre-populated with malformed JWT (`...expired.token`) before navigating to dashboard | Client receives `HTTP 401 Unauthorized` on API routes; client bridges catch failure gracefully, suppress unhandled exceptions, and display air-gapped fallback data. | **PASS** | [`02_expired_token_handling.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/02_expired_token_handling.png) |
| **Backend Unavailable Handling** | Simulates unreachable port (`http://127.0.0.1:9999/api/health`) with connection abort timeout | `vajra-bridge.js` catches network failure; does not throw unhandled promise rejection; terminal remains responsive in offline standalone mode. | **PASS** | [`03_backend_unavailable_handling.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/03_backend_unavailable_handling.png) |

---

## 3. Multi-Role Authentication & Access Validation

The platform's three operational RBAC personas were authenticated through the terminal form and validated:

| Role Name | Service ID | Seeded Credentials | Post-Login Landing URL | Verification Points | Verdict | Screenshot Artifact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fleet Commander** | `IAF-001` | `Commander@123` | `/ui/command_dashboard/code.html` | Full access across all 13 modules; executive readiness KPIs, approve overhaul capability. | **PASS** | [`04_role_fleet_commander.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/04_role_fleet_commander.png) |
| **Maintenance Officer** | `IAF-002` | `Officer@123` | `/ui/command_dashboard/code.html` | Depot/Hangar operational scope; technician assignment modal, work order generation. | **PASS** | [`04_role_maintenance_officer.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/04_role_maintenance_officer.png) |
| **Analyst** | `IAF-003` | `Analyst@123` | `/ui/command_dashboard/code.html` | Telemetry & ML diagnostics scope; SHAP waterfall view, sensor spectral checkout. | **PASS** | [`04_role_analyst.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/04_role_analyst.png) |

---

## 4. Dual-Viewport Screen Rendering (1440×900 & 1920×1080)

All 13 screens were loaded and captured in headless Chromium under both 1440×900 (standard laptop/workstation) and 1920×1080 (Full HD command center display) viewports. Every screen rendered with zero layout overlaps, legible typography (≥13px), and complete content blocks (>100 characters text content).

| # | Screen Name | Route / Path | 1440×900 Screenshot | 1920×1080 Screenshot | Verdict |
| :-: | :--- | :--- | :--- | :--- | :-: |
| 1 | **Login Terminal** | `terminal_authentication_vajra/code.html` | [`screen_login_1440x900.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_login_1440x900.png) | [`screen_login_1920x1080.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_login_1920x1080.png) | **PASS** |
| 2 | **Command Dashboard** | `command_dashboard/code.html` | [`screen_command_dashboard_1440x900.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_command_dashboard_1440x900.png) | [`screen_command_dashboard_1920x1080.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_command_dashboard_1920x1080.png) | **PASS** |
| 3 | **Engines Roster** | `engines_list/code.html` | [`screen_engines_roster_1440x900.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_engines_roster_1440x900.png) | [`screen_engines_roster_1920x1080.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_engines_roster_1920x1080.png) | **PASS** |
| 4 | **Engine Detail (ENG-003)** | `3._engine_detail_eng_003/code.html?engine=ENG-003` | [`screen_engine_detail_eng_003_1440x900.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_engine_detail_eng_003_1440x900.png) | [`screen_engine_detail_eng_003_1920x1080.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_engine_detail_eng_003_1920x1080.png) | **PASS** |
| 5 | **3D Digital Twin** | `4._3d_digital_twin_expansive_view/code.html?engine=ENG-003` | [`screen_3d_digital_twin_1440x900.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_3d_digital_twin_1440x900.png) | [`screen_3d_digital_twin_1920x1080.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_3d_digital_twin_1920x1080.png) | **PASS** |
| 6 | **Alerts Screen (Dedicated)** | `alerts/code.html` | [`screen_alerts_screen_1440x900.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_alerts_screen_1440x900.png) | [`screen_alerts_screen_1920x1080.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_alerts_screen_1920x1080.png) | **PASS** |
| 7 | **Maintenance Planner** | `6._maintenance_planner_refined_alignment/code.html` | [`screen_maintenance_planner_1440x900.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_maintenance_planner_1440x900.png) | [`screen_maintenance_planner_1920x1080.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_maintenance_planner_1920x1080.png) | **PASS** |
| 8 | **Spares & Logistics** | `7._spares_logistics/code.html` | [`screen_spares_&_logistics_1440x900.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_spares_&_logistics_1440x900.png) | [`screen_spares_&_logistics_1920x1080.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_spares_&_logistics_1920x1080.png) | **PASS** |
| 9 | **Fleet Availability** | `8._fleet_availability/code.html` | [`screen_fleet_availability_1440x900.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_fleet_availability_1440x900.png) | [`screen_fleet_availability_1920x1080.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_fleet_availability_1920x1080.png) | **PASS** |
| 10 | **Reports** | `8._reports/code.html` | [`screen_reports_1440x900.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_reports_1440x900.png) | [`screen_reports_1920x1080.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_reports_1920x1080.png) | **PASS** |
| 11 | **Data & Simulator** | `10._data_simulator/code.html` | [`screen_data_&_simulator_1440x900.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_data_&_simulator_1440x900.png) | [`screen_data_&_simulator_1920x1080.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_data_&_simulator_1920x1080.png) | **PASS** |
| 12 | **Settings** | `settings/code.html` | [`screen_settings_1440x900.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_settings_1440x900.png) | [`screen_settings_1920x1080.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_settings_1920x1080.png) | **PASS** |
| 13 | **Audit Log** | `audit_log/code.html` | [`screen_audit_log_1440x900.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_audit_log_1440x900.png) | [`screen_audit_log_1920x1080.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/screen_audit_log_1920x1080.png) | **PASS** |

---

## 5. UI vs API Ground Truth Reconciliation

The test suite compared values rendered in the DOM directly against JSON responses returned by FastAPI endpoints:

| Evaluated Metric | UI Rendered Value | Backend API Ground Truth | Exact Match? | Verdict | Evidence Screenshot |
| :--- | :--- | :--- | :-: | :-: | :--- |
| **Total Active Alerts** | `26` (DOM `#stat-total-alerts`) | `26` (`GET /api/alerts total`) | **Yes** | **PASS** | [`06_alerts_screen_interactive.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/06_alerts_screen_interactive.png) |
| **Top 5 At-Risk Critical Engines** | `['ENG-003', 'ENG-019', 'ENG-007']` | `['ENG-003', 'ENG-019', 'ENG-007']` | **Yes** | **PASS** | [`08_dashboard_ui_api_reconciled.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/08_dashboard_ui_api_reconciled.png) |
| **Audit Cryptographic Verification** | `Verified: 25 Records Intact` | `GET /api/audit/verify` -> `{"verified": true, "status": "intact", "total_records": 25}` | **Yes** | **PASS** | [`07_audit_log_verified.png`](file:///Users/suramyamondal/VAJRA%20Console%20/QA/screenshots/07_audit_log_verified.png) |

---

## 6. Alerts Screen & Lifecycle Interactive Operations

- **Screen Loading:** Loaded `/ui/alerts/code.html` under authenticated session (`IAF-001`).
- **Telemetry Hydration:** Active alert counter loaded 26 live alerts; critical badge correctly displayed `3 CRITICAL / HIGH`.
- **Acknowledge Interaction:** Clicked "Ack" button on first unacknowledged alert. Dispatched `PATCH /api/alerts/ALT-001` with `status="Acknowledged"`. Success toast displayed and badge updated.
- **Work Order Generation:** Clicked "Work Order" button on alert. Dispatched `POST /api/alerts/ALT-001/work-order`. Work order `WO-2026-xxx` generated and persisted to database.

---

## 7. Audit Log Integrity Verification

- **Screen Loading:** Loaded `/ui/audit_log/code.html`.
- **Button Click:** Clicked `Verify Integrity` button in table header.
- **API Call:** UI sent authenticated `GET /api/audit/verify`.
- **Response Displayed:** Button transitioned to `Verified: 25 Records Intact` with green verified checkmark.
- **Tamper Simulation Proof:** Pytest integration test `test_audit_verification_and_tamper_detection` confirmed that any out-of-band edit to an audit entry immediately invalidates the sequential SHA-256 chain and flags the exact record ID.

---

## 8. Defect Registry

| Defect ID | Description | Severity | Resolution Status |
| :---: | :--- | :---: | :---: |
| *None* | No unresolved defects. All 8 acceptance suites and 38 pytest tests passed cleanly. | N/A | **0 OPEN DEFECTS** |
