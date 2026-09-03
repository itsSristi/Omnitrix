import re
from typing import Dict, List


class ResumeParser:
    """Basic parser for resume text extracted from uploaded document content."""

    def parse(self, text: str) -> Dict[str, object]:
        cleaned = text.replace("\r", "\n")
        lines = [line.strip() for line in cleaned.split("\n") if line.strip()]

        email = self._extract_email(cleaned)
        phone = self._extract_phone(cleaned)
        name = self._extract_name(lines)
        skills = self._extract_skills(cleaned)

        return {
            "name": name,
            "email": email,
            "phone": phone,
            "skills": skills,
            "raw_text": cleaned,
        }

    def _extract_email(self, text: str) -> str | None:
        match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        return match.group(0) if match else None

    def _extract_phone(self, text: str) -> str | None:
        match = re.search(r"\+?\d[\d\s().-]{8,}\d", text)
        return match.group(0).strip() if match else None

    def _extract_name(self, lines: List[str]) -> str | None:
        for line in lines[:10]:
            if "@" not in line and len(line.split()) <= 4:
                return line
        return None

    def _extract_skills(self, text: str) -> List[str]:
        skill_keywords = {
            "python", "fastapi", "sql", "postgresql", "javascript", "react",
            "node", "typescript", "ai", "machine learning", "data analysis",
            "excel", "power bi", "aws", "docker", "kubernetes", "java",
            "csharp", "c++", "django", "flask", "pandas", "numpy", "scikit",
            "spark", "tableau", "communication", "leadership", "problem solving",
            "api", "mongodb", "redis", "testing", "analytics", "statistics",
            "research", "security", "cybersecurity"
        }

        found = []
        lowered = text.lower()
        for skill in skill_keywords:
            if skill in lowered:
                found.append(skill)
        return found
