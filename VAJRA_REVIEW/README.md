# VAJRA: Predictive Maintenance & Fleet Availability Platform
### Smart India Hackathon 2026 | Problem Statement PS 26249 | Ministry of Defence
**Review Package:** Prepared for External Technical Code Review & Evaluation  
**Directory:** `VAJRA_REVIEW/`  

---

## 1. Project Overview

**VAJRA** is an integrated predictive maintenance, digital twin, and fleet availability platform designed for military aviation assets. It integrates four core operational data streams into a unified relational model:
1. **Aircraft Health-Monitoring Systems** (real-time vibration, EGT, oil pressure, rotor speeds).
2. **Technical & Maintenance Records** (historical maintenance records, component failures, scheduled checks).
3. **Spares & Logistics Inventory** (multi-base parts stock, lead times, safety stocks).
4. **Maintenance Agencies & Bases** (hangar bay slot capacities, personnel, readiness targets).

### Core Capabilities
- **AI/ML Prognostics**: Tuned XGBoost regressor predicting Remaining Useful Life (RUL) with Random Forest baseline and SHAP feature attribution.
- **Early Detection**: Isolation Forest anomaly scoring rising monotonically during degradation; ML alert generated before physical safety rule breach; lead time calculated automatically.
- **Fail-Safe Rule Engine**: Deterministic safety envelope evaluating MIL-STD operational thresholds independently of ML.
- **Maintenance Planner**: Automated hangar slot constraint solver, risk-ranked tasks, spares stock validation, and audit logging.
- **14-Day Availability Simulator**: Scenario analysis comparing Baseline, Predictive, and Reactive operations.
- **3D Digital Twin**: WebGL CAD rendering of the airframe (33 parts) and turbofan assembly (7 parts) with X-ray, 100% exploded separation, and synchronized telemetry replay.
- **100% Air-Gapped & Offline**: Zero external network dependencies, CDNs, or cloud calls.

---

## 2. Quickstart Execution Guide

### Prerequisites
- **Python**: Python 3.11, 3.12, or 3.13 installed.
- **Browser**: Modern web browser (Chrome, Chromium, Firefox, Edge, or Safari) with WebGL support.
- **Hardware**: Standard laptop or workstation (runs fully local; no GPU required).

---

### Step 1: Environment Setup
Clone or extract the repository, navigate to the `VAJRA_REVIEW/` directory:

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install pinned requirements
pip install -r requirements.txt
```
*(Or simply run `make setup`)*

---

### Step 2: Environment Configuration
Copy the sanitized environment template:

```bash
cp .env.example .env
```

The default values in `.env` are configured for local offline execution using SQLite (`vajra.db`).

---

### Step 3: Database Ingestion & Initialization
Load and normalize all source CSV records from `data/` into `vajra.db`:

```bash
make load-data
# Alternatively: PYTHONPATH=. python backend/scripts/load_data.py
```
This populates all 42 engines, 24 aircraft, 5 bases, spares, alerts, and rules, asserting exact fleet invariants:
- **Total Engines:** 42 (27 Healthy / 12 Watch / 3 Critical)
- **Total Aircraft:** 24
- **Total Bases:** 5 (`Base 01` to `Base 05`)

---

### Step 4: ML Model Training & Metrics Verification
Verify and train the predictive maintenance models:

```bash
make train
# Alternatively: PYTHONPATH=. python ml/train.py
```
This performs 5-fold `GroupKFold` cross-validation grouped by engine ID, evaluates holdout test engines on their terminal cycles, and writes `ml/metrics.json`.

---

### Step 5: Start the Backend Server
Start the local FastAPI application:

```bash
make serve
# Alternatively: PYTHONPATH=. uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
The server will be available at:
- **API Server:** `http://localhost:8000`
- **Interactive OpenAPI Documentation:** `http://localhost:8000/docs`
- **WebSocket Live Telemetry Stream:** `ws://localhost:8000/ws/live`

---

### Step 6: Launch the Frontend Screens
The frontend runs as static client files served directly or through any static file server:

1. Open `frontend/terminal_authentication_vajra/code.html` directly in your browser.
2. Log in using the demo roles below, or use the quick role pills on the login screen.
3. Navigate across all 12 tactical screens using the global navigation sidebar.

---

## 3. Demo Roles & Authentication Credentials

| Service ID | User Name | Role | Demo Password | Access Level |
|---|---|---|---|---|
| **`IAF-001`** | Fleet Commander | Fleet Commander | `Commander@123` | **Full Admin**: Approve tasks, transfer stock, user admin |
| **`IAF-002`** | Maintenance Officer | Maintenance Officer | `Officer@123` | **Operations**: Create work orders, assign tasks, request parts |
| **`IAF-003`** | Analyst | Analyst | `Analyst@123` | **Read-Only**: Analytics, SHAP attribution, PDF reports |

*(Note: In production deployments, passwords can be overridden via `DEFAULT_COMMANDER_PASSWORD` in `.env`)*

---

## 4. Running the Verification & Test Suites

The repository contains three comprehensive automated test suites:

### Suite 1: Automated Unit & Integration Tests (34 Tests)
```bash
make test
# Alternatively: PYTHONPATH=. pytest tests/ -v
```
Verifies API routes, database counts, ML inference bounds, SHAP outputs, rule engine safety fallbacks, and WebSocket streams.

### Suite 2: End-to-End Acceptance Test (6 Criteria)
```bash
make acceptance
# Alternatively: PYTHONPATH=. python scripts/acceptance_test.py
```
Asserts:
1. Role-based login and token issuance.
2. Invariants: 42 engines (27 Healthy / 12 Watch / 3 Critical), 24 aircraft, 5 bases.
3. Fault injection on `ENG-001`: monotonic anomaly rise, early ML alert (`source="ml"`, severity Medium) with lead time > 0s, and automated task generation.
4. Fallback: `ML_ENABLED=false` still triggers safety rule engine alerts.
5. ML model metrics integrity (`ml/metrics.json`).
6. Pytest suite health.

### Suite 3: 3D Digital Twin Control Verification (53 Controls)
```bash
make twin-test
# Alternatively: PYTHONPATH=. python scripts/test_3d_twin_screen.py
```
Tests all 53 UI controls on the 3D twin screen (camera presets, view modes, 100% explode separation slider, spool test, control deflection test, replay scrubber, export telemetry, and raycast hit detection across all 33 airframe meshes and 7 turbofan parts).

---

## 5. Screen Inventory for Code Reviewers

| Screen Name | Path in `frontend/` | Key Features to Evaluate |
|---|---|---|
| **Terminal Login** | `terminal_authentication_vajra/code.html` | Role-based authentication, quick pills, error handling |
| **Command Dashboard** | `command_dashboard/code.html` | Fleet readiness KPIs, at-risk engines table, active alerts |
| **Fleet Engines** | `engines_list/code.html` | Status filter, search, sorting, pagination, CSV export |
| **Engine Detail (ENG-003)** | `3._engine_detail_eng_003/code.html` | Sensor sparklines, local SHAP attribution, component health |
| **3D Digital Twin** | `4._3d_digital_twin_expansive_view/code.html` | 33-part airframe, 7-part turbofan, X-ray, 100% exploded, replay |
| **Maintenance Planner** | `6._maintenance_planner_refined_alignment/code.html` | Auto-optimise bay slots, task approval, bottleneck banner |
| **Spares Logistics** | `7._spares_logistics/code.html` | 10 parts $\times$ 5 bases stock matrix, inter-base transfer modal |
| **Fleet Availability** | `8._fleet_availability/code.html` | 14-day forecast, scenario toggles (Baseline vs Predictive vs Reactive) |
| **Analytics & Reports** | `8._reports/code.html` | On-demand PDF/CSV report generation and download |
| **Data & Simulator** | `10._data_simulator/code.html` | Live WebSocket fault injection, speed control, demo reset |
| **Settings** | `settings/code.html` | Dynamic health bands, notification rules, user management |
| **Audit Log** | `audit_log/code.html` | Immutable audit trail with user attribution and timestamps |

---

## 6. Architecture & QA Documentation

- **System Architecture**: [`ARCHITECTURE.md`](file:///Users/suramyamondal/VAJRA%20Console%20/VAJRA_REVIEW/ARCHITECTURE.md)
- **Full QA Audit Report**: [`QA/QA_REPORT.md`](file:///Users/suramyamondal/VAJRA%20Console%20/VAJRA_REVIEW/QA/QA_REPORT.md)
- **3D Digital Twin Test Report**: [`QA/twin_test_report.md`](file:///Users/suramyamondal/VAJRA%20Console%20/VAJRA_REVIEW/QA/twin_test_report.md)
- **REST API Specification**: [`backend/API_ENDPOINTS.md`](file:///Users/suramyamondal/VAJRA%20Console%20/VAJRA_REVIEW/backend/API_ENDPOINTS.md)
- **Interactive Evaluator Script**: [`QA/DEMO_SCRIPT.md`](file:///Users/suramyamondal/VAJRA%20Console%20/VAJRA_REVIEW/QA/DEMO_SCRIPT.md)
- **Change Log**: [`QA/CHANGELOG.md`](file:///Users/suramyamondal/VAJRA%20Console%20/VAJRA_REVIEW/QA/CHANGELOG.md)
