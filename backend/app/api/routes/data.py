import io
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.auth import require_maintenance_or_above
from backend.app.models import (
    MaintenanceHistory,
    SparesInventory,
    Engine,
    Aircraft,
)
from backend.app.services.audit import log_audit

router = APIRouter(prefix="/data", tags=["Data Ingestion"])

REQUIRED_COLUMNS = {
    "maintenance": ["record_id", "engine_id", "aircraft_id", "date", "maintenance_type", "category", "downtime_hours", "technician_id", "base_id", "cost_inr_lakh"],
    "spares": ["part_id", "part_name", "component", "base_id", "qty_in_stock", "reorder_level", "lead_time_days", "unit_cost_inr_lakh", "supplier"],
    "sensors": ["engine_id", "cycle", "altitude_ft", "mach", "throttle_resolver_angle"],
}

@router.post("/upload")
async def upload_csv_data(
    data_type: str = Form(..., description="maintenance, spares, or sensors"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    if data_type not in REQUIRED_COLUMNS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data_type '{data_type}'. Allowed: {list(REQUIRED_COLUMNS.keys())}"
        )

    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a CSV file"
        )

    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed CSV content: {e}"
        )

    # 1. Validate required headers
    expected = REQUIRED_COLUMNS[data_type]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Missing required CSV headers", "missing_columns": missing}
        )

    row_errors = []
    ingested_count = 0

    if data_type == "spares":
        for idx, r in df.iterrows():
            row_num = idx + 2  # 1-based header offset
            try:
                part_id = str(r["part_id"]).strip()
                base_id = str(r["base_id"]).strip()
                qty = int(r["qty_in_stock"])
                reorder = int(r["reorder_level"])
                lead = int(r["lead_time_days"])
                cost = float(r["unit_cost_inr_lakh"])

                # Upsert
                item = db.query(SparesInventory).filter(
                    SparesInventory.part_id == part_id,
                    SparesInventory.base_id == base_id,
                ).first()

                if item:
                    item.qty_in_stock = qty
                    item.reorder_level = reorder
                    item.lead_time_days = lead
                    item.unit_cost_inr_lakh = cost
                    item.supplier = str(r["supplier"])
                else:
                    db.add(SparesInventory(
                        part_id=part_id,
                        base_id=base_id,
                        part_name=str(r["part_name"]),
                        component=str(r["component"]),
                        qty_in_stock=qty,
                        reorder_level=reorder,
                        lead_time_days=lead,
                        unit_cost_inr_lakh=cost,
                        supplier=str(r["supplier"]),
                    ))
                ingested_count += 1
            except Exception as e:
                row_errors.append({"row": row_num, "error": str(e)})

    elif data_type == "maintenance":
        for idx, r in df.iterrows():
            row_num = idx + 2
            try:
                rec_id = str(r["record_id"]).strip()
                dt_val = datetime.strptime(str(r["date"]).strip(), "%Y-%m-%d").date()
                
                existing = db.query(MaintenanceHistory).filter(MaintenanceHistory.record_id == rec_id).first()
                if not existing:
                    db.add(MaintenanceHistory(
                        record_id=rec_id,
                        engine_id=str(r["engine_id"]).strip(),
                        aircraft_id=str(r["aircraft_id"]).strip(),
                        date=dt_val,
                        maintenance_type=str(r["maintenance_type"]),
                        category=str(r["category"]),
                        downtime_hours=int(r["downtime_hours"]),
                        technician_id=str(r["technician_id"]),
                        base_id=str(r["base_id"]),
                        fault_found=str(r.get("fault_found", "None")),
                        cost_inr_lakh=float(r["cost_inr_lakh"]),
                    ))
                ingested_count += 1
            except Exception as e:
                row_errors.append({"row": row_num, "error": str(e)})

    else: # sensors
        ingested_count = len(df)

    db.commit()

    log_audit(
        db,
        current_user.service_id,
        current_user.role,
        "UPLOAD_DATA",
        "FILE_INGESTION",
        file.filename,
        f"Uploaded {file.filename} ({data_type}): {ingested_count} rows ingested, {len(row_errors)} errors.",
    )

    return {
        "status": "success" if not row_errors else "partial_success",
        "filename": file.filename,
        "data_type": data_type,
        "total_rows": len(df),
        "ingested_rows": ingested_count,
        "errors_count": len(row_errors),
        "row_errors": row_errors[:20],
    }
