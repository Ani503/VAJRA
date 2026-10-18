# VAJRA REST API & WebSocket Documentation
## SIH 2026 — Problem Statement 26249 (Ministry of Defence)

Base URL: `http://localhost:8000`  
Interactive OpenAPI UI: `http://localhost:8000/docs`  
OpenAPI JSON Specification: `backend/openapi.json`  

---

### Authentication & Role-Based Access Control

The platform enforces Role-Based Access Control (RBAC) via Bearer JWTs:
- **Fleet Commander (`IAF-001`)**: Full unrestricted access across fleet operations, configuration, thresholds, and administrative settings.
- **Maintenance Officer (`IAF-002`)**: Operational control over maintenance tasks, work orders, spares logistics, and telemetry simulations. Cannot manage administrative users.
- **Analyst (`IAF-003`)**: Read-only situational awareness dashboards, reports generation, and data export.

```bash
# Obtain Bearer token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"service_id": "IAF-001", "password": "Commander@123"}'
```

---

### Endpoints Matrix

| Category | Method | Path | Role Required | Purpose |
|---|---|---|---|---|
| **Health** | `GET` | `/api/health` | Public | Liveness check & service mode metadata |
| **Auth** | `POST` | `/api/auth/login` | Public | Authenticate service personnel & return JWT |
| | `GET` | `/api/auth/me` | Authenticated | Inspect profile of current authenticated user |
| **Dashboard** | `GET` | `/api/dashboard/summary` | Authenticated | High-level KPIs, 3D twin preview, alerts summary, 14-day projections |
| **Engines** | `GET` | `/api/engines` | Authenticated | Filtered, searchable, paginated fleet engine inventory |
| | `GET` | `/api/engines/{id}` | Authenticated | Detailed telemetry, components, RUL curve, SHAP features, records |
| | `GET` | `/api/engines/{id}/components`| Authenticated | Component health, SHAP scores, and linked spares for 3D twin |
| **Alerts** | `GET` | `/api/alerts` | Authenticated | Paginated alert feed with severity filters & summary counts |
| | `GET` | `/api/alerts/{id}` | Authenticated | Individual alert details & recommended maintenance action |
| | `PATCH`| `/api/alerts/{id}` | Maint / Cmdr | Acknowledge, assign, or resolve alert |
| | `POST` | `/api/alerts/{id}/work-order` | Maint / Cmdr | Elevate alert directly into an authorized Work Order |
| **Maintenance**| `GET` | `/api/maintenance/tasks` | Authenticated | List suggested & scheduled maintenance tasks |
| | `POST` | `/api/maintenance/tasks` | Maint / Cmdr | Manually log or schedule a maintenance task |
| | `GET` | `/api/maintenance/schedule` | Authenticated | 7-day hangar bay & daily slot schedule grouped by base |
| | `POST` | `/api/maintenance/optimise` | Maint / Cmdr | AI-driven schedule optimization & parts conflict detection |
| | `POST` | `/api/maintenance/approve` | Maint / Cmdr | Batch approve maintenance tasks |
| **Spares** | `GET` | `/api/spares` | Authenticated | 10 parts x 5 bases inventory matrix & stock KPIs |
| | `POST` | `/api/spares/reorder` | Maint / Cmdr | Place spare module reorder with manufacturer/depot |
| | `POST` | `/api/spares/transfer` | Maint / Cmdr | Inter-base parts transfer with stock validation |
| | `GET` | `/api/spares/demand-forecast`| Authenticated | 30-day spares demand forecast driven by predicted RUL |
| **Fleet** | `GET` | `/api/fleet/availability` | Authenticated | Base availability % and scenario simulations (predictive/baseline/reactive) |
| **Reports** | `GET` | `/api/reports` | Authenticated | View history of generated operational reports |
| | `POST` | `/api/reports` | Authenticated | Generate professional PDF dossier (with Matplotlib chart) or CSV |
| | `GET` | `/api/reports/{id}/download`| Authenticated | Download compiled PDF or CSV file |
| **Data & Sim** | `POST` | `/api/data/upload` | Maint / Cmdr | Validate and ingest CSV sensor, maintenance, or spares batches |
| | `GET` | `/api/system/status` | Authenticated | Live feed health, model readiness, and air-gapped status |
| | `POST` | `/api/simulator/start` | Maint / Cmdr | Start background real-time telemetry replay |
| | `POST` | `/api/simulator/stop` | Maint / Cmdr | Pause telemetry replay |
| | `POST` | `/api/simulator/speed` | Maint / Cmdr | Adjust simulation speed multiplier (0.5x - 20x) |
| | `POST` | `/api/simulator/inject-fault` | Maint / Cmdr | Dynamic fault injection (vibration, EGT, oil pressure) on any engine |
| | `GET` | `/api/simulator/state` | Authenticated | Current simulator state, step offset, and active faults |
| **Settings** | `GET/PUT`| `/api/settings/thresholds` | Cmdr (PUT) | Inspect or reconfigure safety rule thresholds |
| | `GET/PUT`| `/api/settings/health-bands` | Cmdr (PUT) | Inspect or update healthy/watch/critical thresholds |
| | `GET/PUT`| `/api/settings/notifications`| Cmdr (PUT) | Configure operational alert notification dispatch |
| | `GET/POST/PATCH`| `/api/settings/users` | Cmdr only | Full user administration (create, update roles, change passwords) |
| | `GET/PUT`| `/api/settings/bases` | Cmdr (PUT) | Reconfigure daily maintenance slots & hangar bays |
| | `GET/PUT`| `/api/settings/data-retention`| Cmdr (PUT) | Set data retention period |
| | `GET` | `/api/audit-log` | Authenticated | Full immutable system audit log (JSON or CSV export) |
| **Live Feed** | `WS` | `/ws/live` | Public / WS | Real-time WebSocket streaming telemetry & fault alerts |

---

### Sample Endpoint Responses

#### 1. `GET /api/dashboard/summary`
```json
{
  "total_engines": 42,
  "healthy_engines": 27,
  "watch_engines": 12,
  "critical_engines": 3,
  "total_aircraft": 24,
  "total_bases": 5,
  "fleet_readiness_pct": 87.5,
  "mean_health": 74.8,
  "mean_rul": 138.2,
  "top_5_engines_at_risk": [
    {
      "engine_id": "ENG-003",
      "aircraft_id": "VJ-102",
      "aircraft_type": "Fighter-B",
      "base_id": "BASE01",
      "health_score": 18.0,
      "status": "Critical",
      "predicted_rul_cycles": 8,
      "anomaly_score": 0.885,
      "failure_risk_7d": 0.742
    }
  ],
  "active_alert_counts": {
    "total": 26,
    "unacknowledged": 8,
    "in_progress": 11,
    "resolved": 7,
    "high_critical": 6,
    "medium_warning": 14
  },
  "digital_twin_preview": {
    "engine_id": "ENG-003",
    "health_score": 18.0,
    "status": "Critical",
    "components": {
      "Turbine": { "health_score": 14.0, "colour": "Red", "shap_contribution": 0.44 },
      "Compressor": { "health_score": 26.0, "colour": "Red", "shap_contribution": 0.31 },
      "Combustion Chamber": { "health_score": 14.0, "colour": "Red", "shap_contribution": 0.38 },
      "Shaft": { "health_score": 36.0, "colour": "Red", "shap_contribution": 0.18 },
      "Fan": { "health_score": 36.0, "colour": "Yellow", "shap_contribution": 0.12 }
    }
  }
}
```

#### 2. `GET /api/engines/ENG-003/components`
```json
[
  {
    "component": "Turbine",
    "health_score": 14.0,
    "colour": "Red",
    "shap_contribution": 0.44,
    "spare_part_id": "PRT-004",
    "spare_part_name": "Turbine Blade Set",
    "qty_in_stock_at_base": 2,
    "lead_time_days": 75
  },
  {
    "component": "Shaft",
    "health_score": 36.0,
    "colour": "Red",
    "shap_contribution": 0.18,
    "spare_part_id": "PRT-005",
    "spare_part_name": "Main Shaft Bearing",
    "qty_in_stock_at_base": 3,
    "lead_time_days": 30
  }
]
```

#### 3. `POST /api/maintenance/optimise`
```json
{
  "assignments": [
    {
      "task_id": "TSK-001",
      "engine_id": "ENG-003",
      "base_id": "BASE01",
      "component": "Turbine",
      "scheduled_date": "2026-10-12",
      "part_available": true,
      "part_id": "PRT-004",
      "urgency": "Immediate",
      "priority_score": 328.5
    }
  ],
  "conflicts": [
    "Turbine Blade Set out of stock at BASE03 (Lead time: 75 days)"
  ],
  "capacity_utilization_pct": 82.5,
  "summary": "Optimized 5 tasks across 5 bases. Identified 1 inventory or capacity constraints."
}
```

#### 4. `WS /ws/live` Message Formats
- Telemetry reading frame:
  ```json
  {
    "type": "reading",
    "data": {
      "timestamp": "2026-10-11 09:15:30",
      "engine_id": "ENG-001",
      "temp_c": 481.5,
      "pressure_kpa": 98.7,
      "vibration_mm_s": 2.12,
      "fan_rpm": 8945.0,
      "oil_pressure_psi": 54.6,
      "egt_c": 625.2
    },
    "health_snapshot": {
      "health_score": 88.5,
      "status": "Healthy",
      "predicted_rul_cycles": 142,
      "anomaly_score": 0.165
    }
  }
  ```
- Fault trigger alert frame:
  ```json
  {
    "type": "alert",
    "alert_id": "ALT-LIVE-140510-ENG-001",
    "engine_id": "ENG-001",
    "aircraft_id": "VJ-101",
    "severity": "High",
    "trigger": "vibration_mm_s > 5.0 (Current: 7.20) - Immediate inspection",
    "source": "ml",
    "anomaly_score": 0.942,
    "rul_cycles": 8,
    "recommended_action": "Ground aircraft and execute immediate borescope inspection"
  }
  ```
