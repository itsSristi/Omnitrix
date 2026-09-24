import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.onboarding import router as onboarding_router
from app.api.resume import router as resume_router
from app.api.assessment import router as assessment_router

from app.database.database import Base, engine

from app.models import (  # noqa: F401
    resume,
    resume_section,
    resume_skill,
    resume_vector,
    skill,
    user,
)

from app.services.assessment_timer import assessment_timer_loop


# --------------------------------------------------
# Database / pgvector setup
# --------------------------------------------------

if engine.dialect.name == "postgresql":
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE EXTENSION IF NOT EXISTS vector"
            )
        )

Base.metadata.create_all(bind=engine)


# --------------------------------------------------
# Application lifespan
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    timer_task = asyncio.create_task(
        assessment_timer_loop()
    )

    try:
        yield
    finally:
        timer_task.cancel()

        try:
            await timer_task
        except asyncio.CancelledError:
            pass


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="AI Interviewer API",
    description="Backend API for AI Interviewer",
    version="1.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# Routers
# --------------------------------------------------

app.include_router(auth_router)
app.include_router(onboarding_router)
app.include_router(resume_router)
app.include_router(jobs_router)
app.include_router(assessment_router)


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "AI Interviewer API is running"
    }