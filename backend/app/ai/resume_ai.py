from app.ai.llm_service import LLMService


class ResumeAI:
    def __init__(self):
        self.llm = LLMService()

    def evaluate(self, resume_text: str, analysis: dict) -> dict:
        try:
            return self.llm.analyze_resume(resume_text, analysis)
        except Exception as exc:
            return {
                "status": "unavailable",
                "message": "AI evaluation is temporarily unavailable.",
                "error": str(exc),
            }
