import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.user import AuditLog

GENESIS_HASH = "0" * 64

def compute_entry_hash(
    prev_hash: str,
    timestamp: str,
    user_id: str,
    user_role: str,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[str] = None
) -> str:
    raw = f"{prev_hash}|{timestamp}|{user_id}|{user_role}|{action}|{entity_type}|{entity_id or ''}|{details or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def log_audit(
    db: Session,
    user_id: str,
    user_role: str,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    details: Optional[str] = None
) -> Optional[AuditLog]:
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        last_entry = db.query(AuditLog).order_by(desc(AuditLog.id)).first()
        prev_hash = last_entry.entry_hash if (last_entry and last_entry.entry_hash) else GENESIS_HASH
        entry_hash = compute_entry_hash(
            prev_hash=prev_hash,
            timestamp=now_str,
            user_id=user_id,
            user_role=user_role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=details
        )
        entry = AuditLog(
            timestamp=now_str,
            user_id=user_id,
            user_role=user_role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=details,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except Exception:
        db.rollback()
        return None

def verify_audit_chain(db: Session) -> Dict[str, Any]:
    """
    Sequentially verifies cryptographic SHA-256 hash chaining across all audit log records.
    Each entry must correctly link to the preceding entry's hash, and the recomputed hash
    must match the stored hash.
    """
    entries = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    if not entries:
        return {
            "verified": True,
            "status": "intact",
            "total_records": 0,
            "genesis_hash": GENESIS_HASH,
            "latest_hash": None,
            "failed_at_id": None,
            "detail": "No audit records present to verify."
        }

    expected_prev = GENESIS_HASH
    for entry in entries:
        if entry.prev_hash != expected_prev:
            return {
                "verified": False,
                "status": "corrupted",
                "total_records": len(entries),
                "genesis_hash": GENESIS_HASH,
                "latest_hash": None,
                "failed_at_id": entry.id,
                "detail": f"Hash chain broken at record #{entry.id}: stored prev_hash does not match previous record."
            }

        recomputed = compute_entry_hash(
            prev_hash=entry.prev_hash,
            timestamp=entry.timestamp,
            user_id=entry.user_id,
            user_role=entry.user_role,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            details=entry.details
        )

        if entry.entry_hash != recomputed:
            return {
                "verified": False,
                "status": "corrupted",
                "total_records": len(entries),
                "genesis_hash": GENESIS_HASH,
                "latest_hash": None,
                "failed_at_id": entry.id,
                "detail": f"Content tampering detected at record #{entry.id}: entry_hash does not match recomputed SHA-256."
            }

        expected_prev = entry.entry_hash

    return {
        "verified": True,
        "status": "intact",
        "total_records": len(entries),
        "genesis_hash": GENESIS_HASH,
        "latest_hash": entries[-1].entry_hash if entries else None,
        "failed_at_id": None,
        "detail": f"Cryptographic SHA-256 integrity verified across all {len(entries)} audit records."
    }
