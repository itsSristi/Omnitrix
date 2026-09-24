from datetime import datetime

from pydantic import BaseModel

from app.database.enums import AssessmentStatus
from app.database.enums import AssessmentMode

class AssessmentInstruction(BaseModel):
    section: str
    duration_minutes: int
    number_of_questions: int
    positive_mark: float
    negative_mark: float
    skipped_mark: float = 0.0


class AssessmentInstructionsResponse(BaseModel):
    total_duration_minutes: int
    sections: list[AssessmentInstruction]


class StartAssessmentResponse(BaseModel):
    assessment_id: int
    status: AssessmentStatus
    started_at: datetime

class AssessmentStartRequest(BaseModel):
    assessment_mode: AssessmentMode


class AssessmentStartResponse(BaseModel):
    assessment_id: int
    assessment_mode: AssessmentMode
    status: str