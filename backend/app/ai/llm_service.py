import json
import os


class LLMService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = None
        if self.api_key:
            from openai import OpenAI

            self.client = OpenAI(api_key=self.api_key)

    def analyze_resume(self, resume_text: str, deterministic_analysis: dict) -> dict:
        if self.client is None:
            return {
                "status": "not_configured",
                "message": "Set OPENAI_API_KEY to enable AI resume evaluation.",
            }

        prompt = {
            "resume": resume_text[:12000],
            "deterministic_analysis": deterministic_analysis,
            "required_output": {
                "summary": "A concise professional summary",
                "strengths": ["specific strengths"],
                "improvement_areas": ["specific improvement areas"],
                "recommended_roles": ["up to five roles"],
                "interview_focus": ["up to five interview topics"],
            },
        }
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a practical technical recruiter. Return only valid JSON matching the requested output.",
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
        )
        content = response.choices[0].message.content or "{}"
        result = json.loads(content)
        result["status"] = "complete"
        return result
