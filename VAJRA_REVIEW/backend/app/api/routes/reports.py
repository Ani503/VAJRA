import os
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.database import get_db
from backend.app.core.auth import require_any_authenticated
from backend.app.models.system import Report
from backend.app.schemas.report import CreateReportRequest, ReportResponse
from backend.app.services.pdf_report import generate_pdf_report, generate_csv_report
from backend.app.services.audit import log_audit

router = APIRouter(prefix="/reports", tags=["Reports"])

REPORT_TITLES = {
    "daily_fleet_health": "Daily Fleet Health & Readiness Briefing",
    "weekly_maintenance": "Weekly Maintenance Workload & Hangar Bay Schedule",
    "alert_log": "Operational Alert Log & Prognostic Incident Dossier",
    "spares_risk": "Critical Spares Inventory & Supply Chain Risk Assessment",
}

@router.get("", response_model=List[ReportResponse])
def list_reports(
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    reports = db.query(Report).order_by(desc(Report.created_at)).all()
    return [
        ReportResponse(
            report_id=r.report_id,
            report_type=r.report_type,
            title=r.title,
            format=r.format,
            base_id=r.base_id,
            date_range_start=r.date_range_start.strftime("%Y-%m-%d"),
            date_range_end=r.date_range_end.strftime("%Y-%m-%d"),
            generated_by=r.generated_by,
            created_at=r.created_at,
            file_path=r.file_path,
        )
        for r in reports
    ]

@router.post("", response_model=ReportResponse)
def create_report(
    req: CreateReportRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    valid_types = ("daily_fleet_health", "weekly_maintenance", "alert_log", "spares_risk")
    if req.report_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report_type. Allowed types: {valid_types}"
        )

    valid_formats = ("pdf", "csv")
    if req.format.lower() not in valid_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format '{req.format}'. Allowed: {valid_formats}"
        )

    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    report_id = f"RPT-{now.strftime('%Y%m%d%H%M%S%f')}"
    title = REPORT_TITLES.get(req.report_type, req.report_type.replace("_", " ").title())

    start_d = datetime.strptime(req.date_range_start, "%Y-%m-%d").date() if req.date_range_start else date.today()
    end_d = datetime.strptime(req.date_range_end, "%Y-%m-%d").date() if req.date_range_end else date.today()

    if req.format.lower() == "pdf":
        file_path = generate_pdf_report(
            db=db,
            report_id=report_id,
            report_type=req.report_type,
            title=title,
            base_id=req.base_id,
            user_name=current_user.name,
        )
    else:
        file_path = generate_csv_report(
            db=db,
            report_id=report_id,
            report_type=req.report_type,
        )

    report_record = Report(
        report_id=report_id,
        report_type=req.report_type,
        title=title,
        format=req.format.lower(),
        base_id=req.base_id,
        date_range_start=start_d,
        date_range_end=end_d,
        file_path=file_path,
        generated_by=current_user.name,
        created_at=now_str,
    )
    db.add(report_record)
    db.commit()
    db.refresh(report_record)

    log_audit(
        db,
        current_user.service_id,
        current_user.role,
        "GENERATE_REPORT",
        "REPORT",
        report_id,
        f"Generated {req.format.upper()} report '{title}' ({report_id})",
    )

    return ReportResponse(
        report_id=report_record.report_id,
        report_type=report_record.report_type,
        title=report_record.title,
        format=report_record.format,
        base_id=report_record.base_id,
        date_range_start=report_record.date_range_start.strftime("%Y-%m-%d"),
        date_range_end=report_record.date_range_end.strftime("%Y-%m-%d"),
        generated_by=report_record.generated_by,
        created_at=report_record.created_at,
        file_path=report_record.file_path,
    )

@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    rep = db.query(Report).filter(Report.report_id == report_id).first()
    if not rep or not os.path.exists(rep.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report {report_id} file not found")

    filename = os.path.basename(rep.file_path)
    media_type = "application/pdf" if rep.format == "pdf" else "text/csv"

    return FileResponse(
        path=rep.file_path,
        media_type=media_type,
        filename=filename,
    )
