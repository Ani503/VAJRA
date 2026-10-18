import pytest
from backend.app.models import (
    BaseAgency,
    Aircraft,
    Engine,
    EngineHealthStatus,
    ComponentHealth,
    Alert,
    User,
    SparesInventory,
)
from backend.scripts.load_data import load_all_data

def test_database_counts_and_invariants(db_session):
    load_all_data()
    db_session.expire_all()
    # Total counts
    n_bases = db_session.query(BaseAgency).count()
    n_aircraft = db_session.query(Aircraft).count()
    n_engines = db_session.query(Engine).count()

    assert n_bases == 5, f"Expected 5 bases, found {n_bases}"
    assert n_aircraft == 24, f"Expected 24 aircraft, found {n_aircraft}"
    assert n_engines == 42, f"Expected 42 engines, found {n_engines}"

    # Engine status counts
    health_records = db_session.query(EngineHealthStatus).all()
    counts = {}
    for h in health_records:
        counts[h.status] = counts.get(h.status, 0) + 1

    assert counts.get("Healthy") == 27, f"Expected 27 Healthy, got {counts.get('Healthy')}"
    assert counts.get("Watch") == 12, f"Expected 12 Watch, got {counts.get('Watch')}"
    assert counts.get("Critical") == 3, f"Expected 3 Critical, got {counts.get('Critical')}"

def test_demo_overrides_engines(db_session):
    expected_overrides = {
        "ENG-003": {"health_score": 18.0, "status": "Critical", "rul": 8},
        "ENG-019": {"health_score": 27.0, "status": "Critical", "rul": 14},
        "ENG-007": {"health_score": 35.0, "status": "Critical", "rul": 22},
        "ENG-031": {"health_score": 52.0, "status": "Watch"},
        "ENG-014": {"health_score": 58.0, "status": "Watch"},
        "ENG-022": {"health_score": 63.0, "status": "Watch"},
        "ENG-038": {"health_score": 67.0, "status": "Watch"},
        "ENG-001": {"health_score": 94.0, "status": "Healthy"},
        "ENG-002": {"health_score": 92.0, "status": "Healthy"},
        "ENG-011": {"health_score": 89.0, "status": "Healthy"},
    }

    for eid, exp in expected_overrides.items():
        st = db_session.query(EngineHealthStatus).filter(EngineHealthStatus.engine_id == eid).first()
        assert st is not None, f"Engine {eid} not found in database"
        assert st.status == exp["status"], f"Engine {eid} status mismatch: expected {exp['status']}, got {st.status}"
        assert abs(st.health_score - exp["health_score"]) < 1.0, f"Engine {eid} health score mismatch: expected {exp['health_score']}, got {st.health_score}"
        if "rul" in exp:
            assert st.predicted_rul_cycles == exp["rul"], f"Engine {eid} RUL mismatch: expected {exp['rul']}, got {st.predicted_rul_cycles}"

def test_component_health_consistency(db_session):
    # Critical engine ENG-003 must have at least one Red component
    eng003_comps = db_session.query(ComponentHealth).filter(ComponentHealth.engine_id == "ENG-003").all()
    assert len(eng003_comps) == 5
    red_comps = [c for c in eng003_comps if c.colour == "Red"]
    assert len(red_comps) >= 1, "ENG-003 must have Red components"

    # Healthy engine ENG-001 must have Green components
    eng001_comps = db_session.query(ComponentHealth).filter(ComponentHealth.engine_id == "ENG-001").all()
    assert len(eng001_comps) == 5
    assert all(c.colour == "Green" for c in eng001_comps)

def test_spares_inventory_matrix_count(db_session):
    # 10 parts x 5 bases = 50 rows
    n_spares = db_session.query(SparesInventory).count()
    assert n_spares == 50, f"Expected 50 spares records, found {n_spares}"

def test_loader_idempotency(db_session):
    # Running load_all_data again should not duplicate rows or change invariant
    load_all_data()
    db_session.rollback()
    db_session.expire_all()

    assert db_session.query(Engine).count() == 42
    assert db_session.query(Aircraft).count() == 24
    assert db_session.query(BaseAgency).count() == 5

    health_records = db_session.query(EngineHealthStatus).all()
    counts = {}
    for h in health_records:
        counts[h.status] = counts.get(h.status, 0) + 1

    assert counts.get("Healthy") == 27
    assert counts.get("Watch") == 12
    assert counts.get("Critical") == 3
