from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from contextlib import asynccontextmanager
from ai_agent import Ai

BASE_DIR = Path(__file__).parent


agent: Ai = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    print("[INFO] Loading AI Agent...")
    agent = Ai()
    print("[INFO] AI Agent ready.")
    yield
    print("[INFO] Shutting down.")


app = FastAPI(
    title="DiabetesAI Agent",
    description="Ask the AI agent to analyze the diabetes dataset, run predictions, or do calculations.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    role: str = "agent"
    content: str


app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")


@app.get("/", tags=["UI"], include_in_schema=False)
@app.get("/index.html", tags=["UI"], include_in_schema=False)
def serve_ui():
    return FileResponse(BASE_DIR / "index.html")

@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok", "message": "DiabetesAI Agent is running"}

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest):
    """Send a message to the DiabetesAI agent and get a response."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    try:
        response = agent.invoke(request.message)
        return ChatResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
