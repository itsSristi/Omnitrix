from sqlalchemy import (
    Column,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base

from app.database.enums import (
    AssessmentStatus,
    AssessmentMode,
)


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # ========================================================
    # ASSESSMENT MODE
    # ========================================================
    #
    # Determines what the student wants to attempt:
    #
    # full      -> Aptitude + English + DSA
    # aptitude  -> Aptitude only
    # english   -> English only
    # dsa       -> DSA only
    #
    assessment_mode = Column(
        SQLEnum(AssessmentMode),
        nullable=False,
        default=AssessmentMode.FULL,
    )

    status = Column(
        SQLEnum(AssessmentStatus),
        default=AssessmentStatus.NOT_STARTED,
        nullable=False,
    )

    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    total_score = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    maximum_score = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    percentage = Column(
        Float,
        default=0.0,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ========================================================
    # RELATIONSHIPS
    # ========================================================

    sections = relationship(
        "AssessmentSectionResult",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )

    answers = relationship(
        "AssessmentAnswer",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )