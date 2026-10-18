from sqlalchemy import Column, String, Integer, Float, Boolean, Date, Text, Index
from backend.app.database import Base

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(String, nullable=True)
    updated_at = Column(String, nullable=False)


class Report(Base):
    __tablename__ = "reports"

    report_id = Column(String, primary_key=True, index=True)
    report_type = Column(String, nullable=False, index=True)  # daily_fleet_health, weekly_maintenance, alert_log, spares_risk
    title = Column(String, nullable=False)
    format = Column(String, nullable=False)  # pdf, csv
    base_id = Column(String, nullable=True)
    date_range_start = Column(Date, nullable=False)
    date_range_end = Column(Date, nullable=False)
    file_path = Column(String, nullable=False)
    generated_by = Column(String, nullable=False)
    created_at = Column(String, nullable=False)


class SimulatorState(Base):
    __tablename__ = "simulator_state"

    id = Column(Integer, primary_key=True, default=1)
    is_running = Column(Boolean, nullable=False, default=False)
    speed = Column(Float, nullable=False, default=1.0)
    current_step = Column(Integer, nullable=False, default=0)
    total_steps = Column(Integer, nullable=False, default=720)
    active_faults = Column(Text, nullable=True, default="{}")
    updated_at = Column(String, nullable=False)
