import os

import numpy as np


class EmbeddingService:
    """Configurable embedding provider with a deterministic local fallback."""

    def __init__(self, dimension: int = 64):
        self.dimension = dimension
        self.model_name = os.getenv("EMBEDDING_MODEL", "")
        self.model = None

    def encode(self, text: str, fallback):
        if not self.model_name:
            return fallback(text)
        if self.model is None:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(self.model_name)
        vector = np.asarray(self.model.encode(text, normalize_embeddings=True), dtype="float32")
        if vector.size >= self.dimension:
            return vector[:self.dimension].tolist()
        return np.pad(vector, (0, self.dimension - vector.size)).tolist()
