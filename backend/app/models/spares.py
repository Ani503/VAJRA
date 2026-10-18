from sqlalchemy import Column, String, Integer, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.app.database import Base

class SparesInventory(Base):
    __tablename__ = "spares_inventory"

    part_id = Column(String, primary_key=True)
    base_id = Column(String, ForeignKey("bases.base_id"), primary_key=True, index=True)
    part_name = Column(String, nullable=False, index=True)
    component = Column(String, nullable=False, index=True)
    qty_in_stock = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, nullable=False, default=2)
    lead_time_days = Column(Integer, nullable=False, default=30)
    unit_cost_inr_lakh = Column(Float, nullable=False)
    supplier = Column(String, nullable=False)

    # Relationships
    base = relationship("BaseAgency", back_populates="spares")


class SpareOrder(Base):
    __tablename__ = "spare_orders"

    order_id = Column(String, primary_key=True, index=True)
    part_id = Column(String, nullable=False, index=True)
    base_id = Column(String, ForeignKey("bases.base_id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    status = Column(String, nullable=False, index=True)  # Placed, In Transit, Received, Cancelled
    order_date = Column(String, nullable=False)
    expected_delivery = Column(String, nullable=False)
    supplier = Column(String, nullable=False)
    total_cost_inr_lakh = Column(Float, nullable=False)
