import math
import re
from collections import defaultdict

from app.database.database import SessionLocal
from app.models.resume_vector import ResumeVector


class PostgresVectorStore:
    """pgvector-backed store for uploaded resume embeddings."""

    def __init__(self, dimension: int = 64):
        self.dimension = dimension

    def _tokenize(self, text: str):
        return re.findall(r"[a-zA-Z0-9+.#-]+", text.lower())

    def _build_vocabulary(self):
        vocab = [
            "python", "fastapi", "sql", "postgresql", "javascript", "react",
            "node", "typescript", "ai", "machine", "learning", "nlp",
            "data", "analytics", "excel", "powerbi", "aws", "docker",
            "kubernetes", "terraform", "java", "csharp", "c++", "django",
            "flask", "pandas", "numpy", "scikit", "spark", "tableau",
            "communication", "leadership", "problem", "solving", "product",
            "design", "research", "statistics", "deep", "vision", "cybersecurity",
            "security", "api", "graphql", "mongodb", "redis", "testing"
        ]
        return {term: index for index, term in enumerate(vocab)}

    def _vectorize(self, text: str):
        vocabulary = self._build_vocabulary()
        vector = [0.0] * len(vocabulary)
        counts = defaultdict(int)
        for token in self._tokenize(text):
            counts[token] += 1

        for token, count in counts.items():
            if token in vocabulary:
                vector[vocabulary[token]] = float(count)

        norm = math.sqrt(sum(v * v for v in vector))
        if norm:
            vector = [v / norm for v in vector]
        return vector + [0.0] * (self.dimension - len(vector))

    def add_document(self, user_id: int, content: str, metadata: dict | None = None):
        embedding = self._vectorize(content)
        with SessionLocal() as db:
            document = db.query(ResumeVector).filter(ResumeVector.user_id == user_id).first()
            if document is None:
                document = ResumeVector(user_id=user_id)
                db.add(document)

            document.text_content = content
            document.payload = metadata or {}
            document.embedding = embedding
            db.commit()
        return {"user_id": user_id, "metadata": metadata or {}, "embedding": embedding}

    def search(self, query: str, top_k: int = 3):
        query_vector = self._vectorize(query)
        with SessionLocal() as db:
            distance = ResumeVector.embedding.cosine_distance(query_vector).label("distance")
            rows = (
                db.query(ResumeVector, distance)
                .order_by(distance)
                .limit(top_k)
                .all()
            )

        return [
            {
                "user_id": document.user_id,
                "text": document.text_content,
                "metadata": document.payload or {},
                "similarity": 1 - float(distance_value),
            }
            for document, distance_value in rows
        ]


InMemoryVectorStore = PostgresVectorStore
