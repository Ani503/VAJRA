import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.core.security import create_access_token
from backend.app.services.simulator import sim_manager
from backend.scripts.load_data import load_all_data

import shutil

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    db_path = ROOT_DIR / "vajra.db"
    backup_path = ROOT_DIR / "vajra.db.backup_test"
    if db_path.exists():
        shutil.copy2(db_path, backup_path)
    sim_manager.stop()
    load_all_data()
    yield
    sim_manager.stop()
    if backup_path.exists():
        shutil.copy2(backup_path, db_path)
        try:
            backup_path.unlink()
        except Exception:
            pass

@pytest.fixture(autouse=True)
def cleanup_simulator_after_each_test():
    yield
    if sim_manager.is_running or sim_manager.active_faults:
        sim_manager.stop()

@pytest.fixture(scope="session")
def client(setup_test_db):
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def db_session():
    db = SessionLocal()
    try:
        db.expire_all()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="session")
def commander_token():
    return create_access_token({"sub": "IAF-001", "role": "Fleet Commander"})

@pytest.fixture(scope="session")
def maintenance_token():
    return create_access_token({"sub": "IAF-002", "role": "Maintenance Officer"})

@pytest.fixture(scope="session")
def analyst_token():
    return create_access_token({"sub": "IAF-003", "role": "Analyst"})

@pytest.fixture(scope="session")
def commander_headers(commander_token):
    return {"Authorization": f"Bearer {commander_token}"}

@pytest.fixture(scope="session")
def maintenance_headers(maintenance_token):
    return {"Authorization": f"Bearer {maintenance_token}"}

@pytest.fixture(scope="session")
def analyst_headers(analyst_token):
    return {"Authorization": f"Bearer {analyst_token}"}
