from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from pgvector.sqlalchemy import Vector

from app.database.database import Base


class ResumeVector(Base):
    __tablename__ = "resume_vectors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    text_content = Column(Text, nullable=False)
    payload = Column("metadata", JSON, nullable=True, default=dict)
    embedding = Column(Vector(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
