"""
PDF and CSV Report Generation Service for VAJRA.
Uses ReportLab to build professional defense-grade maintenance and health dossiers,
complete with executive summary tables and matplotlib statistical telemetry charts.
"""

import os
from pathlib import Path
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session

# Ensure matplotlib runs headlessly
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from backend.app.models import (
    EngineHealthStatus,
    Engine,
    Aircraft,
    BaseAgency,
    Alert,
    MaintenanceTask,
    SparesInventory,
    Report,
)

REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "generated_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def generate_pdf_report(
    db: Session,
    report_id: str,
    report_type: str,
    title: str,
    base_id: str = None,
    user_name: str = "Fleet Operations",
) -> str:
    file_path = REPORTS_DIR / f"{report_id}.pdf"
    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#14181C"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#6B7280"),
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1C2127"),
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
    )

    story = []

    # 1. Header
    story.append(Paragraph("MINISTRY OF DEFENCE — VAJRA FLEET COMMAND", subtitle_style))
    story.append(Paragraph(f"VAJRA: {title.upper()}", title_style))
    story.append(Paragraph(f"Report Ref: {report_id}  |  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}  |  Officer: {user_name}", subtitle_style))
    story.append(Spacer(1, 15))

    # 2. Matplotlib Chart
    chart_img_path = REPORTS_DIR / f"{report_id}_chart.png"
    plt.figure(figsize=(7, 2.8), dpi=150)
    plt.tight_layout()

    if report_type == "daily_fleet_health":
        health_data = db.query(EngineHealthStatus).all()
        counts = {"Healthy (70-100)": 0, "Watch (40-69)": 0, "Critical (0-39)": 0}
        for h in health_data:
            if h.status == "Healthy":
                counts["Healthy (70-100)"] += 1
            elif h.status == "Watch":
                counts["Watch (40-69)"] += 1
            else:
                counts["Critical (0-39)"] += 1

        bars = plt.bar(list(counts.keys()), list(counts.values()), color=["#3FA34D", "#D9A21B", "#D64545"], width=0.5)
        plt.title("Fleet Engine Health Distribution", fontsize=11, fontweight="bold", pad=8)
        plt.ylabel("Number of Engines", fontsize=9)
        plt.grid(axis="y", linestyle="--", alpha=0.5)
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, int(yval), ha="center", va="bottom", fontsize=9, fontweight="bold")
    elif report_type == "alert_log":
        alerts = db.query(Alert).all()
        sev_counts = {"High / Critical": sum(1 for a in alerts if a.severity in ("High", "Critical")),
                      "Medium / Warning": sum(1 for a in alerts if a.severity in ("Medium", "Warning")),
                      "Low": sum(1 for a in alerts if a.severity == "Low")}
        plt.bar(list(sev_counts.keys()), list(sev_counts.values()), color=["#D64545", "#D9A21B", "#4C8DB8"], width=0.45)
        plt.title("Active System Alerts by Severity Tier", fontsize=11, fontweight="bold", pad=8)
        plt.ylabel("Alert Count", fontsize=9)
        plt.grid(axis="y", linestyle="--", alpha=0.5)
    elif report_type == "spares_risk":
        spares = db.query(SparesInventory).all()
        low_spares = [s for s in spares if s.qty_in_stock <= s.reorder_level][:8]
        names = [s.part_name for s in low_spares]
        stocks = [s.qty_in_stock for s in low_spares]
        reorders = [s.reorder_level for s in low_spares]
        x = range(len(names))
        plt.bar([i - 0.15 for i in x], stocks, width=0.3, label="In Stock", color="#D64545")
        plt.bar([i + 0.15 for i in x], reorders, width=0.3, label="Reorder Level", color="#4C8DB8")
        plt.xticks(x, [n[:12] for n in names], rotation=15, fontsize=8)
        plt.title("Spares Stock vs Reorder Thresholds (High Risk)", fontsize=11, fontweight="bold", pad=8)
        plt.legend(fontsize=8)
        plt.grid(axis="y", linestyle="--", alpha=0.5)
    else: # weekly_maintenance
        bases = db.query(BaseAgency).all()
        base_names = [b.base_id for b in bases]
        tasks = db.query(MaintenanceTask).all()
        b_counts = [sum(1 for t in tasks if t.base_id == b.base_id) for b in bases]
        plt.bar(base_names, b_counts, color="#4C8DB8", width=0.45)
        plt.title("Maintenance Task Workload by Operational Base", fontsize=11, fontweight="bold", pad=8)
        plt.ylabel("Scheduled & Suggested Tasks", fontsize=9)
        plt.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(str(chart_img_path))
    plt.close()

    story.append(Image(str(chart_img_path), width=500, height=200))
    story.append(Spacer(1, 15))

    # 3. Data Table
    story.append(Paragraph("Executive Operational Data Summary", heading_style))
    story.append(Spacer(1, 6))

    if report_type == "daily_fleet_health":
        engines = db.query(Engine, EngineHealthStatus).join(EngineHealthStatus, Engine.engine_id == EngineHealthStatus.engine_id).order_by(EngineHealthStatus.health_score).limit(12).all()
        table_data = [["Engine ID", "Aircraft", "Health Score", "Status", "RUL (Cycles)", "Failure Risk (7d)"]]
        for eng, h in engines:
            table_data.append([
                eng.engine_id,
                eng.aircraft_id,
                f"{h.health_score:.1f}",
                h.status,
                str(h.predicted_rul_cycles),
                f"{h.failure_risk_7d * 100:.1f}%",
            ])
    elif report_type == "alert_log":
        alerts = db.query(Alert).order_by(Alert.severity).limit(12).all()
        table_data = [["Alert ID", "Timestamp", "Engine", "Severity", "Trigger Description", "Status"]]
        for a in alerts:
            table_data.append([
                a.alert_id,
                a.timestamp[:16],
                a.engine_id,
                a.severity,
                Paragraph(a.trigger[:35], cell_style),
                a.status,
            ])
    elif report_type == "spares_risk":
        spares = db.query(SparesInventory).order_by(SparesInventory.qty_in_stock).limit(12).all()
        table_data = [["Part ID", "Part Name", "Base", "Stock", "Reorder Level", "Lead Time", "Cost (Lakh)"]]
        for s in spares:
            table_data.append([
                s.part_id,
                s.part_name,
                s.base_id,
                str(s.qty_in_stock),
                str(s.reorder_level),
                f"{s.lead_time_days}d",
                f"₹{s.unit_cost_inr_lakh}",
            ])
    else: # weekly_maintenance
        tasks = db.query(MaintenanceTask).limit(12).all()
        table_data = [["Task ID", "Engine", "Base", "Component", "Maintenance Type", "Urgency", "Status"]]
        for t in tasks:
            table_data.append([
                t.task_id,
                t.engine_id,
                t.base_id,
                t.component,
                t.maintenance_type,
                t.urgency,
                t.status,
            ])

    t = Table(table_data, colWidths=None)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1C2127")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#E6E9EC")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)

    # 4. Footer Note
    story.append(Spacer(1, 20))
    story.append(Paragraph("OFFICIAL OPERATIONAL REPORT — AUTOMATICALLY GENERATED VIA VAJRA AI PLATFORM", subtitle_style))

    doc.build(story)

    # Clean up temporary chart image
    if chart_img_path.exists():
        try:
            chart_img_path.unlink()
        except Exception:
            pass

    return str(file_path)

def generate_csv_report(db: Session, report_id: str, report_type: str) -> str:
    file_path = REPORTS_DIR / f"{report_id}.csv"

    if report_type == "daily_fleet_health":
        rows = (
            db.query(Engine.engine_id, Engine.aircraft_id, EngineHealthStatus.health_score, EngineHealthStatus.status, EngineHealthStatus.predicted_rul_cycles, EngineHealthStatus.failure_risk_7d)
            .join(EngineHealthStatus, Engine.engine_id == EngineHealthStatus.engine_id)
            .all()
        )
        df = pd.DataFrame(rows, columns=["engine_id", "aircraft_id", "health_score", "status", "predicted_rul_cycles", "failure_risk_7d"])
    elif report_type == "alert_log":
        rows = db.query(Alert.alert_id, Alert.timestamp, Alert.engine_id, Alert.aircraft_id, Alert.severity, Alert.trigger, Alert.status, Alert.source).all()
        df = pd.DataFrame(rows, columns=["alert_id", "timestamp", "engine_id", "aircraft_id", "severity", "trigger", "status", "source"])
    elif report_type == "spares_risk":
        rows = db.query(SparesInventory.part_id, SparesInventory.part_name, SparesInventory.component, SparesInventory.base_id, SparesInventory.qty_in_stock, SparesInventory.reorder_level, SparesInventory.lead_time_days, SparesInventory.unit_cost_inr_lakh).all()
        df = pd.DataFrame(rows, columns=["part_id", "part_name", "component", "base_id", "qty_in_stock", "reorder_level", "lead_time_days", "unit_cost_inr_lakh"])
    else:
        rows = db.query(MaintenanceTask.task_id, MaintenanceTask.engine_id, MaintenanceTask.aircraft_id, MaintenanceTask.base_id, MaintenanceTask.component, MaintenanceTask.maintenance_type, MaintenanceTask.urgency, MaintenanceTask.status, MaintenanceTask.scheduled_date).all()
        df = pd.DataFrame(rows, columns=["task_id", "engine_id", "aircraft_id", "base_id", "component", "maintenance_type", "urgency", "status", "scheduled_date"])

    df.to_csv(file_path, index=False)
    return str(file_path)
