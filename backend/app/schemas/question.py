from datetime import datetime

from pydantic import BaseModel

from app.database.enums import (
    AssessmentSection,
    QuestionStatus,
)


# ============================================================
# ASSESSMENT QUESTION RESPONSE
# ============================================================

class AssessmentQuestionResponse(BaseModel):
    id: int
    section: AssessmentSection
    question_text: str

    option_a: str
    option_b: str
    option_c: str
    option_d: str

    # Question configuration
    difficulty: str
    expected_time_seconds: int
    positive_mark: float
    negative_mark: float

    # User answer state
    selected_option: str | None
    status: QuestionStatus
    visited_at: datetime | None
    answered_at: datetime | None
    time_spent_seconds: int


# ============================================================
# SECTION QUESTIONS RESPONSE
# ============================================================

class SectionQuestionsResponse(BaseModel):
    assessment_id: int
    section: AssessmentSection
    deadline: datetime | None
    questions: list[AssessmentQuestionResponse]