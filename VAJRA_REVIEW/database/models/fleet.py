from sqlalchemy import Column, String, Integer, Date, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base

class BaseAgency(Base):
    __tablename__ = "bases"

    base_id = Column(String, primary_key=True, index=True)
    base_name = Column(String, nullable=False)
    state = Column(String, nullable=False)
    daily_maintenance_slots = Column(Integer, nullable=False, default=2)
    hangar_bays = Column(Integer, nullable=False, default=2)

    # Relationships
    aircraft = relationship("Aircraft", back_populates="base")
    spares = relationship("SparesInventory", back_populates="base")
    maintenance_records = relationship("MaintenanceHistory", back_populates="base")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="base")


class Aircraft(Base):
    __tablename__ = "aircraft"

    aircraft_id = Column(String, primary_key=True, index=True)
    aircraft_type = Column(String, nullable=False, index=True)  # Transport-A, Fighter-B, Trainer-C, Heli-D
    engine_config = Column(String, nullable=False)
    num_engines = Column(Integer, nullable=False)
    base_id = Column(String, ForeignKey("bases.base_id"), nullable=False, index=True)
    commission_year = Column(Integer, nullable=False)
    total_flight_hours = Column(Integer, nullable=False)
    mission_role = Column(String, nullable=False)
    last_inspection_date = Column(Date, nullable=False)

    # Relationships
    base = relationship("BaseAgency", back_populates="aircraft")
    engines = relationship("Engine", back_populates="aircraft")
    maintenance_records = relationship("MaintenanceHistory", back_populates="aircraft")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="aircraft")
    alerts = relationship("Alert", back_populates="aircraft")


class Engine(Base):
    __tablename__ = "engines"

    engine_id = Column(String, primary_key=True, index=True)
    aircraft_id = Column(String, ForeignKey("aircraft.aircraft_id"), nullable=False, index=True)
    position = Column(Integer, nullable=False)
    engine_model = Column(String, nullable=False)
    install_date = Column(Date, nullable=False)
    cycles_since_new = Column(Integer, nullable=False)
    hours_since_overhaul = Column(Integer, nullable=False)

    # Relationships
    aircraft = relationship("Aircraft", back_populates="engines")
    health_status = relationship("EngineHealthStatus", back_populates="engine", uselist=False)
    components = relationship("ComponentHealth", back_populates="engine")
    maintenance_records = relationship("MaintenanceHistory", back_populates="engine")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="engine")
    alerts = relationship("Alert", back_populates="engine")

__table_args__ = (
    Index("ix_engines_aircraft_pos", Engine.aircraft_id, Engine.position),
)
