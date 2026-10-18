from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.database import get_db
from backend.app.core.auth import require_any_authenticated
from backend.app.models import Engine, Aircraft, Alert, SimulatorState
from backend.app.schemas.system import SystemStatusResponse
from backend.app.config import settings
from ml.inference import ml_inference

router = APIRouter(prefix="/system", tags=["System Status"])

@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    # Test DB connection
    db_connected = True
    try:
        db.execute(text("SELECT 1;"))
    except Exception:
        db_connected = False

    sim_state = db.query(SimulatorState).first()
    live_feed_status = "Active" if (sim_state and sim_state.is_running) else "Idle"

    n_engines = db.query(Engine).count() if db_connected else 0
    n_aircraft = db.query(Aircraft).count() if db_connected else 0
    active_alerts = db.query(Alert).filter(Alert.status.in_(["Unacknowledged", "In Progress"])).count() if db_connected else 0

    return SystemStatusResponse(
        database_connected=db_connected,
        live_feed_status=live_feed_status,
        models_loaded=ml_inference.is_loaded,
        ml_enabled=settings.ML_ENABLED,
        offline_mode=settings.OFFLINE_MODE,
        last_sync=datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        total_engines=n_engines,
        total_aircraft=n_aircraft,
        active_alerts=active_alerts,
    )
