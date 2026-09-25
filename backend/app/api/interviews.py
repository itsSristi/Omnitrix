from datetime import datetime
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.ai.interview_ai import InterviewAI
from app.database.database import SessionLocal
from app.database.enums import AssessmentSection, DifficultyLevel
from app.dependencies.auth import get_current_user
from app.models.answer import Answer
from app.models.interview import Interview
from app.models.job import Job
from app.models.question import Question
from app.models.result import InterviewResult
from app.models.user import User
from app.schemas.interview import (
    AnswerSubmitRequest,
    AnswerSubmitResponse,
    FollowupQuestionRequest,
    InterviewCompleteResponse,
    InterviewDetailResponse,
    InterviewHistoryItem,
    InterviewStartRequest,
    InterviewStartResponse,
    TTSAudioRequest,
)
from app.schemas.question import QuestionCandidateView

router = APIRouter(prefix="/interviews", tags=["Interviews"])
interview_ai = InterviewAI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/start", response_model=InterviewStartResponse)
def start_interview(
    request: InterviewStartRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """1 & 2. Prepare candidate profile, retrieve/generate deduplicated questions, and initialize interview session."""
    valid_job_id = request.job_id if (request.job_id and request.job_id > 0) else None
    if valid_job_id:
        if not db.query(Job).filter(Job.id == valid_job_id).first():
            valid_job_id = None

    interview = Interview(
        user_id=current_user.id,
        job_id=valid_job_id,
        interview_type=request.interview_type or "TECHNICAL",
        status="IN_PROGRESS",
        scheduled_at=datetime.utcnow(),
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    # 1. Candidate profile preparation & 2. Question preparation with deduplication
    session_data = interview_ai.prepare_session(
        db=db,
        user_id=current_user.id,
        role=request.role or "Software Engineer",
        difficulty=request.difficulty or "MEDIUM",
        interview_type=request.interview_type or "TECHNICAL",
        topics=request.topics,
        resume_id=request.resume_id,
        target_company=request.target_company,
        num_questions=request.num_questions or 5,
    )

    questions = session_data["questions"]

    return InterviewStartResponse(
        interview_id=interview.id,
        interview_type=interview.interview_type,
        status=interview.status,
        target_role=request.role,
        target_company=request.target_company,
        current_difficulty=request.difficulty or "MEDIUM",
        questions=[QuestionCandidateView.model_validate(q) for q in questions],
        created_at=interview.created_at,
    )


@router.post("/tts")
def text_to_speech_post(body: TTSAudioRequest):
    """3. Convert interviewer question text into natural audio stream (TTS) via POST."""
    audio_bytes, mime_type = interview_ai.synthesize_speech_with_mime(body.text)
    ext = "mp3" if "mpeg" in mime_type else "wav"
    return Response(
        content=audio_bytes,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="question_audio.{ext}"',
            "Content-Type": mime_type,
            "Content-Length": str(len(audio_bytes)),
            "Accept-Ranges": "bytes",
        },
    )


@router.get("/tts")
def text_to_speech_get(text: str = "Please introduce yourself and explain your background."):
    """3. Convert interviewer question text into natural audio stream (TTS) via GET for HTML5 audio."""
    audio_bytes, mime_type = interview_ai.synthesize_speech_with_mime(text)
    ext = "mp3" if "mpeg" in mime_type else "wav"
    return Response(
        content=audio_bytes,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="question_audio.{ext}"',
            "Content-Type": mime_type,
            "Content-Length": str(len(audio_bytes)),
            "Accept-Ranges": "bytes",
        },
    )


@router.get("/{interview_id}/questions/{question_id}/audio")
def get_question_audio(
    interview_id: int,
    question_id: int,
    db: Session = Depends(get_db),
):
    """3. Stream synthesized spoken audio (TTS) for a specific interview question."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    audio_bytes, mime_type = interview_ai.synthesize_speech_with_mime(q.question_text)
    ext = "mp3" if "mpeg" in mime_type else "wav"
    return Response(
        content=audio_bytes,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="question_{question_id}.{ext}"',
            "Content-Type": mime_type,
            "Content-Length": str(len(audio_bytes)),
            "Accept-Ranges": "bytes",
        },
    )


@router.get("/questions/{question_id}/audio")
def get_direct_question_audio(
    question_id: int,
    db: Session = Depends(get_db),
):
    """3. Stream synthesized spoken audio (TTS) directly for a question by ID."""
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    audio_bytes, mime_type = interview_ai.synthesize_speech_with_mime(q.question_text)
    ext = "mp3" if "mpeg" in mime_type else "wav"
    return Response(
        content=audio_bytes,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="question_{question_id}.{ext}"',
            "Content-Type": mime_type,
            "Content-Length": str(len(audio_bytes)),
            "Accept-Ranges": "bytes",
        },
    )



@router.post("/{interview_id}/answer", response_model=AnswerSubmitResponse)
def submit_interview_answer(
    interview_id: int,
    request: AnswerSubmitRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """4 & 6. Submit typed answer, evaluate with 6 rubrics, adapt difficulty, and optionally generate a follow-up question."""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id,
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview session not found")

    question_text = request.question_text
    expected_section = "PROFESSIONAL_KNOWLEDGE"
    curr_diff = DifficultyLevel.MEDIUM

    if request.question_id:
        q = db.query(Question).filter(Question.id == request.question_id).first()
        if q:
            question_text = q.question_text
            expected_section = q.section.value if hasattr(q.section, "value") else str(q.section)
            curr_diff = q.difficulty or DifficultyLevel.MEDIUM

    if not question_text:
        question_text = "General Technical Question"

    # 6. Answer evaluation
    eval_result = interview_ai.evaluate_response(
        question_text=question_text,
        answer_text=request.answer_text or "",
        expected_section=expected_section,
    )

    # 7. Adaptive questioning: adjust difficulty based on performance
    new_difficulty = interview_ai.adapt_difficulty(curr_diff, eval_result["score"])

    # 8. Follow-up questioning if requested or relevant
    followup_q = None
    if request.generate_followup and request.answer_text:
        followup_q = interview_ai.generate_followup(
            db=db,
            previous_question=question_text,
            candidate_answer=request.answer_text,
            difficulty=new_difficulty,
        )

    # Persist answer record
    answer = Answer(
        question_id=request.question_id,
        user_id=current_user.id,
        answer_text=request.answer_text,
        audio_path=request.audio_path,
        score=eval_result["score"],
        feedback=eval_result["feedback"],
        keywords_detected=eval_result["keywords_detected"],
        time_taken_seconds=request.time_taken_seconds or 0,
        created_at=datetime.utcnow(),
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)

    return AnswerSubmitResponse(
        answer_id=answer.id,
        question_id=answer.question_id,
        score=answer.score,
        correctness=eval_result.get("correctness"),
        technical_accuracy=eval_result.get("technical_accuracy"),
        reasoning_depth=eval_result.get("reasoning_depth"),
        relevance=eval_result.get("relevance"),
        completeness=eval_result.get("completeness"),
        communication_clarity=eval_result.get("communication_clarity"),
        feedback=answer.feedback,
        keywords_detected=answer.keywords_detected or [],
        time_taken_seconds=answer.time_taken_seconds,
        adapted_difficulty=new_difficulty.value if hasattr(new_difficulty, "value") else str(new_difficulty),
        followup_question=QuestionCandidateView.model_validate(followup_q) if followup_q else None,
    )


@router.post("/{interview_id}/answer-audio", response_model=AnswerSubmitResponse)
async def submit_interview_audio_answer(
    interview_id: int,
    file: UploadFile = File(...),
    question_id: Optional[int] = Form(None),
    question_text: Optional[str] = Form(None),
    time_taken_seconds: Optional[int] = Form(60),
    generate_followup: Optional[bool] = Form(False),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """4 & 5. Receive microphone audio, transcribe to text with Speech-to-Text (STT), evaluate answer, adapt difficulty."""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id,
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview session not found")

    audio_bytes = await file.read()
    # 5. Speech-to-Text conversion
    transcript = interview_ai.transcribe_audio(audio_bytes, filename=file.filename or "audio.wav")
    if not transcript.strip():
        transcript = "Audio response provided (microphone input recorded)."

    submit_req = AnswerSubmitRequest(
        question_id=question_id,
        question_text=question_text,
        answer_text=transcript,
        time_taken_seconds=time_taken_seconds,
        audio_path=file.filename,
        generate_followup=generate_followup,
    )
    return submit_interview_answer(
        interview_id=interview_id,
        request=submit_req,
        current_user=current_user,
        db=db,
    )


@router.post("/{interview_id}/followup", response_model=QuestionCandidateView)
def request_followup_question(
    interview_id: int,
    body: FollowupQuestionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """8. Explicitly generate a probing follow-up question based on the candidate's actual answer."""
    diff_enum = DifficultyLevel.MEDIUM
    if body.difficulty:
        from app.services.question_generator import map_difficulty
        diff_enum = map_difficulty(body.difficulty)

    followup = interview_ai.generate_followup(
        db=db,
        previous_question=body.question_text,
        candidate_answer=body.candidate_answer,
        role=body.role or "Software Engineer",
        difficulty=diff_enum,
    )
    return QuestionCandidateView.model_validate(followup)


@router.post("/{interview_id}/complete", response_model=InterviewCompleteResponse)
def complete_interview(
    interview_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """10. Final evaluation: Generates the final report using the entire interview history with Qwen LLM."""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id,
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview session not found")

    report = interview_ai.complete_session(db=db, interview_id=interview_id)

    return InterviewCompleteResponse(
        interview_id=interview.id,
        status=interview.status,
        overall_score=report["overall_score"],
        technical_score=report["technical_score"],
        problem_solving_score=report.get("problem_solving_score", report.get("confidence_score", 75.0)),
        communication_score=report["communication_score"],
        confidence_score=report.get("confidence_score", 75.0),
        summary=report["summary"],
        overall_performance=report.get("overall_performance"),
        technical_knowledge=report.get("technical_knowledge"),
        problem_solving=report.get("problem_solving"),
        communication=report.get("communication"),
        strong_areas=report.get("strong_areas", []),
        weak_areas=report.get("weak_areas", []),
        topics_needing_improvement=report.get("topics_needing_improvement", []),
        question_wise_performance=report.get("question_wise_performance", []),
        recommended_preparation_topics=report.get("recommended_preparation_topics", []),
        strengths=report.get("strengths", []),
        improvements=report.get("improvements", []),
        completed_at=interview.completed_at or datetime.utcnow(),
    )


@router.get("/history", response_model=List[InterviewHistoryItem])
def list_interview_history(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """List all interviews completed or scheduled by the user."""
    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .order_by(Interview.created_at.desc())
        .all()
    )
    return [InterviewHistoryItem.model_validate(i) for i in interviews]


@router.get("/{interview_id}", response_model=InterviewDetailResponse)
def get_interview_detail(
    interview_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Get full details, results, final evaluation breakdown, and answers for a specific interview session."""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id,
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview session not found")

    result = db.query(InterviewResult).filter(InterviewResult.interview_id == interview.id).first()
    answers = db.query(Answer).filter(Answer.user_id == current_user.id).order_by(Answer.created_at.asc()).all()

    # Extract parsed fields from result strengths/improvements JSON if available
    strong_areas = []
    weak_areas = []
    topics_imp = []
    prep_topics = []
    q_performance = []
    tech_knowledge = None
    problem_solving = None
    comm_text = None

    if result:
        if isinstance(result.strengths, dict):
            strong_areas = result.strengths.get("strong_areas", [])
            tech_knowledge = result.strengths.get("technical_knowledge")
            problem_solving = result.strengths.get("problem_solving")
            comm_text = result.strengths.get("communication")
        elif isinstance(result.strengths, list):
            strong_areas = result.strengths

        if isinstance(result.improvements, dict):
            weak_areas = result.improvements.get("weak_areas", [])
            topics_imp = result.improvements.get("topics_needing_improvement", [])
            prep_topics = result.improvements.get("recommended_preparation_topics", [])
            q_performance = result.improvements.get("question_wise_performance", [])
        elif isinstance(result.improvements, list):
            weak_areas = result.improvements

    return InterviewDetailResponse(
        id=interview.id,
        user_id=interview.user_id,
        job_id=interview.job_id,
        interview_type=interview.interview_type,
        status=interview.status,
        score=interview.score,
        feedback=interview.feedback,
        created_at=interview.created_at,
        completed_at=interview.completed_at,
        overall_performance=result.summary if result else interview.feedback,
        technical_knowledge=tech_knowledge,
        problem_solving=problem_solving,
        communication=comm_text,
        strong_areas=strong_areas,
        weak_areas=weak_areas,
        topics_needing_improvement=topics_imp,
        question_wise_performance=q_performance,
        recommended_preparation_topics=prep_topics,
        result={
            "overall_score": result.overall_score,
            "technical_score": result.technical_score,
            "communication_score": result.communication_score,
            "confidence_score": result.confidence_score,
            "summary": result.summary,
            "strengths": result.strengths,
            "improvements": result.improvements,
        } if result else None,
        answers=[
            {
                "id": a.id,
                "question_id": a.question_id,
                "answer_text": a.answer_text,
                "score": a.score,
                "feedback": a.feedback,
                "keywords_detected": a.keywords_detected,
                "time_taken_seconds": a.time_taken_seconds,
            }
            for a in answers
        ],
    )
