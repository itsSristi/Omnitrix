import logging
import os
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.resume_ai import ResumeAI
from app.database.database import SessionLocal
from app.dependencies.auth import get_current_user
from app.models.resume import Resume
from app.models.resume_section import ResumeSection
from app.models.user import User
from app.schemas.resume import GeneratedResume, ResumeAnalysis, ResumeGenerateRequest
from app.services.career_recommendations import CareerRecommendationEngine
from app.services.resume_analyzer import ResumeAnalyzer
from app.services.resume_pdf import build_resume_pdf
from app.services.skill_normalizer import SkillNormalizer
from app.services.vector_store import InMemoryVectorStore


router = APIRouter(prefix="/resume", tags=["Resume"])
logger = logging.getLogger(__name__)


vector_store = InMemoryVectorStore()
resume_analyzer = ResumeAnalyzer()
career_engine = CareerRecommendationEngine()
resume_ai = ResumeAI()
skill_normalizer = SkillNormalizer()
MAX_RESUME_BYTES = int(os.getenv("MAX_RESUME_BYTES", str(10 * 1024 * 1024)))
RESUME_UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "resumes"


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
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF resumes are allowed")

    content = file.file.read(MAX_RESUME_BYTES + 1)
    if len(content) > MAX_RESUME_BYTES:
        raise HTTPException(status_code=413, detail="Resume exceeds the maximum file size")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF")

    RESUME_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid4().hex}.pdf"
    stored_path = RESUME_UPLOAD_DIR / stored_filename
    stored_path.write_bytes(content)

    resume_record = Resume(
        user_id=current_user.id,
        file_name=file.filename,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_path=str(stored_path),
        file_type="application/pdf",
        title=f"Resume for {current_user.name}",
        processing_status="processing",
    )
    db.add(resume_record)
    db.commit()
    db.refresh(resume_record)

    try:
        text = extract_document_text(content, file.filename, "application/pdf")
        if len(text.strip()) < 40:
            raise ValueError("The PDF does not contain enough extractable resume text")

        deterministic = resume_analyzer.analyze(text, user_id=None)
        ai_evaluation = resume_ai.evaluate(text, deterministic)
        if ai_evaluation.get("status") != "complete":
            raise RuntimeError(ai_evaluation.get("message", "AI analysis is unavailable"))

        validated = ResumeAnalysis.model_validate(ai_evaluation)
        analysis = skill_normalizer.validate(validated.model_dump(), text)
        sections = vector_store._split_sections(text)
        embedding_record = vector_store.add_document(
            current_user.id,
            text,
            metadata={"resume_id": resume_record.id, "skills": analysis["skills"]},
            section_name="full_resume",
            resume_id=resume_record.id,
        )

        for section_type, section_text in sections:
            db.add(ResumeSection(
                resume_id=resume_record.id,
                section_type=section_type,
                section_text=section_text,
            ))
        persisted_skills = skill_normalizer.persist(db, resume_record.id, analysis)
        skill_vectors = 0
        for item in persisted_skills:
            skill_vector = vector_store.add_document(
                current_user.id,
                item["name"],
                metadata={
                    "resume_id": resume_record.id,
                    "type": "skill",
                    "skill_id": item["id"],
                    "canonical_skill": item["name"],
                },
                section_name=f"skill:{item['name']}",
                resume_id=resume_record.id,
            )
            skill_vectors += len(skill_vector["sections"])
        full_embedding = next(
            (item["embedding"] for item in embedding_record["sections"] if item["section_name"] == "full_resume"),
            None,
        )
        resume_record.raw_text = text
        resume_record.summary = text[:500]
        resume_record.extracted_skills = [item["name"] for item in analysis["skills"]]
        resume_record.embedding = full_embedding
        resume_record.payload = {"analysis": analysis, "skills": persisted_skills}
        resume_record.processing_status = "completed"
        db.commit()
        logger.info("Resume processing completed resume_id=%s user_id=%s", resume_record.id, current_user.id)
    except (ValidationError, ValueError, RuntimeError, OSError) as exc:
        db.rollback()
        failed = db.query(Resume).filter(Resume.id == resume_record.id).first()
        if failed:
            failed.processing_status = "failed"
            failed.payload = {"error": str(exc)}
            db.commit()
        raise HTTPException(status_code=422, detail=f"Resume processing failed: {exc}") from exc

    return {
        "message": "Resume uploaded and analyzed successfully",
        "user_id": current_user.id,
        "resume_id": resume_record.id,
        "filename": resume_record.original_filename,
        "processing_status": resume_record.processing_status,
        "sections_detected": len(sections),
        "skills_extracted": len(persisted_skills),
        "vectors_created": len(embedding_record["sections"]) + skill_vectors,
        "analysis": analysis,
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
    ai_evaluation = resume_ai.evaluate(text, analysis)

    return {
        "message": "Resume analysis complete",
        "user_id": current_user.id,
        "analysis": analysis,
        "career_recommendations": recommendations,
        "skill_gap": {
            "missing_skills": recommendations[0]["missing_skills"] if recommendations else [],
        },
        **({"ai_evaluation": ai_evaluation} if ai_evaluation.get("status") == "complete" else {}),
    }


@router.post("/generate", response_model=GeneratedResume)
def generate_resume(
    request: ResumeGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    existing_resume = db.query(Resume.id).filter(Resume.user_id == current_user.id).first()
    if existing_resume is not None:
        raise HTTPException(
            status_code=409,
            detail="A resume already exists for this user. Use /resume/upload or /resume/analyze.",
        )

    generated = resume_ai.generate_resume(request.name, request.choice)
    if generated.get("status") != "complete":
        raise HTTPException(
            status_code=503,
            detail=generated.get("message", "CV generation is unavailable"),
        )

    try:
        validated = GeneratedResume.model_validate(generated)
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail="AI returned an invalid CV structure") from exc

    return validated


@router.post("/generate/pdf")
def generate_resume_pdf(
    request: ResumeGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    existing_resume = db.query(Resume.id).filter(Resume.user_id == current_user.id).first()
    if existing_resume is not None:
        raise HTTPException(
            status_code=409,
            detail="A resume already exists for this user. Use /resume/upload or /resume/analyze.",
        )

    generated = resume_ai.generate_resume(request.name, request.choice)
    if generated.get("status") != "complete":
        raise HTTPException(
            status_code=503,
            detail=generated.get("message", "CV generation is unavailable"),
        )
    try:
        validated = GeneratedResume.model_validate(generated)
        pdf_bytes = build_resume_pdf(validated)
    except (ValidationError, ValueError, OSError) as exc:
        raise HTTPException(status_code=502, detail="Unable to create the resume PDF") from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="generated_resume.pdf"'},
    )
