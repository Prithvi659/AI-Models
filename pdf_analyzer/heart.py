import uuid
import logging
import inngest
import inngest.fast_api
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from google import genai

from data_loader import load_and_chunk_pdf, embed_texts
from vectorDB import VectorStore
from custom_types import IngestRequest, QueryRequest

load_dotenv()

# ── Gemini LLM client ────────────────────────────────────────────────
gemini = genai.Client()

# ── FastAPI app ──────────────────────────────────────────────────────
app = FastAPI(title="PDF RAG Analyzer")

# Allow the frontend (port 3000) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helper functions ─────────────────────────────────────────────────
def run_ingest(pdf_path: str, source_id: str) -> dict:
    """Load PDF → embed chunks → store in Qdrant."""
    chunks  = load_and_chunk_pdf(pdf_path)
    vectors = embed_texts(chunks)
    ids     = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
    payloads = [{"source": source_id, "text": chunks[i]} for i in range(len(chunks))]
    VectorStore().upsert(ids=ids, vectors=vectors, payloads=payloads)
    return {"ingested": len(chunks), "source_id": source_id}

def run_query(question: str, top_k: int) -> dict:
    """Embed question → search Qdrant → ask Gemini → return answer."""
    query_vec = embed_texts([question])[0]
    found     = VectorStore().search(query_vec, top_k)

    context_block = "\n\n".join(f"- {c}" for c in found["contexts"])
    prompt = (
        "Answer the question using ONLY the context below.\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n\n"
        "Answer concisely."
    )
    answer = gemini.models.generate_content(model="gemini-3.0-flash", contents=prompt).text.strip()
    return {"answer": answer, "sources": found["sources"], "num_contexts": len(found["contexts"])}

# ── Direct REST endpoints (used by the frontend) ─────────────────────
@app.post("/ingest")
async def ingest(req: IngestRequest):
    source = req.source_id or req.pdf_path
    return run_ingest(req.pdf_path, source)

@app.post("/query")
async def query(req: QueryRequest):
    return run_query(req.question, req.top_k)

# ── Inngest functions (optional background processing) ───────────────
inngest_client = inngest.Inngest(
    app_id="pdf_rag",
    is_production=False,
    logger=logging.getLogger("uvicorn"),
    serializer=inngest.PydanticSerializer()
)

@inngest_client.create_function(
    fn_id="RAG Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/inngest_pdf")
)
async def rag_ingest_pdf(ctx: inngest.Context):
    source = ctx.event.data.get("source_id", ctx.event.data["pdf_path"])
    return await ctx.step.run("ingest", lambda: run_ingest(ctx.event.data["pdf_path"], source))

@inngest_client.create_function(
    fn_id="RAG Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf")
)
async def rag_query_pdf(ctx: inngest.Context):
    return await ctx.step.run(
        "query",
        lambda: run_query(ctx.event.data["question"], int(ctx.event.data.get("top_k", 5)))
    )

inngest.fast_api.serve(app, inngest_client, functions=[rag_ingest_pdf, rag_query_pdf])
