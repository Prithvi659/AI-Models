from pathlib import Path
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from sentence_transformers import SentenceTransformer

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=300)
embed_model = SentenceTransformer("all-MiniLM-L6-v2")  # 768-dim, local, fast

def load_and_chunk_pdf(path: str) -> list[str]:
    """load pdf and split it into 1000-token chunks"""
    docs = PDFReader().load_data(file=Path(path))
    chunks = []
    for doc in docs:
        if doc.text:
            chunks.extend(splitter.split_text(doc.text))
    return chunks

def embed_text(texts: list[str]) -> list[list[float]]:
    """Convert list of texts into embedding vectors (local, no API call)"""
    return embed_model.encode(texts, convert_to_numpy=True).tolist()
