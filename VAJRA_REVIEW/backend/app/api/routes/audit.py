import io
import csv
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.database import get_db
from backend.app.core.auth import require_any_authenticated
from backend.app.models.user import AuditLog
from backend.app.schemas.system import AuditLogItem, AuditVerificationResponse
from backend.app.services.audit import verify_audit_chain

router = APIRouter(tags=["Audit Log"])

def handle_get_audit_log(
    user_id: Optional[str],
    action: Optional[str],
    export: Optional[str],
    page: int,
    page_size: int,
    db: Session,
):
    query = db.query(AuditLog)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)

    query = query.order_by(desc(AuditLog.timestamp))

    if export == "csv":
        logs = query.all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Timestamp", "User ID", "User Role", "Action", "Entity Type", "Entity ID", "Details", "Prev Hash", "Entry Hash"])
        for l in logs:
            writer.writerow([
                l.id, l.timestamp, l.user_id, l.user_role, l.action,
                l.entity_type, l.entity_id or "", l.details or "",
                l.prev_hash or "", l.entry_hash or ""
            ])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_log.csv"}
        )

    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()

    items = [
        AuditLogItem(
            id=l.id,
            timestamp=l.timestamp,
            user_id=l.user_id,
            user_role=l.user_role,
            action=l.action,
            entity_type=l.entity_type,
            entity_id=l.entity_id,
            details=l.details,
            prev_hash=l.prev_hash,
            entry_hash=l.entry_hash,
        )
        for l in records
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.get("/audit-log")
@router.get("/audit")
def get_audit_log(
    user_id: Optional[str] = Query(None, description="Filter by user service ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    export: Optional[str] = Query(None, description="Set to 'csv' for CSV download"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    return handle_get_audit_log(user_id, action, export, page, page_size, db)

@router.get("/audit/verify", response_model=AuditVerificationResponse)
@router.get("/audit-log/verify", response_model=AuditVerificationResponse)
def verify_audit(
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    """
    Cryptographic SHA-256 verification of audit log chain.
    Validates sequential hash continuity from genesis block to current entry.
    """
    result = verify_audit_chain(db)
    return AuditVerificationResponse(**result)
