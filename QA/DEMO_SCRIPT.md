# VAJRA: 5-Minute Evaluator Demonstration Flow
**Smart India Hackathon 2026 — Problem Statement 26249 (Ministry of Defence)**  
**Platform:** VAJRA: Predictive Maintenance & Fleet Availability Platform  
**Target Audience:** Technical Evaluation Committee & Defence Jury  
**Demonstration Time:** Exactly 5 Minutes  
**Prerequisites:** Backend running on `http://localhost:8000`, network offline (air-gapped)

---

## Storyline & Evaluation Hook
> *"In military aviation, unscheduled downtime isn't just an engineering bottleneck — it degrades operational combat availability. Today, aircraft telemetry, technical logs, base bay capacities, and depot spares live in siloed, fragmented databases. Maintenance is overwhelmingly reactive.  
> **VAJRA** unites these four critical data sources into a single air-gapped predictive analytics and 3D digital twin platform. Over the next five minutes, we will demonstrate how VAJRA detects a micro-anomaly days before physical failure, simulates the physical degradation in a 3D twin, resolves a supply chain bottleneck, and preserves fleet combat availability."*

---

## Demonstration Timeline Matrix

| Timestamp | Phase / Scene | Screen / Route | Core Action & Key Narrative |
|---|---|---|---|
| **0:00 – 0:30** | **Act 1: Authentication & Identity** | `terminal_authentication_vajra/code.html` | Introduce PS 26249, show stealth emblem, log in as Fleet Commander. |
| **0:30 – 1:15** | **Act 2: Unified Operational Picture** | `1._command_dashboard_master/code.html` | Demonstrate data integration, fleet invariants (42/27/12/3), 3D preview widget. |
| **1:15 – 2:00** | **Act 3: Live Telemetry Stream** | `10._data_simulator/code.html` | Initiate `/ws/live` stream, inspect healthy engine `ENG-001` telemetry. |
| **2:00 – 2:45** | **Act 4: Early Fault Detection** | `10._data_simulator/code.html` | Inject `vibration_spike` on `ENG-001`; show health dropping $<40$, WebSocket alert with lead time. |
| **2:45 – 3:30** | **Act 5: 3D Digital Twin & SHAP** | `4._3d_digital_twin_system_refined/code.html` | Turbine turns RED; toggle Normal/X-Ray/Exploded; inspect part for SHAP & stock. |
| **3:30 – 4:15** | **Act 6: Maintenance & Spares Optimizer** | `6._maintenance_planner_refined_alignment/code.html` | Auto-generated task, resolve spares bottleneck banner, transfer stock, approve plan. |
| **4:15 – 4:45** | **Act 7: Availability Scenario Modeling** | `8._fleet_availability/code.html` | Compare Predictive (87.5%) vs Baseline vs Reactive (66.7%); explain grounded root causes. |
| **4:45 – 5:00** | **Act 8: Compliance Report & Close** | `9._reports/code.html` | Export Daily Fleet Health PDF dossier; recap air-gap defense compliance. |

---

## Detailed Step-by-Step Evaluator Script

### ACT 1: Authentication & Defense Security (0:00 – 0:30)
1. **Open Browser to Login:** Navigate to `http://localhost:8000/ui/terminal_authentication_vajra/code.html`.
2. **Visual Highlight:** Point to the newly integrated, enlarged stealth fighter emblem with holographic cyan back-glow and clean transparent background.
3. **Spoken Cue:**
   > *"Welcome to VAJRA. Designed for air-gapped defense networks, VAJRA runs 100% locally with zero external cloud dependencies. We begin at the Secure Terminal Login."*
4. **Action:** Click the quick role pill **Fleet Commander** (auto-populates `IAF-001` and `Commander@123`). Click **AUTHENTICATE & INITIALIZE**.
5. **Outcome:** Instant authentication via local JWT Bearer token; redirects to the Command Dashboard.

---

### ACT 2: Data Integration & Unified Fleet Readiness (0:30 – 1:15)
1. **Screen:** Command Dashboard (`1._command_dashboard_master/code.html`).
2. **Spoken Cue:**
   > *"Here is the solution to PS 26249's fragmented data problem. Instead of logging into four separate systems, VAJRA integrates aircraft health telemetry, maintenance logs, depot spares, and base bay capacities into one operational picture."*
3. **Key Metrics to Highlight:**
   - **Total Fleet Size:** Exactly **42 engines** across **24 aircraft** and **5 operational bases**.
   - **Health Distribution:** **27 Healthy** ($70\text{--}100$), **12 Watch** ($40\text{--}69$), and **3 Critical** ($0\text{--}39$).
   - **Fleet Combat Readiness:** **87.5%** readiness index.
4. **Interactive Action:**
   - Use the **Base Readiness Filter** to toggle `Base 01`. Note how KPIs, at-risk engine tables, and hangar metrics dynamically adjust.
   - Gently rotate the **3D Twin Preview** widget embedded directly in the dashboard hero card.

---

### ACT 3: Real-Time Telemetry Stream & Healthy Baseline (1:15 – 2:00)
1. **Screen:** Telemetry Simulation Center (`10._data_simulator/code.html`).
2. **Spoken Cue:**
   > *"Under ordinary operations, engines operate within nominal flight envelopes. Let's start the real-time telemetry playback stream over WebSockets."*
3. **Interactive Action:**
   - Click **START SIMULATION**. Set speed multiplier to **5x**.
   - Point out the active `/ws/live` stream indicator in the footer and header bell.
   - Select engine **`ENG-001`** (stationed on aircraft `VJ-101` at `Base 01`).
   - Observe baseline readings: Vibration is nominal at $3.0\text{ mm/s}$, Exhaust Gas Temp ($T_{30}$) is $640^\circ\text{C}$, Health is **94.0** (Healthy band).

---

### ACT 4: Fault Injection & Real-Time Early Warning (2:00 – 2:45)
1. **Screen:** Telemetry Simulation Center (`10._data_simulator/code.html`).
2. **Spoken Cue:**
   > *"Now, let's simulate what happens when a critical bearing begins micro-spalling during a flight mission. We inject a physical vibration fault into the healthy engine ENG-001."*
3. **Interactive Action:**
   - Under Fault Injection, select **Vibration Spike (Rotor Unbalance / Bearing Spall)**.
   - Click **INJECT TARGET FAULT**.
4. **Observable Evidence:**
   - Watch the telemetry ticks update live:
     - Vibration jumps from $3.0\text{ mm/s} \to 4.1\text{ mm/s} \to 5.1\text{ mm/s}$.
     - Health score rapidly drops from $94.0 \to 68.8\text{ (Watch)} \to 16.5\text{ (Critical)}$.
   - An emergency tactical toast notification slides in from the top right:
     - **Alert ID:** `ALT-LIVE-ENG-001`
     - **Trigger:** `vibration_mm_s > 5.0 (Current: 5.09) - Immediate inspection required`
     - **Detection Lead Time:** **4.2 Days** before catastrophic operational failure.
5. **Spoken Cue:**
   > *"Notice the dual safety architecture: both unsupervised machine learning anomaly detection and our deterministic safety rule engine caught the exceedance simultaneously, giving technicians over four days of early warning."*

---

### ACT 5: 3D Digital Twin & SHAP Root-Cause Attribution (2:45 – 3:30)
1. **Screen:** 3D Digital Twin Expansive View (`4._3d_digital_twin_system_refined/code.html`).
2. **Spoken Cue:**
   > *"Technicians don't need to sift through thousands of raw CSV lines. They open the 3D Digital Twin."*
3. **Interactive Action:**
   - Select **`ENG-001`** from the engine dropdown.
   - Observe how the 3D turbofan mesh reflects real-time health: the **High-Pressure Turbine and Shaft** have dynamically turned **CRIMSON RED** ($< 40$).
   - Click **X-Ray View**: the outer casing turns semi-transparent cyan, showing internal shaft misalignment.
   - Click **Exploded View**: stages separate radially along the longitudinal axis.
   - Click on the **Turbine Assembly**:
     - The inspection drawer opens.
     - **Component Health:** $16.5$.
     - **Explainable AI (SHAP):** Shows vibration contributed $+0.41$ and $T_{30}$ $+0.32$ to the failure prediction.
     - **Supply Chain Link:** Lists required replacement part: `PRT-004 (HPT Blade Assembly)` and current base stock.

---

### ACT 6: Maintenance Planning & Spares Bottleneck Resolution (3:30 – 4:15)
1. **Screen:** Maintenance Planner (`6._maintenance_planner_refined_alignment/code.html`).
2. **Spoken Cue:**
   > *"The moment the anomaly was confirmed, VAJRA's automated pipeline created a priority-ranked maintenance task. But here is the real-world challenge: do we have the parts and bay capacity?"*
3. **Interactive Action:**
   - Point to the **Bottleneck Warning Banner**: `Base 03 has low stock for PRT-004`.
   - Click **"Request Stock Transfer"**:
     - Modal pops up pre-populated: Part `PRT-004`, Source `Base 01` (excess stock = 8), Destination `Base 03`, Quantity: 4.
     - Click **Execute Transfer**. The system validates stock levels and updates the $10 \times 5$ inventory heatmap.
   - Click **"Auto-optimise"**:
     - The constraint solver balances technician bay capacity across bases.
   - Click **"Approve Maintenance Plan"**:
     - Commits the hangar schedule and creates a cryptographically timestamped entry in the immutable `audit_log`.

---

### ACT 7: Fleet Availability & Scenario Modeling (4:15 – 4:45)
1. **Screen:** Fleet Availability & Mission Readiness Planner (`8._fleet_availability/code.html`).
2. **Spoken Cue:**
   > *"How does this translate to operational combat power? Let's compare the 14-day fleet availability projections across scenarios."*
3. **Interactive Action:**
   - Click **Baseline Scenario**: Availability drops to **79.2%** as aircraft wait for scheduled calendar maintenance.
   - Click **Reactive Scenario**: Availability plunges to **66.7%** due to unpredicted grounding and parts shortages.
   - Click **Predictive Scenario (VAJRA)**: Availability stabilizes at **87.5%**, comfortably exceeding the mission demand threshold curve.
   - Scroll down to the **Unavailable Aircraft Roster**:
     - Point out `VJ-101` (`ENG-001`): status Grounded, with root cause explicitly attributed: `Vibration spike & turbine stage thermal fatigue (RUL: 14 cycles)`.

---

### ACT 8: Operational Reports Dossier & Defense Conclusion (4:45 – 5:00)
1. **Screen:** Operational Reports & Compliance Export Center (`9._reports/code.html`).
2. **Spoken Cue:**
   > *"To conclude, commanders need actionable compliance dossiers for daily briefings."*
3. **Interactive Action:**
   - Select the **Daily Fleet Health & Readiness** template card.
   - Ensure format is set to **PDF**.
   - Click **GENERATE & DOWNLOAD DOSSIER**.
   - Show the downloaded PDF: vector formatting, executive KPIs, at-risk engine roster, and compliance verification hash.
4. **Closing Pitch:**
   > *"VAJRA solves Problem Statement 26249: from fragmented data to unified intelligence, from reactive failures to 4-day early detection, from supply chain paralysis to automated optimization. All running 100% offline in air-gapped security. Thank you."*

---

## Quick Reference: Demo Credentials & Shortcuts

| Item | Value / Shortcut | Description |
|---|---|---|
| **Fleet Commander Login** | `IAF-001` / `Commander@123` | Full administrative read/write access |
| **Maintenance Officer Login**| `IAF-002` / `Officer@123` | Operational access to planner & simulator |
| **Tactical Analyst Login** | `IAF-003` / `Analyst@123` | Read-only analytics & reporting access |
| **Quick Nav: Dashboard** | `Shift + D` | Jump to Command Dashboard |
| **Quick Nav: 3D Twin** | `Shift + T` | Jump to 3D Digital Twin View |
| **Quick Nav: Alerts** | `Shift + A` | Open Global Alerts Drawer |
| **Quick Nav: Engines** | `Shift + E` | Jump to Fleet Engine Inventory |
| **Close Modal / Drawer** | `Esc` | Close any active modal dialog |
