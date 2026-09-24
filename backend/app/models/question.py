from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    Enum as SQLEnum,
)

from app.database.database import Base
from app.database.enums import AssessmentSection, DifficultyLevel


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)

    section = Column(
        SQLEnum(AssessmentSection),
        nullable=False,
        index=True,
    )

    question_text = Column(
        Text,
        nullable=False,
    )

    option_a = Column(
        String(500),
        nullable=False,
    )

    option_b = Column(
        String(500),
        nullable=False,
    )

    option_c = Column(
        String(500),
        nullable=False,
    )

    option_d = Column(
        String(500),
        nullable=False,
    )

    correct_option = Column(
        String(1),
        nullable=False,
    )

    difficulty = Column(
        SQLEnum(DifficultyLevel),
        default=DifficultyLevel.MEDIUM,
        nullable=False,
    )

    expected_time_seconds = Column(
        Integer,
        default=60,
        nullable=False,
    )

    positive_mark = Column(
        Float,
        default=1.0,
        nullable=False,
    )

    negative_mark = Column(
        Float,
        default=0.25,
        nullable=False,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )
