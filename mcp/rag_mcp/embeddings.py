"""OpenAI embeddings shared by indexing and querying."""
import json
import math
import time

import httpx

DIMENSIONS = 1536


def vector_literal(vector):
    if len(vector) != DIMENSIONS or not all(math.isfinite(v) for v in vector):
        raise ValueError("Expected 1536 finite embedding values")
    if not any(vector):
        raise ValueError("Zero embeddings cannot be used for cosine search")
    return json.dumps(vector, separators=(",", ":"))


class Embedder:
    def __init__(self, api_key, model):
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required")
        self.api_key, self.model = api_key, model

    def embed(self, texts):
        if not texts or any(not t.strip() for t in texts):
            raise ValueError("Embedding input must not be empty")
        with httpx.Client(timeout=60) as client:
            for attempt in range(3):
                response = client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": "Bearer " + self.api_key},
                    json={"input": texts, "model": self.model,
                          "encoding_format": "float", "dimensions": DIMENSIONS},
                )
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                response.raise_for_status()
                data = sorted(response.json()["data"], key=lambda d: d["index"])
                if [d["index"] for d in data] != list(range(len(texts))):
                    raise ValueError("Embedding response indices do not match input")
                vectors = [d["embedding"] for d in data]
                for vector in vectors:
                    vector_literal(vector)
                return vectors
