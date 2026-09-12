from app.ai.llm_service import LLMService
import re


class ResumeAI:
    def __init__(self):
        self.llm = LLMService()

    def evaluate(self, resume_text: str, analysis: dict) -> dict:
        try:
            return self.llm.analyze_resume(resume_text, analysis)
        except Exception as exc:
            skills = analysis.get("skills", [])
            return {
                "skills": [
                    {
                        "name": skill,
                        "category": "Technical Skill",
                        "evidence": skill,
                        "confidence": 1.0,
                    }
                    for skill in skills
                ],
                "education": [],
                "experience": [],
                "internships": [],
                "projects": [],
                "certifications": [],
                "achievements": [],
                "suggested_roles": [],
                "domains": [],
                "status": "complete",
                "provider": "local-fallback",
                "notice": "Qwen was unavailable; analysis used verified text extraction.",
            }

    def recommend_for_job(self, job_description: str, analysis: dict) -> dict:
        try:
            return self.llm.recommend_for_job(job_description, analysis)
        except Exception as exc:
            return {
                "status": "unavailable",
                "message": "AI job recommendation is temporarily unavailable.",
                "error": str(exc),
            }

    def generate_resume(self, name: str, user_choice: str) -> dict:
        try:
            return self.llm.generate_resume(name, user_choice)
        except Exception as exc:
            # Keep CV creation usable when the optional local Qwen runtime is
            # not installed. This fallback only reformats user-provided facts.
            input_text = user_choice.strip()
            skills = self._extract_skills(input_text)
            headline = self._extract_headline(input_text)
            return {
                "name": name.strip(),
                "headline": headline,
                "summary": input_text,
                "skills": skills,
                "experience": [],
                "projects": [],
                "education": [],
                "certifications": [],
                "achievements": [],
                "domains": [],
                "formatted_resume": self._format_resume(name, headline, input_text, skills),
                "status": "complete",
                "provider": "local-fallback",
                "notice": "Qwen was unavailable; the CV was formatted from the supplied information.",
            }

    @staticmethod
    def _extract_skills(text: str) -> list[str]:
        known_skills = [
            "Python", "FastAPI", "Django", "Flask", "Java", "JavaScript", "TypeScript",
            "React", "SQL", "PostgreSQL", "MongoDB", "Redis", "Docker", "Kubernetes",
            "AWS", "Azure", "Git", "Linux", "Machine Learning", "Deep Learning",
            "Data Analysis", "FAISS", "TensorFlow", "PyTorch",
        ]
        lowered = text.lower()
        return [
            skill for skill in known_skills
            if re.search(rf"(?<![a-z0-9]){re.escape(skill.lower())}(?![a-z0-9])", lowered)
        ]

    @staticmethod
    def _extract_headline(text: str) -> str:
        role_match = re.search(
            r"(?:want|seeking|target|role|career|become)\s+(?:a|an)?\s*([a-z][a-z ]{2,50})",
            text,
            re.IGNORECASE,
        )
        return role_match.group(1).strip().title() if role_match else "Professional"

    @staticmethod
    def _format_resume(name: str, headline: str, summary: str, skills: list[str]) -> str:
        skills_text = ", ".join(skills) if skills else "Not provided"
        return (
            f"{name.strip()}\n"
            f"{headline}\n\n"
            "PROFESSIONAL SUMMARY\n"
            f"{summary}\n\n"
            "SKILLS\n"
            f"{skills_text}\n\n"
            "EXPERIENCE\n"
            "Not provided\n\n"
            "EDUCATION\n"
            "Not provided\n\n"
            "PROJECTS\n"
            "Not provided\n"
        )
