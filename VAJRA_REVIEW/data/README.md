# VAJRA - Synthetic Datasets (SIH 2026, PS 26249)
All data is SYNTHETIC. Generated with seed 42 by gen.py. Sensor structure mimics NASA C-MAPSS.

| File | Rows | Purpose |
|---|---|---|
| fleet_aircraft.csv | 24 | Aircraft master (type, base, flight hours) |
| engines.csv | 42 | Engine master, linked to aircraft |
| train_sensor_run_to_failure.csv | 15,092 | 60 engines run-to-failure, 15 sensors + RUL labels -> train XGBoost / Isolation Forest |
| test_sensor_truncated.csv + test_rul_ground_truth.csv | 3,288 / 20 | Test set and true RUL for RMSE / NASA score |
| engine_health_status.csv | 42 | Current health score, RUL, anomaly score, 7-day failure risk |
| component_health.csv | 210 | Per-component health + SHAP contribution -> 3D twin colours |
| live_stream_simulation.csv | 720 | 60 min live feed (6 engines, faults ramp up) -> WebSocket replay |
| alerts.csv | 23 | Alert log for dashboard |
| rule_engine_thresholds.csv | 10 | Manufacturer-limit safety fallback |
| maintenance_history.csv | 450 | Past maintenance / technical records |
| spares_inventory.csv | 50 | Parts stock per base with lead times |
| bases_maintenance_agencies.csv | 5 | Bases, daily maintenance slots, hangar bays |
| fleet_availability_history.csv | 900 | 180 days of mission-ready counts per base |
| mission_demand_next14d.csv | 70 | Aircraft required per base, next 14 days |

Aircraft types/names are fictional placeholders. Swap in real data when available.
