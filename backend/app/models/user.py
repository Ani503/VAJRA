from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Index
from backend.app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, index=True)  # Fleet Commander, Maintenance Officer, Analyst
    password_hash = Column(String, nullable=False)
    base_id = Column(String, ForeignKey("bases.base_id"), nullable=True)
    created_at = Column(String, nullable=False)
    is_active = Column(Integer, default=1, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    user_role = Column(String, nullable=False)
    action = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    prev_hash = Column(String(64), nullable=True)
    entry_hash = Column(String(64), nullable=True)
