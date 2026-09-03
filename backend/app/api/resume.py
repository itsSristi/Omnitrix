from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.dependencies.auth import get_current_user
from app.models.resume import Resume
from app.models.user import User
from app.services.career_recommendations import CareerRecommendationEngine
from app.services.resume_analyzer import ResumeAnalyzer
from app.services.vector_store import InMemoryVectorStore


router = APIRouter(prefix="/resume", tags=["Resume"])


vector_store = InMemoryVectorStore()
resume_analyzer = ResumeAnalyzer()
career_engine = CareerRecommendationEngine()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def extract_document_text(content: bytes, filename: str, content_type: str | None) -> str:
    suffix = Path(filename).suffix.lower()

    try:
        if suffix == ".pdf" or content_type == "application/pdf":
            from io import BytesIO
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()

        if suffix == ".docx" or content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            from io import BytesIO
            from docx import Document

            document = Document(BytesIO(content))
            return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()

        return content.decode("utf-8", errors="ignore").strip()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to read {suffix or 'document'} file: {exc}",
        ) from exc


@router.post("/upload")
def upload_resume(
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    content = file.file.read()
    text = extract_document_text(content, file.filename, file.content_type)

    if not text.strip():
        raise HTTPException(status_code=400, detail="Resume file is empty")

    parsed = resume_analyzer.analyze(text, user_id=current_user.id)
    embedding_record = vector_store.add_document(
        current_user.id,
        text,
        metadata={"skills": parsed["skills"]},
    )

    resume_record = Resume(
        user_id=current_user.id,
        file_name=file.filename,
        file_type=file.content_type or "text/plain",
        title=f"Resume for {current_user.name}",
        summary=parsed.get("summary"),
        raw_text=text,
        extracted_skills=parsed.get("skills", []),
        embedding=embedding_record["embedding"],
        payload={
            "email": parsed.get("email"),
            "phone": parsed.get("phone"),
            "skills": parsed.get("skills", []),
        },
    )
    db.add(resume_record)
    db.commit()
    db.refresh(resume_record)

    user = db.query(User).filter(User.id == current_user.id).first()
    if user:
        user.education = user.education or "Not provided"
        user.experience = user.experience or parsed.get("summary", "")
        user.career_goal = user.career_goal or parsed.get("summary", "")
        db.commit()

    return {
        "message": "Resume uploaded and analyzed successfully",
        "user_id": current_user.id,
        "resume_id": resume_record.id,
        "summary": parsed,
    }


@router.post("/analyze")
def analyze_resume_text(
    text: str,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty resume text")

    analysis = resume_analyzer.analyze(text, user_id=current_user.id)
    recommendations = career_engine.recommend(analysis["skills"])

    return {
        "message": "Resume analysis complete",
        "user_id": current_user.id,
        "analysis": analysis,
        "career_recommendations": recommendations,
        "skill_gap": {
            "missing_skills": recommendations[0]["missing_skills"] if recommendations else [],
        },
    }


@router.get("/skills")
def get_skills(
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    resume_text = "Python FastAPI SQL PostgreSQL AI analytics"
    analysis = resume_analyzer.analyze(resume_text, user_id=current_user.id)
    return {"skills": analysis["skills"]}


@router.get("/recommendations")
def get_recommendations(
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    resume_text = "Python FastAPI SQL PostgreSQL AI analytics"
    analysis = resume_analyzer.analyze(resume_text, user_id=current_user.id)
    return {"career_recommendations": career_engine.recommend(analysis["skills"]) }
