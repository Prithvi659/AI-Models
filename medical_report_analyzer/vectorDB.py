from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct,VectorParams,Distance

QDRANT_URL = "http://localhost:6334" #Docker Container
COLLECTION = "docs"
VECTOR_DIM = 384

class VectorStore:

    def __init__(self):
        self.client = QdrantClient(url=QDRANT_URL,timeout=30)
        if not self.client.collection_exists(COLLECTION):
            self.client.create_collection(
                vectors_config=VectorParams(distance=Distance.COSINE,size=VECTOR_DIM),
                collection_name=COLLECTION
            )
    def upsert(self, ids:list, vectors:list, payloads:list):
        """store the vector values of the id with their payload(readable texts)"""
        points = [
            PointStruct(id=ids[i],vector=vectors[i],payload=payloads[i])
              for i in range(len(ids))
        ]
        self.client.upsert(collection_name=COLLECTION,points=points)

    def search(self,query_vector:list , top_k:int =5) -> dict:
        """Find the top_k most similar vectors and return their text + sources."""
        response = self.client.query_points(
            collection_name=COLLECTION,
            query=query_vector,
            with_payload=True,
            limit=top_k
        )
        soucrce,context = set(),[]
        for r in response.points:
            payload = getattr(r,"payload",{}) or {}
            if payload.get("text"):
                context.append(payload["text"])
                soucrce.add(payload.get("source",""))
        return {"contents":context,"source":list(soucrce)}

