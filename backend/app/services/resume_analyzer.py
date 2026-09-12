from app.services.resume_parser import ResumeParser
from app.services.skill_extractor import SkillExtractor
from app.services.vector_store import InMemoryVectorStore


class ResumeAnalyzer:
    """Composite resume analysis service for parsing, skill extraction and section-aware vectorization."""

    def __init__(self):
        self.parser = ResumeParser()
        self.skill_extractor = SkillExtractor()
        self.vector_store = InMemoryVectorStore()

    def analyze(self, text: str, user_id: int | None = None):
        parsed = self.parser.parse(text)
        skills = self.skill_extractor.extract(text)
        normalized_skills = self.skill_extractor.normalize(skills)

        if user_id is not None:
            self.vector_store.add_document(
                user_id,
                text,
                metadata={"skills": normalized_skills},
                section_name="full_resume",
            )

            for section_name, section_text in self.vector_store._split_sections(text):
                if section_name == "full_resume":
                    continue
                self.vector_store.add_document(
                    user_id,
                    section_text,
                    metadata={"skills": normalized_skills, "section_name": section_name},
                    section_name=section_name,
                )

        summary = {
            "name": parsed.get("name"),
            "email": parsed.get("email"),
            "phone": parsed.get("phone"),
            "skills": normalized_skills,
            "summary": f"Candidate profile includes {', '.join(normalized_skills[:5]) if normalized_skills else 'core technical skills'}.",
            "sections": [
                "summary",
                "skills",
                "experience",
                "education",
                "projects",
                "certifications",
            ],
        }
        return summary
