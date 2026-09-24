from enum import Enum


class AssessmentSection(str, Enum):
    APTITUDE = "APTITUDE"
    ENGLISH = "ENGLISH"
    DSA = "DSA"
    PROFESSIONAL_KNOWLEDGE = "PROFESSIONAL_KNOWLEDGE"


class AssessmentStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"


class QuestionStatus(str, Enum):
    UNSEEN = "unseen"
    VIEWED = "viewed"
    ANSWERED = "answered"
    SKIPPED = "skipped"
    FINALIZED = "finalized"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    
class AssessmentMode(str, Enum):
    FULL = "FULL"
    APTITUDE = "APTITUDE"
    ENGLISH = "ENGLISH"
    DSA = "DSA"