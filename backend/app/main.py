from fastapi import FastAPI
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.onboarding import router as onboarding_router
from app.api.resume import router as resume_router
from app.database.database import Base, engine
from app.models import (  # noqa: F401
    resume,
    resume_section,
    resume_skill,
    resume_vector,
    skill,
    user,
)

if engine.dialect.name == "postgresql":
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Interviewer API",
    description="Backend API for AI Interviewer",
    version="1.0.0"
)


app.include_router(auth_router)
app.include_router(onboarding_router)
app.include_router(resume_router)
app.include_router(jobs_router)

@app.get("/")
def root():
    return {
        "message": "AI Interviewer API is running"
    }