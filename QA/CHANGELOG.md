# VAJRA Platform QA Changelog & Bug Fix Ledger
**Smart India Hackathon 2026 — PS 26249 (Ministry of Defence)**
**Platform:** VAJRA: Predictive Maintenance & Fleet Availability Platform
**Audit Date:** 2026-10-15
**QA Lead & Fixer:** Lead Systems & QA Engineer

---

## 1. Summary of Fixes

| Bug ID | Component | Severity | Description | File(s) Touched | Status |
|---|---|---|---|---|---|
| **BUG-001** | Simulator Engine | P0 (Crash) | `NameError: name 'base_h' is not defined` at line 225 during telemetry loop execution. Caused telemetry stream to crash on start. | `backend/app/services/simulator.py` | **FIXED** |
| **BUG-002** | Asset Vendoring | P0 (Offline) | Multiple Google CDN links (`lh3.googleusercontent.com`, `cdn.tailwindcss.com`, `cdn.jsdelivr.net`) prevented offline self-contained operation. | All 12 HTML templates in `stitch_vajra_fleet_maintenance_platform/`, `vajra-bridge.js` | **FIXED** |
| **BUG-003** | Nomenclature / Generic Rule | P0 (Compliance) | Real equipment names (`AL31FP`, `AL-31`, `An-32`), personnel names (`Analyst Verma`, `sharma`), and branches (`INDIAN AIR FORCE`) violated SIH guidelines. | All HTML templates, `backend/app/services/pdf_report.py`, `vajra-bridge.js` | **FIXED** |
| **BUG-004** | Classification Jargon | P0 (Compliance) | Fake military classification markings (`RESTRICTED / FOUO`, `CLASSIFIED INTERNAL USE ONLY`, `FIPS-140`, `SECURITY LEVEL-4`) found in headers and PDF generation. | `backend/app/services/pdf_report.py`, HTML templates | **FIXED** |
| **BUG-005** | Admin Login Hero Logo | P1 (Visual/Branding) | Missing custom vector emblem on Admin Login screen; user requested prominent, attractive, enlarged placement of uploaded stealth emblem. | `stitch_vajra_fleet_maintenance_platform/terminal_authentication_vajra/code.html`, `Assets/` | **FIXED** |
| **BUG-006** | Global Alerts Drawer | P0 (Control) | Notification bells across page headers and "View all in alerts" had no interactive slide-out drawer or full alert lifecycle actions. | `stitch_vajra_fleet_maintenance_platform/vajra-bridge.js` | **FIXED** |
| **BUG-007** | Maintenance Planner | P0 (Workflow) | Dead controls on "Auto-optimise", "Approve plan", and stock transfer bottleneck banner. | `stitch_vajra_fleet_maintenance_platform/vajra-bridge.js` | **FIXED** |
| **BUG-008** | Spares Logistics & Heatmap | P0 (Workflow) | 10x5 heatmap table not connected to live database; action modals (Transfer, Reorder) lacked validation error handling. | `stitch_vajra_fleet_maintenance_platform/vajra-bridge.js` | **FIXED** |
| **BUG-009** | Reports Generation & Download | P0 (Reporting) | Template key mismatch (`daily` vs `daily_fleet_health`) caused HTTP 400 Bad Request; downloads used static mock report ID. | `stitch_vajra_fleet_maintenance_platform/vajra-bridge.js` | **FIXED** |
| **BUG-010** | Simulator Invariant Drift | P0 (Invariants) | Continuous telemetry replay degraded non-faulted engines to Critical if sensor readings crossed heuristic thresholds, breaking the 27/12/3 invariant. | `backend/app/services/simulator.py` | **FIXED** |
| **BUG-011** | Background Process Interference | P0 (Runtime) | Stale background server process PID 11904 running old in-memory simulator bytecode caused recurring engine status overwrites. | System Process Management | **FIXED** |

---

## 2. Detailed Technical Changelog

### BUG-001: Telemetry Simulator Crash on Undefined Variable
- **Root Cause:** In `backend/app/services/simulator.py`, the variable `base_h` was passed into `self.scorer.score_reading(...)` without being declared or initialized in the local loop scope.
- **Fix:** Added `base_h = eng_stat.health_score if eng_stat else 85.0` prior to ML scoring invocation.
- **Verification:** `tests/test_websocket.py` and `scripts/acceptance_test.py` pass cleanly without unhandled exceptions.

### BUG-002: Offline Self-Containment & Asset Vendoring
- **Root Cause:** The prototype relied on external CDN URLs for Tailwind CSS, Google UserContent imagery, and CDN Three.js scripts. Under air-gapped / offline defense deployment conditions, pages broke or failed to render styles and avatars.
- **Fix:**
  - Downloaded official production vendor scripts to `assets/vendor/`:
    - `three.min.js` (589 KB)
    - `OrbitControls.js` (26 KB)
    - `GLTFLoader.js` (94 KB)
    - `tailwindcss.js` (409 KB)
  - Created offline vector SVG avatar `assets/avatar.svg` and replaced all external profile image URLs across all 12 screens.
  - Replaced `<script src="https://cdn.tailwindcss.com"></script>` with local script tags in all 12 screens.
  - Updated `vajra-bridge.js` to dynamically load Three.js dependencies from local `assets/vendor/`.
- **Verification:** Full platform verified with network disabled (air-gapped simulation).

### BUG-003 & BUG-004: Nomenclature & Classification Sanitization
- **Root Cause:** Artifacts contained references to real military equipment (`AL-31FP`, `An-32`), locations, real personnel names, and fake classification banners (`RESTRICTED / FOUO`, `CLASSIFIED`).
- **Fix:**
  - Enforced SIH generic nomenclature standard:
    - Aircraft: `Transport-A`, `Fighter-B`, `Trainer-C`, `Heli-D`
    - Bases: `Base 01` through `Base 05`
    - Engines: `Turbofan-TF1`, `Turboshaft-TS1`
    - Roles: `Fleet Commander`, `Maintenance Officer`, `Analyst`
  - Replaced fake classification tags with professional military terms: `OFFICIAL OPERATIONAL REPORT`, `OFFICIAL USE ONLY`, `OPERATIONAL BRIEFING`.
  - Replaced `INDIAN AIR FORCE` with `VAJRA FLEET COMMAND`.
- **Verification:** Automated regex audit across backend python files and frontend HTML templates shows zero prohibited terms.

### BUG-005: Stealth Emblem Logo Integration & Login Elevation
- **Root Cause:** User requested prominent, attractive, enlarged placement of custom uploaded stealth jet emblem on the Admin Login screen.
- **Fix:**
  - Processed user image `media_1792034498743_a2ea39e8.jpg` to remove baked JPEG checkerboard transparency artifacts using connected component analysis, chromatic difference thresholding, and morphological smoothing.
  - Saved clean alpha-transparent asset to `Assets /vajra_logo_transparent.png`, `Assets /vajra_logo.png`, and `stitch_vajra_fleet_maintenance_platform/vajra_logo.png`.
  - Updated `stitch_vajra_fleet_maintenance_platform/terminal_authentication_vajra/code.html` with enlarged hero display (`w-72 sm:w-80 md:w-88`), multi-layer cyan/gold holographic radial back-glow, and interactive hover elevation.
- **Verification:** Visual inspection of transparent logo and login page layout.

### BUG-006: Global Alerts Drawer Implementation
- **Root Cause:** Header notification bells and "View all in alerts" had no interactive slide-out panel; alerts could only be viewed statically on the dashboard.
- **Fix:**
  - Implemented `setupGlobalAlertsDrawer()` in `vajra-bridge.js`.
  - Added slide-out tactical drawer markup with severity badges, search filter, and tab filters (`All`, `Critical`, `Warning`, `Info`, `Unacknowledged`, `Resolved`).
  - Added interactive controls on each alert:
    - **Acknowledge:** calls `PATCH /api/alerts/{id}`.
    - **Assign:** opens technician modal calling `PATCH /api/alerts/{id}`.
    - **Resolve:** calls `PATCH /api/alerts/{id}`.
    - **Create Work Order:** calls `POST /api/alerts/{id}/work-order`.
    - **Inspect Engine:** navigates to `3._engine_detail_eng_003/code.html?engine={id}`.
  - Connected live WebSocket alert listener to dynamically update the unacknowledged counter badge.
- **Verification:** Tested alert acknowledgement and work order generation against backend APIs.

### BUG-007: Maintenance Planner Automation & Bottleneck Resolution
- **Root Cause:** "Auto-optimise", "Approve plan", and "Request stock transfer" buttons on `6._maintenance_planner_refined_alignment/code.html` were non-functional.
- **Fix:**
  - Upgraded `hydrateMaintenancePlanner()` in `vajra-bridge.js`:
    - Wired `Auto-optimise` to `POST /api/maintenance/optimise`.
    - Wired `Approve plan` to `POST /api/maintenance/approve` with audit log creation.
    - Wired "Request stock transfer" on the Bottleneck Banner to open pre-filled transfer modal (`PRT-004` from `BASE01` to `BASE03`).
    - Wired "Conflicts only" filter checkbox.
- **Verification:** Pytest `test_maintenance_tasks_and_optimisation` and manual UI clicks verified.

### BUG-008: Spares Inventory Matrix & Action Modals
- **Root Cause:** Spares table was static mock data; transfer requests lacked validation against source stock.
- **Fix:**
  - Dynamically populated $10 \times 5$ inventory heatmap from `GET /api/spares`.
  - Added interactive `Transfer` and `Reorder` action modals with strict client/server validation.
  - Connected 30-day demand forecast endpoint `GET /api/spares/demand-forecast?horizon_days=30`.
- **Verification:** Verified that attempting to transfer when source == destination or quantity > stock returns HTTP 400 with user-friendly error banners.

### BUG-009: Tactical Reports Generation & Direct Download
- **Root Cause:** Report template names in `vajra-bridge.js` were converted to strings like `'weekly_maintenance_summary'`, which failed FastAPI Pydantic validation requiring exact keys (`daily_fleet_health`, `weekly_maintenance`, `alert_log`, `spares_risk`). Downloads were hardcoded to a static fake ID.
- **Fix:**
  - Mapped template cards to exact backend enum keys.
  - Implemented authenticated blob download in JavaScript: `fetch(`${API_BASE}/reports/${id}/download`)` with Authorization headers, generating a dynamic download anchor.
  - Implemented dynamic archive loader that lists generated reports from `GET /api/reports` with functional download buttons.
- **Verification:** All 4 report types (`daily_fleet_health`, `weekly_maintenance`, `alert_log`, `spares_risk`) generated and downloaded as both PDF and CSV.

### BUG-010 & BUG-011: Telemetry Loop Invariant Protection & Server Process Cleanup
- **Root Cause:** The telemetry simulation loop scored raw CSV rows and transitioned engines to Critical even if no fault had been injected, drifting the fleet away from the mandatory 27 Healthy / 12 Watch / 3 Critical invariant. Furthermore, a detached uvicorn process (PID 11904) was running old bytecode in the background.
- **Fix:**
  - Added guard in `simulator.py`: `transitioned_to_critical = is_faulted and (...)` ensuring only actively faulted engines transition to Critical during live telemetry.
  - Added health band clamps for nominal engines during replay (`score_res["health_score"] >= 70.0` for Healthy engines).
  - Terminated detached process PID 11904.
  - Executed idempotent reload via `load_all_data()`.
- **Verification:** Database invariant counts remain stable at 27 Healthy, 12 Watch, 3 Critical over time.

---

## 3. Findings 1–8 Resolution Ledger (Audit Remediation)

| Finding | Component | Requirement & Resolution | Status |
|---|---|---|---|
| **F-01** | Early Detection & ML Lead Time | Smooth health ramping (`f_info["ramp"]`), strictly monotonic anomaly progression, ML early warning (`source="ml"`, `severity="Medium"`) when health enters Watch band before rule breach, and calculated detection lead time (`lead_time_seconds > 0`). Verified in acceptance test. | **VERIFIED PASS** |
| **F-02** | ML Model Tuning & Honest Reporting | GroupKFold hyperparameter tuning in `ml/train.py` for XGBoost (`max_depth=3, learning_rate=0.08, n_estimators=120`, Test RMSE=17.872, NASA Score=134.946). Documented honest CV vs. test gap analysis in `README.md` and `ml/metrics.json`. | **VERIFIED PASS** |
| **F-03** | 100% Offline Asset Vendoring | Vendored IBM Plex Sans/Mono fonts, Material Symbols Outlined, Three.js r128, OrbitControls, and GLTFLoader in `assets/vendor/`. Removed all external Google Font and CDN links from all 12 HTML templates. Tested with network disabled. | **VERIFIED PASS** |
| **F-04** | Demo Reset & Database Isolation | Implemented `POST /api/simulator/reset` and wired UI button `btn-simulator-reset`. Configured automated database backup/restore in test fixtures (`tests/conftest.py` and `scripts/acceptance_test.py`) preventing test-time mutation of baseline `vajra.db`. | **VERIFIED PASS** |
| **F-05** | Settings Endpoints & RBAC Controls | Added `is_active` column to `User` model, added endpoints for health bands, notification rules, users (`POST /api/settings/users/{user_id}/disable`, `enable`), and bases capacity (`PUT /api/settings/bases`). Wired all interactive controls in `vajra-bridge.js` with audit logging. | **VERIFIED PASS** |
| **F-06** | Generic Naming Enforcement | Added `STATE_MAP` (Sector 01–05) and `SUPPLIER_MAP` (Depot-Alpha, Depot-Beta, Depot-Gamma, OEM Supplier) in `load_data.py`. Replaced all real air stations, places, and supplier names dynamically at database seed time without altering `/data`. | **VERIFIED PASS** |
| **F-07** | Documentation Scrubbing | Sanitized `README.md`: removed "quad-engine", "physics-informed", proprietary/MOD classification badges, and armed forces claims. Added explicit notes regarding synthetic training data and offline execution. | **VERIFIED PASS** |
| **F-08** | 3D Digital Twin GLB & Live Recolor | Configured FastAPI static route for `/assets/models/*.glb`, wired Three.js loader to dynamically load local GLB engine models, recolor parts from `GET /api/engines/{id}/components`, support Normal/X-ray/Exploded views, component inspection drawer, and live WebSocket recoloring. | **VERIFIED PASS** |

