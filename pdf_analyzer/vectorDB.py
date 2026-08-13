from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

QDRANT_URL   = "http://localhost:6333"
COLLECTION   = "docs"
VECTOR_DIM   = 3072  # gemini-embedding-001 output size

class VectorStore:
    """Simple wrapper around Qdrant for upsert and search."""

    def __init__(self):
        self.client = QdrantClient(url=QDRANT_URL, timeout=30)
        # Create collection if it doesn't exist
        if not self.client.collection_exists(COLLECTION):
            self.client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)
            )

    def upsert(self, ids: list, vectors: list, payloads: list):
        """Store vectors with their payloads."""
        points = [
            PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i])
            for i in range(len(ids))
        ]
        self.client.upsert(collection_name=COLLECTION, points=points)

    def search(self, query_vector: list, top_k: int = 5) -> dict:
        """Find the top_k most similar vectors and return their text + sources."""
        response = self.client.query_points(
            collection_name=COLLECTION,
            query=query_vector,
            with_payload=True,
            limit=top_k
        )
        contexts, sources = [], set()
        for r in response.points:
            payload = getattr(r, "payload", {}) or {}
            if payload.get("text"):
                contexts.append(payload["text"])
                sources.add(payload.get("source", ""))
        return {"contexts": contexts, "sources": list(sources)}
