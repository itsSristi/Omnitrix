from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.dependencies.auth import get_current_user
from app.models.resume import Resume
from app.models.user import User
from app.services.career_recommendations import CareerRecommendationEngine


router = APIRouter(prefix="/jobs", tags=["Jobs"])
career_engine = CareerRecommendationEngine()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/recommendations")
def recommend_jobs_from_resume(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    limit: int = 4,
):
    latest_resume = (
        db.query(Resume)
        .filter(
            Resume.user_id == current_user.id,
            Resume.processing_status == "completed",
        )
        .order_by(Resume.created_at.desc())
        .first()
    )
    if latest_resume is None:
        raise HTTPException(
            status_code=404,
            detail="Upload and analyze a resume before requesting job recommendations",
        )

    analysis = (latest_resume.payload or {}).get("analysis", {})
    candidate_skills = analysis.get("skills") or latest_resume.extracted_skills or []
    candidate_skills = [
        item.get("name") if isinstance(item, dict) else item
        for item in candidate_skills
    ]
    candidate_skills = [skill for skill in candidate_skills if skill]

    recommendations = career_engine.recommend(candidate_skills)
    return {
        "user_id": current_user.id,
        "resume_id": latest_resume.id,
        "profile": {
            "name": current_user.name,
            "skills": candidate_skills,
            "resume_summary": latest_resume.summary,
        },
        "recommendations": recommendations[: max(1, min(limit, 10))],
    }
