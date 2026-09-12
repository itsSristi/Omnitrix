from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from pgvector.sqlalchemy import Vector

from app.database.database import Base


class ResumeVector(Base):
    __tablename__ = "resume_vectors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True, index=True)
    section_name = Column(String(100), nullable=False, default="resume")
    text_content = Column(Text, nullable=False)
    payload = Column("metadata", JSON, nullable=True, default=dict)
    embedding = Column(Vector(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
