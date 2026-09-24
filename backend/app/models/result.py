from sqlalchemy import (
    Column,
    Integer,
    Float,
    DateTime,
    ForeignKey
)

from sqlalchemy.sql import func

from app.database.database import Base


class AssessmentResult(Base):

    __tablename__ = "assessment_results"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    assessment_id = Column(
        Integer,
        ForeignKey("assessments.id"),
        nullable=False,
        unique=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    total_score = Column(
        Float,
        default=0.0,
        nullable=False
    )

    maximum_score = Column(
        Float,
        default=0.0,
        nullable=False
    )

    percentage = Column(
        Float,
        default=0.0,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )