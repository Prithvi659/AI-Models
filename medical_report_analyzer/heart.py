import uuid
import time
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from google import genai

from data_loaders import load_and_chunk_pdf, embed_text
from vectorDB import VectorStore
from custom_types import LoadRequest, QueryRequest, AnalyzeRequest

load_dotenv()

gemini = genai.Client()
vector_store = VectorStore()

app = FastAPI(title="Medical Report Analyzer")

# allows the frontend to call api
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

DISCLAIMER = (
    "\n\n⚠️ Disclaimer: This information is extracted from your uploaded medical report "
    "and is not a substitute for professional medical advice. Please consult a qualified "
    "healthcare provider for diagnosis and treatment."
)

def _gemini_generate(prompt: str) -> str:
    return gemini.models.generate_content(
        model="gemini-3.6-flash", contents=prompt
    ).text.strip()

def load_data(pdf_path:str,source_id:str) -> dict:
    """load pdf -> embed(create vector) -> store in qdrant"""
    chunks = load_and_chunk_pdf(path=pdf_path)
    vectors = embed_text(chunks)
    ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f" {source_id}:{i} ")) for i in range(len(chunks))]
    payload = [{"source": source_id, "text": chunks[i]} for i in range(len(chunks))]
    vector_store.upsert(ids=ids, vectors=vectors, payloads=payload)
    return {"loaded_chunks": len(chunks), "source_id": source_id}

def run_user_query(question: str, top_k: int) -> dict:
    """Semantic search → answer via Gemini with medical-specific prompt."""
    query_vec = embed_text([question])[0]
    found = vector_store.search(query_vector=query_vec, top_k=top_k)

    context_block = "\n\n".join(found["contents"])
    prompt = (
        "You are a medical assistant. Answer using ONLY the report context below. "
        "Note any abnormal values. If unrelated to the report, say so.\n\n"
        f"Context:\n{context_block}\n\nQuestion: {question}\nAnswer:"
    )
    answer = _gemini_generate(prompt)
    return {
        "answer": answer + DISCLAIMER,
        "sources": found["source"],
        "num_context": len(found["contents"])
    }

def analyze_report(source_id: str, top_k: int) -> dict:
    """Pull report chunks and extract all test results with abnormality flags."""
    # Use a broad medical query to retrieve the most relevant chunks
    query_vec = embed_text(["blood test results CBC hemoglobin glucose cholesterol levels"])[0]
    found = vector_store.search(query_vector=query_vec, top_k=top_k)

    context_block = "\n\n".join(found["contents"])
    prompt = (
        "Extract all medical test results from the report context below. "
        "Return JSON with keys: tests (list of {test_name, value, reference_range, status: NORMAL/LOW/HIGH/UNKNOWN, plain_english}), "
        "summary (1-2 sentences), abnormal_count (int).\n\n"
        f"Context:\n{context_block}\n\nJSON:"
    )
    raw = _gemini_generate(prompt)

    # Strip markdown code fences if Gemini wraps it
    clean = raw.strip()
    if clean.startswith("```"):
        clean = "\n".join(clean.split("\n")[1:])
        clean = clean.rsplit("```", 1)[0].strip()

    return {
        "analysis": clean,
        "source_id": source_id,
        "disclaimer": DISCLAIMER.strip()
    }

@app.post("/load_file_path")
async def file_path(req: LoadRequest):
    """Upload and index a PDF medical report."""
    source = req.source_id or req.pdf_path
    return load_data(req.pdf_path, source)

@app.post("/query")
async def user_query(req: QueryRequest):
    """Ask a natural-language question about the indexed report."""
    return run_user_query(req.question, req.top_k)

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """Extract all test results and flag abnormal values from the indexed report."""
    return analyze_report(req.source_id, req.top_k)

# ─── Static files & root page ───
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

@app.get("/")
async def root():
    return FileResponse(Path(__file__).parent / "static" / "index.html")
