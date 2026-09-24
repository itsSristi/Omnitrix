from sqlalchemy import (
    Column,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Enum as SQLEnum
)

from sqlalchemy.orm import relationship

from app.database.database import Base

from app.database.enums import (
    QuestionStatus
)


class AssessmentAnswer(Base):

    __tablename__ = "assessment_answers"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    assessment_id = Column(
        Integer,
        ForeignKey("assessments.id"),
        nullable=False
    )

    question_id = Column(
        Integer,
        ForeignKey("questions.id"),
        nullable=False
    )

    section_id = Column(
        Integer,
        ForeignKey(
            "assessment_section_results.id"
        ),
        nullable=False
    )

    selected_option = Column(
        String(1),
        nullable=True
    )

    status = Column(
        SQLEnum(QuestionStatus),
        default=QuestionStatus.UNSEEN,
        nullable=False
    )

    visited_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    answered_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    time_spent_seconds = Column(
        Integer,
        default=0,
        nullable=False
    )

    is_correct = Column(
        Boolean,
        nullable=True
    )

    marks_awarded = Column(
        Float,
        default=0.0,
        nullable=False
    )

    assessment = relationship(
        "Assessment",
        back_populates="answers"
    )