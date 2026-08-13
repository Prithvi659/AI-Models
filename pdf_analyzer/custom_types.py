from pydantic import BaseModel

class IngestRequest(BaseModel):
    pdf_path: str
    source_id: str = ""         # defaults to pdf_path if empty

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5