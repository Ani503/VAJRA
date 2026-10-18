# VAJRA Platform Inventory & Gap Analysis
**Smart India Hackathon 2026 — Problem Statement 26249 (Ministry of Defence)**
*Audited & Compiled by Antigravity QA Lead*
*Timestamp: 2026-10-15*

---

## 1. System Overview & Running Services
- **Backend Architecture**: FastAPI 0.115+ running on Uvicorn ASGI server (`backend/app/main.py`), utilizing SQLite (`vajra.db`) with SQLAlchemy ORM and Pydantic v2 schemas.
- **Frontend Architecture**: Modern tactical dark-mode dashboard UI (`stitch_vajra_fleet_maintenance_platform/`), utilizing HTML5, Tailwind CSS, Material Symbols Outlined, IBM Plex Sans/Mono fonts, Three.js WebGL digital twin rendering engine, and the `vajra-bridge.js` unified client adapter.
- **Server Ports**:
  - FastAPI REST API & WebSocket: `http://localhost:8000`
  - OpenAPI Interactive Swagger UI: `http://localhost:8000/docs`
  - OpenAPI ReDoc: `http://localhost:8000/redoc`
  - Static Frontend Mount: `http://localhost:8000/ui/` (and root redirect to command dashboard)
  - Static Assets Mount: `http://localhost:8000/assets/`

---

## 2. API Endpoints Inventory (from OpenAPI Specification)
Total API Paths: **36**  
Total HTTP Operations: **45**  
WebSocket Endpoints: **1** (`/ws/live`)

### 2.1 Health & System Status
| Method | Path | Role Required | Description |
|---|---|---|---|
| `GET` | `/api/health` | Public | System liveness probe and operational metadata |
| `GET` | `/api/system/status` | Authenticated | Live telemetry stream status, ML model readiness, database connectivity, and air-gap flag |

### 2.2 Authentication & User Management
| Method | Path | Role Required | Description |
|---|---|---|---|
| `POST` | `/api/auth/login` | Public | Service personnel authentication issuing signed Bearer JWT |
| `GET` | `/api/auth/me` | Authenticated | Current authenticated user identity, role, and clearance profile |
| `GET` | `/api/settings/users` | Commander Only | Full list of provisioned service accounts |
| `POST` | `/api/settings/users` | Commander Only | Create new user account with role assignment |
| `PATCH` | `/api/settings/users/{user_id}` | Commander Only | Update user role, status, or credentials |

### 2.3 Command Dashboard
| Method | Path | Role Required | Description |
|---|---|---|---|
| `GET` | `/api/dashboard/summary` | Authenticated | Comprehensive executive KPIs, top 5 at-risk engines, alert rollups, fleet readiness %, and 3D digital twin preview state |

### 2.4 Engines Inventory & Diagnostics
| Method | Path | Role Required | Description |
|---|---|---|---|
| `GET` | `/api/engines` | Authenticated | Filtered, searchable, paginated fleet engine inventory with RUL, health band, and anomaly scores |
| `GET` | `/api/engines/{engine_id}` | Authenticated | Detailed telemetry metrics, sensor time-series history, RUL degradation trajectory, SHAP attribution, and maintenance history |
| `GET` | `/api/engines/{engine_id}/components` | Authenticated | Component breakdown (Turbine, Compressor, Combustion Chamber, Shaft, Fan) with individual health scores, SHAP contributions, linked spare parts, and base stock levels |

### 2.5 Alerts & Work Orders
| Method | Path | Role Required | Description |
|---|---|---|---|
| `GET` | `/api/alerts` | Authenticated | Filterable alert feed with severity, status, and engine filters, plus global summary statistics |
| `GET` | `/api/alerts/{alert_id}` | Authenticated | Specific alert inspection with recommended maintenance actions |
| `PATCH` | `/api/alerts/{alert_id}` | Maintenance / Cmdr | Acknowledge, assign technician, or resolve alert |
| `POST` | `/api/alerts/{alert_id}/work-order` | Maintenance / Cmdr | Escalate alert directly into an authorized maintenance work order |

### 2.6 Maintenance Planning & Optimization
| Method | Path | Role Required | Description |
|---|---|---|---|
| `GET` | `/api/maintenance/tasks` | Authenticated | List all active, scheduled, and completed maintenance tasks ranked by risk |
| `POST` | `/api/maintenance/tasks` | Maintenance / Cmdr | Create new manual maintenance task |
| `GET` | `/api/maintenance/schedule` | Authenticated | 7-day hangar bay & daily slot maintenance schedule matrix per base |
| `POST` | `/api/maintenance/optimise` | Maintenance / Cmdr | Algorithmic scheduling optimization against hangar capacities, technician slots, and spare parts availability |
| `POST` | `/api/maintenance/approve` | Maintenance / Cmdr | Formal approval of maintenance assignments with immutable audit ledger write |

### 2.7 Spares Logistics & Supply Chain
| Method | Path | Role Required | Description |
|---|---|---|---|
| `GET` | `/api/spares` | Authenticated | Comprehensive $10 \times 5$ parts stock matrix (10 spare types across 5 operational bases), reorder levels, and critical stock alerts |
| `POST` | `/api/spares/reorder` | Maintenance / Cmdr | Trigger procurement requisition with depot/manufacturer |
| `POST` | `/api/spares/transfer` | Maintenance / Cmdr | Inter-base inventory transfer with strict stock-level validation |
| `GET` | `/api/spares/demand-forecast` | Authenticated | 30-day spares consumption forecast driven by predicted remaining useful life (RUL) |

### 2.8 Fleet Availability & Mission Readiness
| Method | Path | Role Required | Description |
|---|---|---|---|
| `GET` | `/api/fleet/availability` | Authenticated | 14-day fleet availability projections under baseline, predictive, and reactive scenarios with unavailable aircraft downtime attribution |

### 2.9 Operational Reports & Dossiers
| Method | Path | Role Required | Description |
|---|---|---|---|
| `GET` | `/api/reports` | Authenticated | Historical archive of compiled operational intelligence reports |
| `POST` | `/api/reports` | Authenticated | Dynamic report generation across 4 report types (Fleet Health, Maintenance Summary, Alert Log & Anomalies, Spares Risk) in PDF or CSV |
| `GET` | `/api/reports/{report_id}/download` | Authenticated | Secure file download of generated PDF dossiers or CSV exports |

### 2.10 Data Ingestion & Live Simulator
| Method | Path | Role Required | Description |
|---|---|---|---|
| `POST` | `/api/data/upload` | Maintenance / Cmdr | Multipart CSV batch upload with strict schema and row-level validation |
| `POST` | `/api/simulator/start` | Maintenance / Cmdr | Initiate asynchronous real-time telemetry playback |
| `POST` | `/api/simulator/stop` | Maintenance / Cmdr | Halt telemetry playback stream |
| `POST` | `/api/simulator/speed` | Maintenance / Cmdr | Dynamically alter playback time multiplier ($0.5\times$ to $20\times$) |
| `POST` | `/api/simulator/inject-fault` | Maintenance / Cmdr | Inject targeted physical anomalies (vibration spike, EGT exceedance, oil pressure drop) on target engines |
| `GET` | `/api/simulator/state` | Authenticated | Current simulator status, timeline step offset, and active injected faults |

### 2.11 Settings, Policies & Immutable Audit Log
| Method | Path | Role Required | Description |
|---|---|---|---|
| `GET` / `PUT` | `/api/settings/thresholds` | Cmdr (PUT) | Inspect or update rule engine safety alert thresholds |
| `GET` / `PUT` | `/api/settings/health-bands` | Cmdr (PUT) | Inspect or reconfigure health score thresholds (Healthy, Watch, Critical) |
| `GET` / `PUT` | `/api/settings/notifications` | Cmdr (PUT) | Inspect or configure operational alert notification dispatch channels |
| `GET` / `PUT` | `/api/settings/bases` | Cmdr (PUT) | Base maintenance bay capacities and daily slot quotas |
| `GET` / `PUT` | `/api/settings/data-retention` | Cmdr (PUT) | Configure sensor and telemetry data retention windows |
| `GET` | `/api/audit-log` | Authenticated | Immutable audit log ledger query with filtering and CSV export |

### 2.12 WebSocket Live Telemetry Feed
| Protocol | Path | Authorization | Description |
|---|---|---|---|
| `WS` | `/ws/live` | Handshake | Bi-directional real-time feed streaming sensor readings, computed health/anomaly snapshots, and immediate threshold breach alert frames |

---

## 3. Frontend Pages & Screen Routes
The web application is located in `stitch_vajra_fleet_maintenance_platform/` and consists of 12 dedicated HTML screens:

| # | Screen Directory / File | User Interface Purpose | Key Controls |
|---|---|---|---|
| 1 | `terminal_authentication_vajra/code.html` | Secure Terminal Login | Service ID & password fields, Quick role-switch pills (Fleet Commander, Maintenance Officer, Analyst), Error handling |
| 2 | `command_dashboard/code.html` | Command Dashboard | 4 KPI cards, Health distribution, Base readiness filter, Top 5 at-risk engine table, Active alerts card, Interactive 3D preview |
| 3 | `engines_list/code.html` | Fleet Engines Inventory | Search bar, Status / Base / Type filters, Column sorting, Pagination, Rows-per-page, Batch Diagnostics, Export CSV |
| 4 | `3._engine_detail_eng_003/code.html` | Individual Engine Telemetry & SHAP | Live telemetry gauges, Sensor history graphs, RUL degradation curve, Component health table, SHAP feature importance, Embedded 3D viewer |
| 5 | `4._3d_digital_twin_expansive_view/code.html` | 3D Digital Twin Expansive View | Engine/Aircraft selector, Normal / X-ray / Exploded display modes, Camera presets, Rotor spin toggle, Component inspection drawer, Replay timeline slider, Fault simulation |
| 6 | `6._maintenance_planner_refined_alignment/code.html` | Maintenance Planning | Ranked task backlog, 7-day hangar bay Gantt calendar, Base slot capacity meters, Auto-optimise engine, Batch Approve, Conflict alerts banner |
| 7 | `7._spares_logistics/code.html` | Spares & Logistics | Inventory KPIs, Critical shortage warning banner, $10 \times 5$ interactive stock heatmap, Part reorder modal, Inter-base transfer modal, 30-day demand forecast curve |
| 8 | `8._fleet_availability/code.html` | Fleet Availability Projections | 14-day availability chart vs demand, Baseline vs Predictive vs Reactive scenario toggles, Base readiness cards, Unavailable aircraft downtime attribution table |
| 9 | `8._reports/code.html` | Operational Reports Dossier | 4 Report template cards, Date range selector, Base filter, Format toggle (PDF / CSV), Live preview pane, Download report button, Historical report archive |
| 10 | `10._data_simulator/code.html` | Data Ingestion & Live Simulator | Playback controls (Start / Stop / Speed), Target engine selector, Fault injection panel (Vibration, EGT, Oil pressure), CSV batch uploader with drag-and-drop & row validation, System health panel |
| 11 | `settings/code.html` | Configuration & Policies | Rule engine thresholds form, Health band sliders, Notification webhook/email settings, Base slot allocations, User management table, Reset defaults |
| 12 | `audit_log/code.html` | Immutable Audit Ledger | Action & entity type filters, Date range filter, Search, Verification hash drawer, CSV audit export |

---

## 4. Machine Learning Models, Pipeline & Metrics
The machine learning pipeline resides in `ml/` and utilizes models trained with engine-grouped cross-validation:

### 4.1 Models Implemented & Saved (`ml/models/`)
1. **Anomaly Detection (Unsupervised)**:
   - `isolation_forest.joblib`: Isolation Forest trained on normal operating sensor features.
   - `anomaly_calibration.joblib`: Min-Max percentile calibrator mapping raw decision function to $[0.0, 1.0]$.
   - `live_iforest.joblib` & `live_calibration.joblib`: Streamlined real-time inference model for live telemetry scoring.
2. **Remaining Useful Life (RUL) Regressors**:
   - `xgb_rul_model.joblib`: Primary gradient-boosted decision tree regressor (XGBoost) predicting remaining flight cycles.
   - `rf_rul_model.joblib`: Baseline Random Forest regressor for performance benchmarking.
3. **Model Explainability & Preprocessing**:
   - `feature_pipeline.joblib`: Robust scaler and rolling window aggregator ($5\text{-cycle}$ rolling mean/std).
   - `feature_names.joblib`: 90 engineered sensor feature column names.
   - `shap_explainer.joblib`: TreeSHAP explainer for computing local feature importance and attributing anomalies to physical components.

### 4.2 ML Performance Metrics (`ml/metrics.json`)
- **Training Setup**: 60 training engines, 20 test engines (engine-level train/validation split to prevent temporal leakage).
- **Target Variable**: Piecewise linear RUL capped at 125 cycles.
- **XGBoost Primary Model**:
  - Test RMSE: **18.141 cycles**
  - Test MAE: **12.236 cycles**
  - 5-Fold Cross-Validation Mean RMSE: **9.994 cycles**
  - NASA Asymmetric Scoring Function: **144.403** (heavily penalizes late predictions over early ones)
- **Random Forest Baseline**:
  - Test RMSE: **17.670 cycles**
  - Test MAE: **12.123 cycles**
  - 5-Fold Cross-Validation Mean RMSE: **10.138 cycles**
  - NASA Asymmetric Scoring Function: **140.864**
- **Synthetic Data Disclosure**: Explicitly documented in code and UI that models are trained on synthetic C-MAPSS style telemetry.

---

## 5. 3D Digital Twin Assets & Viewers
- **Physical Assets**:
  - `Assets /Models/vajra_aircraft_twin.glb` ($334\text{ KB}$): 33-node airframe digital twin with hierarchical components (avionics bay, wings, control surfaces, landing gear, twin turbofans, hydraulic lines).
  - `Assets /Models/vajra_engine_detailed.glb` ($557\text{ KB}$): Detailed multi-stage turbofan digital twin with internal fan rotor, compressor stages, combustor liner, high/low pressure turbines, bearings, and afterburner nozzle.
- **Standalone Embedded Redundancy**:
  - `stitch_vajra_fleet_maintenance_platform/vajra-3d-models.js`: Base64 embedded GLB binaries (`VAJRA_EMBEDDED_MODELS.aircraft` and `VAJRA_EMBEDDED_MODELS.engine`) providing $100\%$ offline availability when file loading is restricted.
- **3D Interaction Features**:
  - Three viewing modes: **Normal PBR**, **X-ray / Transparent**, and **Exploded View**.
  - Dynamic part recoloring based on real-time health score:
    - Green (`#3FA34D`): Healthy ($70\text{--}100$)
    - Yellow (`#E6B800`): Watch ($40\text{--}69$)
    - Red (`#D64545`): Critical ($0\text{--}39$)
  - Interactive raycasting: Clicking any part opens component telemetry, SHAP importance, linked spare part ID, and on-base inventory stock.
  - Controls: Orbital camera rotate/pan/zoom, rotor spin animation toggle, component isolation, and replay timeline scrubber.

---

## 6. Gap Analysis Against P0 Checklist Requirements
An initial audit against checklist items reveals the following status and identified gaps:

| Item | Requirement | Current Status | Identified Gap / Required Fix |
|---|---|---|---|
| **P0-1** | Data integration of all 4 sources, CSV upload with row-level validation, system status | **PARTIAL** | Backend has endpoints; frontend simulator upload button needs to properly display row-level error modal rather than generic alert. |
| **P0-2** | Consistent anomaly score, RUL, health score, 7-day failure risk across screens | **PASS** | `apiFetch` syncs values; verification needed to ensure static fallbacks in HTML match DB values. |
| **P0-3** | Fault injection on healthy engine drops health $<40$, anomaly rises, alert arrives on WebSocket with lead time | **PASS** | Implemented in simulator service; WebSocket delivers alert frame with `lead_time_days`. |
| **P0-4** | Maintenance planning: risk ranking, slot capacity check, spares check, conflict banner, approve + audit log | **PARTIAL** | Planner UI renders Gantt and optimization; need to verify conflict banner wiring and audit log persistence on Approve. |
| **P0-5** | Fleet availability: 14-day forecast vs demand, baseline/predictive/reactive scenario comparison, unavailable table | **PASS** | API `/api/fleet/availability` provides complete scenario data and grounded aircraft reasons. |
| **P0-6** | Spares: $10 \times 5$ heatmap, reorder and transfer validation, 30-day forecast | **PASS** | Spares API and UI support heatmap and transfer validation (rejects transfer if source stock $< \text{transfer qty}$). |
| **P0-7** | Digital twin: GLB loads, Normal/X-ray/Exploded modes, health recoloring, part click details, replay slider | **PASS** | Full Three.js engine with embedded model fallback and real-time color updating. |
| **P0-8** | Live monitoring: WebSocket stream drives live charts and alerts, speed/start/stop controls work | **PASS** | WebSocket stream connected; playback controls trigger backend simulator. |
| **P0-9** | Reports: 4 report types $\times$ PDF and CSV download | **PASS** | Backend ReportLab and CSV generator implemented; verification of download controls needed. |
| **P0-10**| Fleet invariant consistency: 42 engines (27 Healthy / 12 Watch / 3 Critical), 24 aircraft, 5 bases everywhere | **PARTIAL** | Backend DB conforms to invariant; frontend HTML templates contain legacy static mock strings that must be fully sanitized. |
| **Naming**| Generic names only (`Transport-A`, `Fighter-B`, `Trainer-C`, `Heli-D`, `Base 01-05`), no real names/places/ranks/jargon | **FAIL** | Real places (`Ambala`, `Halwara`, `Gwalior`, `Bareilly`, `Sulur`), real people (`Sharma`, `Pillai`, `Gupta`), military ranks, real aircraft (`Su-30MKI`), and fake classification text (`FIPS-140`, `SECURITY LEVEL-4`, `AIR-GAP ISOLATED`) exist in HTML and seed data. **Must be thoroughly purged.** |
