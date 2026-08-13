from pydantic import BaseModel

class LoadRequest(BaseModel):
    pdf_path : str
    source_id : str = ""  # defaults to pdf_path if empty

class QueryRequest(BaseModel):
    question : str
    top_k : int = 5

class AnalyzeRequest(BaseModel):
    source_id : str        # the source_id used when the PDF was loaded
    top_k : int = 10       # how many chunks to pull for analysis
