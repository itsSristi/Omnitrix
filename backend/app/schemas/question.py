from typing import Optional
from pydantic import BaseModel, ConfigDict


class QuestionBase(BaseModel):
    section: Optional[str] = "TECHNICAL"
    question_text: str
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_option: Optional[str] = None
    difficulty: Optional[str] = "MEDIUM"
    expected_time_seconds: Optional[int] = 60
    positive_mark: Optional[float] = 1.0
    negative_mark: Optional[float] = 0.0
    is_active: Optional[bool] = True


class QuestionCreate(QuestionBase):
    pass


class QuestionResponse(QuestionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class QuestionCandidateView(BaseModel):
    id: int
    section: Optional[str] = None
    question_text: str
    difficulty: Optional[str] = None
    expected_time_seconds: Optional[int] = 60

    model_config = ConfigDict(from_attributes=True)
