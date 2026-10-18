from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base

class EngineHealthStatus(Base):
    __tablename__ = "engine_health_status"

    engine_id = Column(String, ForeignKey("engines.engine_id"), primary_key=True, index=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"), nullable=False, index=True)
    health_score = Column(Float, nullable=False)
    status = Column(String, nullable=False, index=True)  # Healthy, Watch, Critical
    predicted_rul_cycles = Column(Integer, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    failure_risk_7d = Column(Float, nullable=False)
    last_updated = Column(String, nullable=False)

    # Relationships
    engine = relationship("Engine", back_populates="health_status")


class ComponentHealth(Base):
    __tablename__ = "component_health"

    id = Column(Integer, primary_key=True, autoincrement=True)
    engine_id = Column(String, ForeignKey("engines.engine_id"), nullable=False, index=True)
    component = Column(String, nullable=False)  # Fan, Compressor, Combustion Chamber, Turbine, Shaft
    health_score = Column(Float, nullable=False)
    colour = Column(String, nullable=False)  # Green, Yellow, Red
    shap_contribution = Column(Float, nullable=False)

    # Relationships
    engine = relationship("Engine", back_populates="components")

    __table_args__ = (
        Index("ix_comp_engine_comp", "engine_id", "component"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(String, primary_key=True, index=True)
    timestamp = Column(String, nullable=False, index=True)
    engine_id = Column(String, ForeignKey("engines.engine_id"), nullable=False, index=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"), nullable=False, index=True)
    severity = Column(String, nullable=False, index=True)  # High, Medium, Low
    trigger = Column(String, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    rul_cycles = Column(Integer, nullable=False)
    status = Column(String, nullable=False, index=True)  # Unacknowledged, Acknowledged, In Progress, Resolved
    source = Column(String, nullable=False, default="ml")  # ml, rule_engine
    assigned_to = Column(String, nullable=True)
    work_order_id = Column(String, nullable=True)

    # Relationships
    engine = relationship("Engine", back_populates="alerts")
    aircraft = relationship("Aircraft", back_populates="alerts")


class RuleEngineThreshold(Base):
    __tablename__ = "rule_engine_thresholds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parameter = Column(String, nullable=False, index=True)
    operator = Column(String, nullable=False)
    threshold = Column(Float, nullable=False)
    severity = Column(String, nullable=False)  # Critical, Warning
    recommended_action = Column(String, nullable=False)
