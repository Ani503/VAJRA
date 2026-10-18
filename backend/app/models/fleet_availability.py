from sqlalchemy import Column, String, Integer, Float, Date, ForeignKey, Index
from backend.app.database import Base

class FleetAvailabilityHistory(Base):
    __tablename__ = "fleet_availability_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    base_id = Column(String, ForeignKey("bases.base_id"), nullable=False, index=True)
    total_aircraft = Column(Integer, nullable=False)
    mission_ready = Column(Integer, nullable=False)
    under_scheduled_maintenance = Column(Integer, nullable=False)
    under_unscheduled_maintenance = Column(Integer, nullable=False)
    availability_pct = Column(Float, nullable=False)

    __table_args__ = (
        Index("ix_fleet_avail_date_base", "date", "base_id"),
    )


class MissionDemand(Base):
    __tablename__ = "mission_demand"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    base_id = Column(String, ForeignKey("bases.base_id"), nullable=False, index=True)
    aircraft_required = Column(Integer, nullable=False)

    __table_args__ = (
        Index("ix_mission_demand_date_base", "date", "base_id"),
    )
