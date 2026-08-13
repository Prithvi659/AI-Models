from google import genai
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv

load_dotenv()

# ── Gemini client ────────────────────────────────────────────────────
client = genai.Client()
EMBED_MODEL = "gemini-embedding-001"

# ── PDF chunker ──────────────────────────────────────────────────────
splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=300)

def load_and_chunk_pdf(path: str) -> list[str]:
    """Load a PDF and split it into text chunks."""
    docs = PDFReader().load_data(file=path)
    chunks = []
    for doc in docs:
        if doc.text:
            chunks.extend(splitter.split_text(doc.text))
    return chunks

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Convert a list of strings into embedding vectors."""
    result = client.models.embed_content(model=EMBED_MODEL, contents=texts)
    return [item.values for item in result.embeddings]