from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.onboarding import router as onboarding_router
from app.api.resume import router as resume_router

app = FastAPI(
    title="AI Interviewer API",
    description="Backend API for AI Interviewer",
    version="1.0.0"
)


app.include_router(auth_router)
app.include_router(onboarding_router)
app.include_router(resume_router)

@app.get("/")
def root():
    return {
        "message": "AI Interviewer API is running"
    }