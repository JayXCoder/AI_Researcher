"""Retriever agent: RAG retrieval using Gemini embeddings and in-memory vector store (demo)."""
import os
import json
from typing import Optional

import vertexai
from vertexai.language_models import TextEmbeddingModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.schemas import RetrieverRequest, RetrieverResponse, RetrieverChunk

app = FastAPI(title="Retriever Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PROJECT = os.environ.get("GCP_PROJECT", "")
REGION = os.environ.get("VERTEX_REGION", "us-central1")
BUCKET = os.environ.get("GCS_BUCKET", "")

# In-memory store for demo (use Vertex AI Vector Search or Qdrant in production)
_store: list[tuple[list[float], str, str]] = []  # (embedding, text, source)


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Get embeddings via Vertex AI Gemini text-embedding."""
    if not PROJECT:
        return [[0.0] * 768 for _ in texts]  # stub
    try:
        vertexai.init(project=PROJECT, location=REGION)
        model = TextEmbeddingModel.from_pretrained("text-embedding-005")
        emb = model.get_embeddings(texts)
        return [e.values for e in emb]
    except Exception:
        return [[0.0] * 768 for _ in texts]


def cosine_sim(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


@app.on_event("startup")
async def startup():
    """Optionally load documents from GCS or seed demo chunks."""
    global _store
    if not _store:
        # Demo chunks so RAG always returns something
        demo = [
            ("Machine learning is a subset of AI that enables systems to learn from data.", "demo-doc-1"),
            ("Vertex AI provides managed ML and generative AI on Google Cloud.", "demo-doc-2"),
            ("RAG combines retrieval with generation for grounded answers.", "demo-doc-3"),
        ]
        try:
            embs = get_embeddings([t for t, _ in demo])
            _store = list(zip(embs, [t for t, _ in demo], [s for _, s in demo]))
        except Exception:
            _store = [([0.0] * 768, t, s) for t, s in demo]


@app.post("/", response_model=RetrieverResponse)
async def retrieve(request: RetrieverRequest):
    """Retrieve top-k chunks by embedding similarity."""
    query = request.query
    top_k = min(request.top_k, 10)
    query_emb = get_embeddings([query])[0]
    scored = []
    for emb, text, source in _store:
        score = cosine_sim(query_emb, emb)
        scored.append((score, text, source))
    scored.sort(key=lambda x: -x[0])
    chunks = [RetrieverChunk(content=t, source=s, score=sc) for sc, t, s in scored[:top_k]]
    return RetrieverResponse(chunks=chunks)


@app.post("/ingest")
async def ingest(doc_id: str, content: str, source: str = ""):
    """Ingest a document (embed and add to store). For demo, in-memory only."""
    embs = get_embeddings([content])
    _store.append((embs[0], content, source or doc_id))
    return {"status": "ok", "store_size": len(_store)}
