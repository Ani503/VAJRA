from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base

class MaintenanceHistory(Base):
    __tablename__ = "maintenance_history"

    record_id = Column(String, primary_key=True, index=True)
    engine_id = Column(String, ForeignKey("engines.engine_id"), nullable=False, index=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    maintenance_type = Column(String, nullable=False)
    category = Column(String, nullable=False)  # Routine, Unscheduled, Scheduled
    downtime_hours = Column(Integer, nullable=False)
    technician_id = Column(String, nullable=False)
    base_id = Column(String, ForeignKey("bases.base_id"), nullable=False, index=True)
    fault_found = Column(String, nullable=True)
    cost_inr_lakh = Column(Float, nullable=False)

    # Relationships
    base = relationship("BaseAgency", back_populates="maintenance_records")
    aircraft = relationship("Aircraft", back_populates="maintenance_records")
    engine = relationship("Engine", back_populates="maintenance_records")


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"

    task_id = Column(String, primary_key=True, index=True)
    engine_id = Column(String, ForeignKey("engines.engine_id"), nullable=False, index=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"), nullable=False, index=True)
    base_id = Column(String, ForeignKey("bases.base_id"), nullable=False, index=True)
    component = Column(String, nullable=False)
    required_part_id = Column(String, nullable=True)
    maintenance_type = Column(String, nullable=False)
    urgency = Column(String, nullable=False, index=True)  # Immediate, Within 7 Days, Within 14 Days, Routine
    status = Column(String, nullable=False, index=True)  # Suggested, Scheduled, In Progress, Completed
    scheduled_date = Column(Date, nullable=True)
    estimated_downtime_hours = Column(Integer, nullable=False, default=12)
    created_at = Column(String, nullable=False)

    # Relationships
    base = relationship("BaseAgency", back_populates="maintenance_tasks")
    aircraft = relationship("Aircraft", back_populates="maintenance_tasks")
    engine = relationship("Engine", back_populates="maintenance_tasks")


class WorkOrder(Base):
    __tablename__ = "work_orders"

    work_order_id = Column(String, primary_key=True, index=True)
    alert_id = Column(String, ForeignKey("alerts.alert_id"), nullable=True)
    engine_id = Column(String, ForeignKey("engines.engine_id"), nullable=False, index=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"), nullable=False, index=True)
    base_id = Column(String, ForeignKey("bases.base_id"), nullable=False, index=True)
    status = Column(String, nullable=False, index=True)  # Draft, Pending Approval, Approved, In Progress, Completed, Cancelled
    priority = Column(String, nullable=False)  # Critical, High, Medium, Low
    task_description = Column(Text, nullable=False)
    assigned_technician = Column(String, nullable=True)
    estimated_downtime_hours = Column(Integer, nullable=False, default=8)
    created_at = Column(String, nullable=False)
    approved_at = Column(String, nullable=True)
    approved_by = Column(String, nullable=True)
