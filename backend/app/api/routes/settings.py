import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.auth import require_commander, require_maintenance_or_above, require_any_authenticated
from backend.app.models import (
    RuleEngineThreshold,
    Setting,
    User,
    BaseAgency,
)
from backend.app.schemas.system import RuleThresholdItem
from backend.app.core.security import get_password_hash
from backend.app.services.audit import log_audit
from backend.app.core.rule_engine import rule_engine

router = APIRouter(prefix="/settings", tags=["Settings & Administration"])

# --- Thresholds ---
@router.get("/thresholds", response_model=List[RuleThresholdItem])
def get_thresholds(
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    rules = db.query(RuleEngineThreshold).all()
    return [
        RuleThresholdItem(
            id=r.id,
            parameter=r.parameter,
            operator=r.operator,
            threshold=r.threshold,
            severity=r.severity,
            recommended_action=r.recommended_action,
        )
        for r in rules
    ]

@router.put("/thresholds")
def update_thresholds(
    thresholds: List[RuleThresholdItem],
    db: Session = Depends(get_db),
    current_user = Depends(require_commander),
):
    db.query(RuleEngineThreshold).delete()
    for t in thresholds:
        db.add(RuleEngineThreshold(
            parameter=t.parameter,
            operator=t.operator,
            threshold=t.threshold,
            severity=t.severity,
            recommended_action=t.recommended_action,
        ))
    db.commit()

    # Reload active rule engine memory
    rule_engine.load_rules(db)

    log_audit(
        db,
        current_user.service_id,
        current_user.role,
        "UPDATE_SETTINGS",
        "RULE_THRESHOLDS",
        None,
        f"Updated {len(thresholds)} rule engine safety thresholds",
    )

    return {"status": "success", "message": f"Successfully updated {len(thresholds)} safety thresholds"}

# --- Health Bands ---
@router.get("/health-bands")
def get_health_bands(
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    setting = db.query(Setting).filter(Setting.key == "health_bands").first()
    if setting:
        return json.loads(setting.value)
    return {"Healthy": [70, 100], "Watch": [40, 69], "Critical": [0, 39]}

@router.put("/health-bands")
def update_health_bands(
    bands: Dict[str, List[int]],
    db: Session = Depends(get_db),
    current_user = Depends(require_commander),
):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    setting = db.query(Setting).filter(Setting.key == "health_bands").first()
    if setting:
        setting.value = json.dumps(bands)
        setting.updated_at = now_str
    else:
        db.add(Setting(key="health_bands", value=json.dumps(bands), description="Fleet Health Bands", updated_at=now_str))
    db.commit()

    log_audit(db, current_user.service_id, current_user.role, "UPDATE_SETTINGS", "HEALTH_BANDS", None, str(bands))
    return {"status": "success", "health_bands": bands}

# --- Notifications ---
@router.get("/notifications")
def get_notifications_setting(
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    setting = db.query(Setting).filter(Setting.key == "notification_dispatch").first()
    if setting:
        return json.loads(setting.value)
    return {"sms": False, "email": False, "console_banner": True}

@router.put("/notifications")
def update_notifications_setting(
    cfg: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(require_commander),
):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    setting = db.query(Setting).filter(Setting.key == "notification_dispatch").first()
    if setting:
        setting.value = json.dumps(cfg)
        setting.updated_at = now_str
    else:
        db.add(Setting(key="notification_dispatch", value=json.dumps(cfg), description="Notification Dispatch", updated_at=now_str))
    db.commit()

    log_audit(db, current_user.service_id, current_user.role, "UPDATE_SETTINGS", "NOTIFICATIONS", None, str(cfg))
    return {"status": "success", "notification_dispatch": cfg}

# --- Users (Commander only) ---
@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user = Depends(require_commander),
):
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "service_id": u.service_id,
            "name": u.name,
            "role": u.role,
            "base_id": u.base_id,
            "created_at": u.created_at,
            "is_active": getattr(u, "is_active", 1),
        }
        for u in users
    ]

@router.post("/users")
def create_user(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(require_commander),
):
    service_id = data.get("service_id")
    name = data.get("name")
    role = data.get("role", "Analyst")
    password = data.get("password")
    base_id = data.get("base_id")

    if not service_id or not name or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="service_id, name, and password required")

    existing = db.query(User).filter(User.service_id == service_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User {service_id} already exists")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = User(
        service_id=service_id,
        name=name,
        role=role,
        password_hash=get_password_hash(password),
        base_id=base_id,
        created_at=now_str,
        is_active=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit(db, current_user.service_id, current_user.role, "CREATE_USER", "USER", service_id, f"Created user {name} ({role})")
    return {"status": "success", "user": {"id": user.id, "service_id": user.service_id, "name": user.name, "role": user.role, "is_active": user.is_active}}

@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user = Depends(require_commander),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")

    if "name" in data:
        user.name = data["name"]
    if "role" in data:
        user.role = data["role"]
    if "base_id" in data:
        user.base_id = data["base_id"]
    if "is_active" in data:
        user.is_active = int(data["is_active"])
    if "password" in data and data["password"]:
        user.password_hash = get_password_hash(data["password"])

    db.commit()
    log_audit(db, current_user.service_id, current_user.role, "UPDATE_USER", "USER", user.service_id, f"Updated user {user.service_id}")
    return {"status": "success", "message": f"User {user.service_id} updated", "is_active": user.is_active}

@router.post("/users/{user_id}/disable")
def disable_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_commander),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
    user.is_active = 0
    db.commit()
    log_audit(db, current_user.service_id, current_user.role, "DISABLE_USER", "USER", user.service_id, f"Disabled user {user.service_id}")
    return {"status": "success", "message": f"User {user.service_id} disabled", "user_id": user.id, "is_active": 0}

@router.post("/users/{user_id}/enable")
def enable_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_commander),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
    user.is_active = 1
    db.commit()
    log_audit(db, current_user.service_id, current_user.role, "ENABLE_USER", "USER", user.service_id, f"Enabled user {user.service_id}")
    return {"status": "success", "message": f"User {user.service_id} enabled", "user_id": user.id, "is_active": 1}

# --- Bases ---
@router.get("/bases")
def list_bases(
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    bases = db.query(BaseAgency).all()
    return [
        {"base_id": b.base_id, "base_name": b.base_name, "state": b.state, "daily_maintenance_slots": b.daily_maintenance_slots, "hangar_bays": b.hangar_bays}
        for b in bases
    ]

@router.put("/bases")
def update_bases(
    bases_data: List[Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    items = bases_data if isinstance(bases_data, list) else [bases_data]
    for b_in in items:
        b = db.query(BaseAgency).filter(BaseAgency.base_id == b_in.get("base_id")).first()
        if b:
            if "daily_maintenance_slots" in b_in:
                b.daily_maintenance_slots = int(b_in["daily_maintenance_slots"])
            if "hangar_bays" in b_in:
                b.hangar_bays = int(b_in["hangar_bays"])
            if "state" in b_in:
                b.state = str(b_in["state"])
            if "base_name" in b_in:
                b.base_name = str(b_in["base_name"])
    db.commit()
    log_audit(db, current_user.service_id, current_user.role, "UPDATE_SETTINGS", "BASES", None, f"Updated {len(items)} base operational capacities")
    return {"status": "success", "message": "Updated base capacity settings"}

# --- Data Retention ---
@router.get("/data-retention")
def get_data_retention(
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    setting = db.query(Setting).filter(Setting.key == "data_retention_days").first()
    return {"data_retention_days": int(setting.value if setting else 365)}

@router.put("/data-retention")
def update_data_retention(
    data: Dict[str, int],
    db: Session = Depends(get_db),
    current_user = Depends(require_commander),
):
    days = data.get("data_retention_days", 365)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    setting = db.query(Setting).filter(Setting.key == "data_retention_days").first()
    if setting:
        setting.value = str(days)
        setting.updated_at = now_str
    else:
        db.add(Setting(key="data_retention_days", value=str(days), description="Data retention in days", updated_at=now_str))
    db.commit()

    log_audit(db, current_user.service_id, current_user.role, "UPDATE_SETTINGS", "DATA_RETENTION", None, f"Set to {days} days")
    return {"status": "success", "data_retention_days": days}
